"""Core ingestion run manager for equity market data using yfinance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Any, Dict, List, Optional

import yfinance as yf  # type: ignore[import-not-found]

from .db import db_models, get_session
from .logging import logger


@dataclass
class StocksIngestionConfig:
    """Configuration payload for a stocks ingestion run.

    Mirrors the shape of StocksIngestionConfig in theory-engine-api.
    """

    exchange_code: str
    tickers: List[str]
    timeframe: str
    start: str | None
    end: str | None
    include_candles: bool = True
    backfill_missing_candles: bool = False


class StocksIngestionRunManager:
    """Responsible for executing a single stocks ingestion run."""

    TIMEFRAME_TO_INTERVAL: Dict[str, str] = {
        "1d": "1d",
        "1h": "60m",
    }

    TIMEFRAME_SECONDS: Dict[str, int] = {
        "1d": 86400,
        "1h": 3600,
    }

    def _update_run(self, run_id: int, **updates: Any) -> None:
        with get_session() as session:
            run = (
                session.query(db_models.EquityIngestionRun)
                .filter(db_models.EquityIngestionRun.id == run_id)
                .first()
            )
            if not run:
                logger.error("equity_run_not_found", run_id=run_id)
                return
            for key, value in updates.items():
                setattr(run, key, value)
            session.flush()
            logger.info("equity_run_updated", run_id=run_id, updates=list(updates.keys()))

    def _resolve_time_bounds(
        self,
        cfg: StocksIngestionConfig,
        timeframe: str,
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

        window_days = 365 if timeframe == "1d" else 30

        if start_dt and not end_dt:
            end_dt = start_dt + timedelta(days=window_days)
        elif end_dt and not start_dt:
            start_dt = end_dt - timedelta(days=window_days)
        elif not start_dt and not end_dt:
            end_dt = now
            start_dt = now - timedelta(days=window_days)

        assert start_dt is not None and end_dt is not None
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(days=1)
        return start_dt, end_dt

    def _get_or_create_exchange(
        self, session, code: str
    ) -> "db_models.EquityExchange":
        exchange = (
            session.query(db_models.EquityExchange)
            .filter(db_models.EquityExchange.code == code)
            .first()
        )
        if exchange:
            return exchange

        exchange = db_models.EquityExchange(
            code=code,
            name=code.title(),
            timezone="UTC",
            extra_metadata={},
        )
        session.add(exchange)
        session.flush()
        return exchange

    def _get_or_create_asset(
        self,
        session,
        exchange: "db_models.EquityExchange",
        ticker: str,
        info: dict | None = None,
    ) -> "db_models.EquityAsset":
        asset = (
            session.query(db_models.EquityAsset)
            .filter(
                db_models.EquityAsset.exchange_id == exchange.id,
                db_models.EquityAsset.ticker == ticker,
            )
            .first()
        )
        if asset:
            return asset

        name = (info or {}).get("longName") or (info or {}).get("shortName")
        sector = (info or {}).get("sector")
        industry = (info or {}).get("industry")

        asset = db_models.EquityAsset(
            exchange_id=exchange.id,
            ticker=ticker,
            name=name,
            sector=sector,
            industry=industry,
            external_codes={"yfinance": ticker},
            extra_metadata={"info": info or {}},
        )
        session.add(asset)
        session.flush()
        return asset

    def _ingest_ticker(
        self,
        run_id: int,
        cfg: StocksIngestionConfig,
        exchange_code: str,
        ticker: str,
    ) -> int:
        """Fetch OHLCV for a single ticker via yfinance and upsert candles."""
        timeframe = cfg.timeframe
        interval = self.TIMEFRAME_TO_INTERVAL.get(timeframe)
        if not interval or timeframe not in self.TIMEFRAME_SECONDS:
            logger.warning(
                "unsupported_timeframe_stocks",
                run_id=run_id,
                timeframe=timeframe,
            )
            return 0

        start_dt, end_dt = self._resolve_time_bounds(cfg, timeframe)

        logger.info(
            "fetch_history_start",
            run_id=run_id,
            ticker=ticker,
            exchange=exchange_code,
            timeframe=timeframe,
            interval=interval,
            start=str(start_dt),
            end=str(end_dt),
        )

        yf_ticker = yf.Ticker(ticker)
        hist = yf_ticker.history(
            interval=interval,
            start=start_dt,
            end=end_dt,
        )
        if hist.empty:
            logger.warning(
                "no_history_for_ticker",
                run_id=run_id,
                ticker=ticker,
                timeframe=timeframe,
            )
            return 0

        inserted = 0
        with get_session() as session:
            exchange_row = self._get_or_create_exchange(session, exchange_code.upper())
            info = yf_ticker.info if hasattr(yf_ticker, "info") else {}
            asset = self._get_or_create_asset(session, exchange_row, ticker, info)

            for ts, row in hist.iterrows():
                # yfinance index is pandas Timestamp
                ts_dt = ts.to_pydatetime()
                if ts_dt.tzinfo is None:
                    ts_dt = ts_dt.replace(tzinfo=timezone.utc)

                existing = (
                    session.query(db_models.EquityCandle)
                    .filter(
                        db_models.EquityCandle.asset_id == asset.id,
                        db_models.EquityCandle.timeframe == timeframe,
                        db_models.EquityCandle.timestamp == ts_dt,
                    )
                    .first()
                )
                if existing:
                    continue

                open_ = float(row["Open"])
                high = float(row["High"])
                low = float(row["Low"])
                close = float(row["Close"])
                volume = float(row["Volume"])
                stats: Dict[str, Any] = {}
                if "Adj Close" in row:
                    stats["adj_close"] = float(row["Adj Close"])

                candle = db_models.EquityCandle(
                    asset_id=asset.id,
                    exchange_id=exchange_row.id,
                    timeframe=timeframe,
                    timestamp=ts_dt,
                    open=open_,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                    stats=stats,
                )
                session.add(candle)
                inserted += 1

            logger.info(
                "equity_candles_inserted_for_ticker",
                run_id=run_id,
                exchange=exchange_code,
                ticker=ticker,
                timeframe=timeframe,
                inserted=inserted,
            )

        return inserted

    def run(self, run_id: int, config: StocksIngestionConfig) -> Dict[str, Any]:
        """Execute ingestion for the given equities run using yfinance."""
        summary: Dict[str, Any] = {
            "exchange": config.exchange_code,
            "tickers": config.tickers,
            "timeframe": config.timeframe,
            "candles_inserted": 0,
            "gaps_backfilled": 0,
        }

        logger.info(
            "equity_run_started",
            run_id=run_id,
            exchange=config.exchange_code,
            tickers=config.tickers,
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
            total_inserted = 0
            for ticker in config.tickers or []:
                try:
                    inserted = self._ingest_ticker(run_id, config, config.exchange_code, ticker)
                    total_inserted += inserted
                except Exception as exc:  # pragma: no cover
                    logger.exception(
                        "ticker_ingestion_failed",
                        run_id=run_id,
                        ticker=ticker,
                        error=str(exc),
                    )

            summary["candles_inserted"] = total_inserted
            summary_str = (
                f"Exchange={config.exchange_code}, tickers={','.join(config.tickers) or 'N/A'}, "
                f"timeframe={config.timeframe}, candles_inserted={total_inserted}, gaps_backfilled=0"
            )

            self._update_run(
                run_id,
                status="success",
                finished_at=datetime.utcnow(),
                summary=summary_str,
            )
            logger.info("equity_run_complete", run_id=run_id, summary=summary)
        except Exception as exc:  # pragma: no cover
            logger.exception("equity_run_failed", run_id=run_id, error=str(exc))
            self._update_run(
                run_id,
                status="error",
                finished_at=datetime.utcnow(),
                error_details=str(exc),
            )
            raise

        return summary


manager = StocksIngestionRunManager()


