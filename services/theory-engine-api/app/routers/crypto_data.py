"""Admin endpoints for crypto market data ingestion and browsing."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, desc, select
from sqlalchemy.orm import selectinload

from .. import db_models
from ..celery_client import get_celery_app
from ..db import AsyncSession, get_db

router = APIRouter(prefix="/api/admin/crypto", tags=["crypto-data"])


class CryptoIngestionConfig(BaseModel):
    """Configuration for a crypto ingestion run."""

    model_config = ConfigDict(populate_by_name=True)

    exchange_code: str = Field(..., alias="exchangeCode")
    symbols: list[str] = Field(default_factory=list, alias="symbols")
    timeframe: str = Field(..., alias="timeframe")
    start: datetime | None = Field(None, alias="start")
    end: datetime | None = Field(None, alias="end")
    include_candles: bool = Field(True, alias="includeCandles")
    backfill_missing_candles: bool = Field(False, alias="backfillMissingCandles")

    def to_worker_payload(self) -> dict[str, Any]:
        return {
            "exchange_code": self.exchange_code,
            "symbols": self.symbols,
            "timeframe": self.timeframe,
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
            "include_candles": self.include_candles,
            "backfill_missing_candles": self.backfill_missing_candles,
        }


class CryptoIngestionCreateRequest(BaseModel):
    config: CryptoIngestionConfig
    requested_by: str | None = Field(None, alias="requestedBy")


class CryptoIngestionRunResponse(BaseModel):
    id: int
    exchange_code: str
    status: str
    timeframe: str
    symbols: list[str]
    start_time: datetime | None
    end_time: datetime | None
    summary: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    requested_by: str | None
    config: dict[str, Any] | None = None


class CryptoAssetSummary(BaseModel):
    id: int
    symbol: str
    base: str | None
    quote: str | None
    exchange_code: str


class CryptoAssetDetail(BaseModel):
    id: int
    symbol: str
    base: str | None
    quote: str | None
    exchange_code: str
    metadata: dict[str, Any]


class CryptoCandleSummary(BaseModel):
    id: int
    asset_id: int
    exchange_code: str
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class CryptoAssetListResponse(BaseModel):
    assets: list[CryptoAssetSummary]
    total: int


class CryptoCandleListResponse(BaseModel):
    candles: list[CryptoCandleSummary]
    total: int
    next_offset: int | None


def _serialize_run(run: db_models.CryptoIngestionRun) -> CryptoIngestionRunResponse:
    """Serialize a crypto ingestion run to API response."""
    return CryptoIngestionRunResponse(
        id=run.id,
        exchange_code=run.exchange_code,
        status=run.status,
        timeframe=str(run.timeframe),
        symbols=run.symbols or [],
        start_time=run.start_time,
        end_time=run.end_time,
        summary=run.summary,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        requested_by=run.requested_by,
        config=run.config,
    )


@router.post("/ingestion/runs", response_model=CryptoIngestionRunResponse)
async def create_ingestion_run(
    payload: CryptoIngestionCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> CryptoIngestionRunResponse:
    """Create and enqueue a new crypto ingestion run."""

    cfg = payload.config
    config_dict = cfg.model_dump(by_alias=False)
    # Normalize datetimes in config for JSONB storage
    if isinstance(config_dict.get("start"), datetime):
        config_dict["start"] = config_dict["start"].isoformat()
    if isinstance(config_dict.get("end"), datetime):
        config_dict["end"] = config_dict["end"].isoformat()

    run = db_models.CryptoIngestionRun(
        exchange_code=cfg.exchange_code,
        symbols=cfg.symbols or [],
        timeframe=cfg.timeframe,
        start_time=cfg.start,
        end_time=cfg.end,
        status="pending",
        requested_by=payload.requested_by,
        config=config_dict,
    )
    session.add(run)
    await session.flush()

    worker_payload = cfg.to_worker_payload()
    try:
        celery_app = get_celery_app()
        async_result = celery_app.send_task(
            "run_crypto_ingestion_job",
            args=[run.id, worker_payload],
            queue="crypto-worker",
            routing_key="crypto-worker",
        )
        run.job_id = async_result.id
    except Exception as exc:  # pragma: no cover
        from ..logging_config import get_logger

        logger = get_logger(__name__)
        logger.error("failed_to_enqueue_crypto_ingestion", error=str(exc), exc_info=True)
        run.status = "error"
        run.error_details = f"Failed to enqueue crypto ingestion job: {exc}"
        raise HTTPException(status_code=500, detail="Failed to enqueue crypto ingestion job") from exc

    return _serialize_run(run)


@router.get("/ingestion/runs", response_model=list[CryptoIngestionRunResponse])
async def list_ingestion_runs(
    exchange: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    timeframe: str | None = Query(None),
    limit: int = Query(50, le=200),
    session: AsyncSession = Depends(get_db),
) -> list[CryptoIngestionRunResponse]:
    stmt: Select[tuple[db_models.CryptoIngestionRun]] = (
        select(db_models.CryptoIngestionRun)
        .order_by(desc(db_models.CryptoIngestionRun.created_at))
        .limit(limit)
    )
    if exchange:
        stmt = stmt.where(db_models.CryptoIngestionRun.exchange_code == exchange.upper())
    if status_filter:
        stmt = stmt.where(db_models.CryptoIngestionRun.status == status_filter)
    if timeframe:
        stmt = stmt.where(db_models.CryptoIngestionRun.timeframe == timeframe)

    results = await session.execute(stmt)
    runs = results.scalars().all()
    return [_serialize_run(run) for run in runs]


@router.get("/ingestion/runs/{run_id}", response_model=CryptoIngestionRunResponse)
async def fetch_ingestion_run(
    run_id: int,
    session: AsyncSession = Depends(get_db),
) -> CryptoIngestionRunResponse:
    result = await session.execute(
        select(db_models.CryptoIngestionRun).where(db_models.CryptoIngestionRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return _serialize_run(run)


@router.get("/assets", response_model=CryptoAssetListResponse)
async def list_assets(
    session: AsyncSession = Depends(get_db),
    exchange: str | None = Query(None),
    symbol_prefix: str | None = Query(None, alias="symbolPrefix"),
    base: str | None = Query(None),
    quote: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> CryptoAssetListResponse:
    base_stmt: Select[tuple[db_models.CryptoAsset]] = select(db_models.CryptoAsset).options(
        selectinload(db_models.CryptoAsset.exchange),
    )

    if exchange:
        base_stmt = base_stmt.join(db_models.CryptoExchange).where(
            db_models.CryptoExchange.code == exchange.upper()
        )
    if symbol_prefix:
        like_pattern = f"{symbol_prefix.upper()}%"
        base_stmt = base_stmt.where(db_models.CryptoAsset.symbol.ilike(like_pattern))
    if base:
        base_stmt = base_stmt.where(db_models.CryptoAsset.base == base.upper())
    if quote:
        base_stmt = base_stmt.where(db_models.CryptoAsset.quote == quote.upper())

    total_result = await session.execute(base_stmt.with_only_columns(db_models.CryptoAsset.id))
    total = len(total_result.scalars().all())

    stmt = base_stmt.order_by(db_models.CryptoAsset.symbol).offset(offset).limit(limit)
    results = await session.execute(stmt)
    assets: Sequence[db_models.CryptoAsset] = results.scalars().unique().all()

    summaries = [
        CryptoAssetSummary(
            id=a.id,
            symbol=a.symbol,
            base=a.base,
            quote=a.quote,
            exchange_code=a.exchange.code if a.exchange else "",
        )
        for a in assets
    ]
    return CryptoAssetListResponse(assets=summaries, total=total)


@router.get("/assets/{asset_id}", response_model=CryptoAssetDetail)
async def fetch_asset(
    asset_id: int,
    session: AsyncSession = Depends(get_db),
) -> CryptoAssetDetail:
    result = await session.execute(
        select(db_models.CryptoAsset)
        .options(selectinload(db_models.CryptoAsset.exchange))
        .where(db_models.CryptoAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    return CryptoAssetDetail(
        id=asset.id,
        symbol=asset.symbol,
        base=asset.base,
        quote=asset.quote,
        exchange_code=asset.exchange.code if asset.exchange else "",
        metadata=asset.extra_metadata or {},
    )


@router.get("/candles", response_model=CryptoCandleListResponse)
async def list_candles(
    session: AsyncSession = Depends(get_db),
    asset_id: int | None = Query(None, alias="assetId"),
    symbol: str | None = Query(None),
    exchange: str | None = Query(None),
    timeframe: str | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> CryptoCandleListResponse:
    base_stmt = (
        select(db_models.CryptoCandle)
        .options(
            selectinload(db_models.CryptoCandle.asset).selectinload(db_models.CryptoAsset.exchange),
        )
    )

    if asset_id is not None:
        base_stmt = base_stmt.where(db_models.CryptoCandle.asset_id == asset_id)
    if symbol:
        base_stmt = base_stmt.join(db_models.CryptoAsset).where(
            db_models.CryptoAsset.symbol == symbol.upper()
        )
    if exchange:
        base_stmt = base_stmt.join(db_models.CryptoExchange).where(
            db_models.CryptoExchange.code == exchange.upper()
        )
    if timeframe:
        base_stmt = base_stmt.where(db_models.CryptoCandle.timeframe == timeframe)
    if start:
        base_stmt = base_stmt.where(db_models.CryptoCandle.timestamp >= start)
    if end:
        base_stmt = base_stmt.where(db_models.CryptoCandle.timestamp <= end)

    total_result = await session.execute(base_stmt.with_only_columns(db_models.CryptoCandle.id))
    total = len(total_result.scalars().all())

    stmt = base_stmt.order_by(desc(db_models.CryptoCandle.timestamp)).offset(offset).limit(limit)
    results = await session.execute(stmt)
    candles: Sequence[db_models.CryptoCandle] = results.scalars().unique().all()

    items = [
        CryptoCandleSummary(
            id=c.id,
            asset_id=c.asset_id,
            exchange_code=c.exchange.code if c.exchange else "",
            symbol=c.asset.symbol if c.asset else "",
            timeframe=str(c.timeframe),
            timestamp=c.timestamp,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume,
        )
        for c in candles
    ]

    next_offset = offset + len(items) if (offset + len(items)) < total else None
    return CryptoCandleListResponse(candles=items, total=total, next_offset=next_offset)


@router.get("/candles/{candle_id}", response_model=CryptoCandleSummary)
async def fetch_candle(
    candle_id: int,
    session: AsyncSession = Depends(get_db),
) -> CryptoCandleSummary:
    result = await session.execute(
        select(db_models.CryptoCandle)
        .options(
            selectinload(db_models.CryptoCandle.asset).selectinload(db_models.CryptoAsset.exchange),
        )
        .where(db_models.CryptoCandle.id == candle_id)
    )
    candle = result.scalar_one_or_none()
    if not candle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candle not found")

    return CryptoCandleSummary(
        id=candle.id,
        asset_id=candle.asset_id,
        exchange_code=candle.exchange.code if candle.exchange else "",
        symbol=candle.asset.symbol if candle.asset else "",
        timeframe=str(candle.timeframe),
        timestamp=candle.timestamp,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
    )


