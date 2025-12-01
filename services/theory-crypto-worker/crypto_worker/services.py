"""Core ingestion run manager for crypto market data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Any, Dict, List, Optional

import ccxt  # type: ignore[import-not-found]

from .db import db_models, get_session
from .logging import logger


@dataclass
class CryptoIngestionConfig:
    """Configuration payload for a crypto ingestion run.

    Mirrors the shape of CryptoIngestionConfig in theory-engine-api.
    """

    exchange_code: str
    symbols: List[str]
    timeframe: str
    start: str | None
    end: str | None
    include_candles: bool = True
    backfill_missing_candles: bool = False


class CryptoIngestionRunManager:
    """Responsible for executing a single crypto ingestion run."""

    EXCHANGE_ID_MAP: Dict[str, str] = {
        "BINANCE": "binance",
        "COINBASE": "coinbase",
        "BYBIT": "bybit",
    }

    TIMEFRAME_SECONDS: Dict[str, int] = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
    }

    def _update_run(self, run_id: int, **updates: Any) -> None:
        with get_session() as session:
            run = (
                session.query(db_models.CryptoIngestionRun)
                .filter(db_models.CryptoIngestionRun.id == run_id)
                .first()
            )
            if not run:
                logger.error("crypto_run_not_found", run_id=run_id)
                return
            for key, value in updates.items():
                setattr(run, key, value)
            session.flush()
            logger.info("crypto_run_updated", run_id=run_id, updates=list(updates.keys()))

    def _normalize_symbol(self, raw: str) -> str:
        """Convert symbols like 'BTCUSDT' -> 'BTC/USDT' for ccxt.

        If a slash is already present, return as-is.
        """
        s = raw.strip().upper()
        if "/" in s:
            return s
        if len(s) > 4:
            return f"{s[:-4]}/{s[-4:]}"
        return s

    def _resolve_time_bounds(
        self,
        cfg: CryptoIngestionConfig,
    ) -> tuple[datetime, datetime]:
        """Compute start/end datetimes with sane defaults."""
        now = datetime.now(tz=timezone.utc)

        def parse_iso(value: Optional[str]) -> Optional[datetime]:
            if not value:
                return None
            # datetime-local comes without timezone; treat as UTC
            try:
                dt = datetime.fromisoformat(value)
            except ValueError:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt

        start_dt = parse_iso(cfg.start)
        end_dt = parse_iso(cfg.end)

        if start_dt and not end_dt:
            end_dt = start_dt + timedelta(hours=24)
        elif end_dt and not start_dt:
            start_dt = end_dt - timedelta(hours=24)
        elif not start_dt and not end_dt:
            end_dt = now
            start_dt = now - timedelta(hours=24)

        assert start_dt is not None and end_dt is not None
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(minutes=1)
        return start_dt, end_dt

    def _get_or_create_exchange(
        self, session, code: str, ccxt_id: str
    ) -> "db_models.CryptoExchange":
        exchange = (
            session.query(db_models.CryptoExchange)
            .filter(db_models.CryptoExchange.code == code)
            .first()
        )
        if exchange:
            return exchange

        exchange = db_models.CryptoExchange(
            code=code,
            name=code.title(),
            timezone="UTC",
            metadata={"ccxt_id": ccxt_id},
        )
        session.add(exchange)
        session.flush()
        return exchange

    def _get_or_create_asset(
        self,
        session,
        exchange: "db_models.CryptoExchange",
        market: dict,
    ) -> "db_models.CryptoAsset":
        symbol = market.get("symbol") or market.get("id")
        base = market.get("base")
        quote = market.get("quote")

        asset = (
            session.query(db_models.CryptoAsset)
            .filter(
                db_models.CryptoAsset.exchange_id == exchange.id,
                db_models.CryptoAsset.symbol == symbol,
            )
            .first()
        )
        if asset:
            return asset

        asset = db_models.CryptoAsset(
            exchange_id=exchange.id,
            symbol=symbol,
            base=base,
            quote=quote,
            external_codes={"ccxt": market.get("id")},
            metadata={"info": market.get("info", {})},
        )
        session.add(asset)
        session.flush()
        return asset

    def _ingest_symbol(
        self,
        run_id: int,
        cfg: CryptoIngestionConfig,
        ccxt_exchange_id: str,
        symbol_raw: str,
    ) -> int:
        """Fetch OHLCV for a single symbol via ccxt and upsert candles."""
        norm_symbol = self._normalize_symbol(symbol_raw)
        if cfg.timeframe not in self.TIMEFRAME_SECONDS:
            logger.warning(
                "unsupported_timeframe",
                run_id=run_id,
                timeframe=cfg.timeframe,
            )
            return 0

        tf_seconds = self.TIMEFRAME_SECONDS[cfg.timeframe]
        start_dt, end_dt = self._resolve_time_bounds(cfg)
        since_ms = int(start_dt.timestamp() * 1000)

        max_bars = min(
            1000,
            max(1, ceil((end_dt - start_dt).total_seconds() / tf_seconds)),
        )

        logger.info(
            "fetch_ohlcv_start",
            run_id=run_id,
            exchange=ccxt_exchange_id,
            symbol=norm_symbol,
            timeframe=cfg.timeframe,
            since_ms=since_ms,
            limit=max_bars,
        )

        exchange_cls = getattr(ccxt, ccxt_exchange_id)
        exchange = exchange_cls()
        markets = exchange.load_markets()
        if norm_symbol not in markets:
            logger.warning(
                "symbol_not_in_markets",
                run_id=run_id,
                exchange=ccxt_exchange_id,
                symbol=norm_symbol,
            )
            return 0

        ohlcv = exchange.fetch_ohlcv(
            norm_symbol,
            timeframe=cfg.timeframe,
            since=since_ms,
            limit=max_bars,
        )

        inserted = 0
        with get_session() as session:
            exchange_row = self._get_or_create_exchange(
                session, cfg.exchange_code.upper(), ccxt_exchange_id
            )
            market = markets[norm_symbol]
            asset = self._get_or_create_asset(session, exchange_row, market)

            for row in ohlcv:
                ts_ms, o, h, l, c, v, *_ = row
                ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

                existing = (
                    session.query(db_models.CryptoCandle)
                    .filter(
                        db_models.CryptoCandle.asset_id == asset.id,
                        db_models.CryptoCandle.timeframe == cfg.timeframe,
                        db_models.CryptoCandle.timestamp == ts,
                    )
                    .first()
                )
                if existing:
                    continue

                candle = db_models.CryptoCandle(
                    asset_id=asset.id,
                    exchange_id=exchange_row.id,
                    timeframe=cfg.timeframe,
                    timestamp=ts,
                    open=float(o),
                    high=float(h),
                    low=float(l),
                    close=float(c),
                    volume=float(v),
                    stats={},
                )
                session.add(candle)
                inserted += 1

            logger.info(
                "candles_inserted_for_symbol",
                run_id=run_id,
                exchange=ccxt_exchange_id,
                symbol=norm_symbol,
                timeframe=cfg.timeframe,
                inserted=inserted,
            )

        return inserted

    def run(self, run_id: int, config: CryptoIngestionConfig) -> Dict[str, Any]:
        """Execute ingestion for the given run using ccxt (free public data)."""
        summary: Dict[str, Any] = {
            "exchange": config.exchange_code,
            "symbols": config.symbols,
            "timeframe": config.timeframe,
            "candles_inserted": 0,
            "gaps_backfilled": 0,
        }

        logger.info(
            "crypto_run_started",
            run_id=run_id,
            exchange=config.exchange_code,
            symbols=config.symbols,
            timeframe=config.timeframe,
            start=config.start,
            end=config.end,
        )

        self._update_run(
            run_id,
            status="running",
            started_at=datetime.utcnow(),
        )

        try:
            ccxt_id = self.EXCHANGE_ID_MAP.get(config.exchange_code.upper())
            if not ccxt_id:
                raise ValueError(f"Unsupported exchange code: {config.exchange_code}")

            if not config.symbols:
                logger.warning(
                    "no_symbols_provided",
                    run_id=run_id,
                    exchange=config.exchange_code,
                )

            total_inserted = 0
            for symbol in config.symbols or []:
                try:
                    inserted = self._ingest_symbol(run_id, config, ccxt_id, symbol)
                    total_inserted += inserted
                except Exception as exc:  # pragma: no cover
                    logger.exception(
                        "symbol_ingestion_failed",
                        run_id=run_id,
                        symbol=symbol,
                        error=str(exc),
                    )

            summary["candles_inserted"] = total_inserted
            summary_str = (
                f"Exchange={config.exchange_code}, symbols={','.join(config.symbols) or 'N/A'}, "
                f"timeframe={config.timeframe}, candles_inserted={total_inserted}, gaps_backfilled=0"
            )

            self._update_run(
                run_id,
                status="success",
                finished_at=datetime.utcnow(),
                summary=summary_str,
            )
            logger.info("crypto_run_complete", run_id=run_id, summary=summary)
        except Exception as exc:  # pragma: no cover
            logger.exception("crypto_run_failed", run_id=run_id, error=str(exc))
            self._update_run(
                run_id,
                status="error",
                finished_at=datetime.utcnow(),
                error_details=str(exc),
            )
            raise

        return summary


manager = CryptoIngestionRunManager()


