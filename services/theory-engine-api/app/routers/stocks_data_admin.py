"""Admin endpoints for stocks (equities) data ingestion and browsing."""

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

router = APIRouter(prefix="/api/admin/stocks", tags=["stocks-data"])


class StocksIngestionConfig(BaseModel):
    """Configuration for a stocks ingestion run."""

    model_config = ConfigDict(populate_by_name=True)

    exchange_code: str = Field(..., alias="exchangeCode")
    tickers: list[str] = Field(default_factory=list, alias="tickers")
    timeframe: str = Field(..., alias="timeframe")
    start: datetime | None = Field(None, alias="start")
    end: datetime | None = Field(None, alias="end")
    include_candles: bool = Field(True, alias="includeCandles")
    backfill_missing_candles: bool = Field(False, alias="backfillMissingCandles")

    def to_worker_payload(self) -> dict[str, Any]:
        return {
            "exchange_code": self.exchange_code,
            "tickers": self.tickers,
            "timeframe": self.timeframe,
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
            "include_candles": self.include_candles,
            "backfill_missing_candles": self.backfill_missing_candles,
        }


class StocksIngestionCreateRequest(BaseModel):
    config: StocksIngestionConfig
    requested_by: str | None = Field(None, alias="requestedBy")


class StocksIngestionRunResponse(BaseModel):
    id: int
    exchange_code: str
    status: str
    timeframe: str
    tickers: list[str]
    start_time: datetime | None
    end_time: datetime | None
    summary: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    requested_by: str | None
    config: dict[str, Any] | None = None


class EquityAssetSummary(BaseModel):
    id: int
    ticker: str
    name: str | None
    exchange_code: str
    sector: str | None
    industry: str | None


class EquityAssetDetail(BaseModel):
    id: int
    ticker: str
    name: str | None
    exchange_code: str
    sector: str | None
    industry: str | None
    metadata: dict[str, Any]


class EquityCandleSummary(BaseModel):
    id: int
    asset_id: int
    exchange_code: str
    ticker: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class EquityAssetListResponse(BaseModel):
    assets: list[EquityAssetSummary]
    total: int


class EquityCandleListResponse(BaseModel):
    candles: list[EquityCandleSummary]
    total: int
    next_offset: int | None


def _serialize_run(run: db_models.EquityIngestionRun) -> StocksIngestionRunResponse:
    """Serialize an equity ingestion run to API response."""
    return StocksIngestionRunResponse(
        id=run.id,
        exchange_code=run.exchange_code,
        status=run.status,
        timeframe=str(run.timeframe),
        tickers=run.tickers or [],
        start_time=run.start_time,
        end_time=run.end_time,
        summary=run.summary,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        requested_by=run.requested_by,
        config=run.config,
    )


@router.post("/ingestion/runs", response_model=StocksIngestionRunResponse)
async def create_ingestion_run(
    payload: StocksIngestionCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> StocksIngestionRunResponse:
    """Create and enqueue a new stocks ingestion run."""

    cfg = payload.config
    config_dict = cfg.model_dump(by_alias=False)
    if isinstance(config_dict.get("start"), datetime):
        config_dict["start"] = config_dict["start"].isoformat()
    if isinstance(config_dict.get("end"), datetime):
        config_dict["end"] = config_dict["end"].isoformat()

    run = db_models.EquityIngestionRun(
        exchange_code=cfg.exchange_code,
        tickers=cfg.tickers or [],
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
            "run_stocks_ingestion_job",
            args=[run.id, worker_payload],
            queue="stocks-worker",
            routing_key="stocks-worker",
        )
        run.job_id = async_result.id
    except Exception as exc:  # pragma: no cover
        from ..logging_config import get_logger

        logger = get_logger(__name__)
        logger.error("failed_to_enqueue_stocks_ingestion", error=str(exc), exc_info=True)
        run.status = "error"
        run.error_details = f"Failed to enqueue stocks ingestion job: {exc}"
        raise HTTPException(status_code=500, detail="Failed to enqueue stocks ingestion job") from exc

    return _serialize_run(run)


@router.get("/ingestion/runs", response_model=list[StocksIngestionRunResponse])
async def list_ingestion_runs(
    exchange: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    timeframe: str | None = Query(None),
    limit: int = Query(50, le=200),
    session: AsyncSession = Depends(get_db),
) -> list[StocksIngestionRunResponse]:
    stmt: Select[tuple[db_models.EquityIngestionRun]] = (
        select(db_models.EquityIngestionRun)
        .order_by(desc(db_models.EquityIngestionRun.created_at))
        .limit(limit)
    )
    if exchange:
        stmt = stmt.where(db_models.EquityIngestionRun.exchange_code == exchange.upper())
    if status_filter:
        stmt = stmt.where(db_models.EquityIngestionRun.status == status_filter)
    if timeframe:
        stmt = stmt.where(db_models.EquityIngestionRun.timeframe == timeframe)

    results = await session.execute(stmt)
    runs = results.scalars().all()
    return [_serialize_run(run) for run in runs]


@router.get("/ingestion/runs/{run_id}", response_model=StocksIngestionRunResponse)
async def fetch_ingestion_run(
    run_id: int,
    session: AsyncSession = Depends(get_db),
) -> StocksIngestionRunResponse:
    result = await session.execute(
        select(db_models.EquityIngestionRun).where(db_models.EquityIngestionRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return _serialize_run(run)


@router.get("/assets", response_model=EquityAssetListResponse)
async def list_assets(
    session: AsyncSession = Depends(get_db),
    exchange: str | None = Query(None),
    ticker_prefix: str | None = Query(None, alias="tickerPrefix"),
    sector: str | None = Query(None),
    industry: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> EquityAssetListResponse:
    base_stmt: Select[tuple[db_models.EquityAsset]] = select(db_models.EquityAsset).options(
        selectinload(db_models.EquityAsset.exchange),
    )

    if exchange:
        base_stmt = base_stmt.join(db_models.EquityExchange).where(
            db_models.EquityExchange.code == exchange.upper()
        )
    if ticker_prefix:
        like_pattern = f"{ticker_prefix.upper()}%"
        base_stmt = base_stmt.where(db_models.EquityAsset.ticker.ilike(like_pattern))
    if sector:
        base_stmt = base_stmt.where(db_models.EquityAsset.sector == sector)
    if industry:
        base_stmt = base_stmt.where(db_models.EquityAsset.industry == industry)

    total_result = await session.execute(base_stmt.with_only_columns(db_models.EquityAsset.id))
    total = len(total_result.scalars().all())

    stmt = base_stmt.order_by(db_models.EquityAsset.ticker).offset(offset).limit(limit)
    results = await session.execute(stmt)
    assets: Sequence[db_models.EquityAsset] = results.scalars().unique().all()

    summaries = [
        EquityAssetSummary(
            id=a.id,
            ticker=a.ticker,
            name=a.name,
            exchange_code=a.exchange.code if a.exchange else "",
            sector=a.sector,
            industry=a.industry,
        )
        for a in assets
    ]
    return EquityAssetListResponse(assets=summaries, total=total)


@router.get("/assets/{asset_id}", response_model=EquityAssetDetail)
async def fetch_asset(
    asset_id: int,
    session: AsyncSession = Depends(get_db),
) -> EquityAssetDetail:
    result = await session.execute(
        select(db_models.EquityAsset)
        .options(selectinload(db_models.EquityAsset.exchange))
        .where(db_models.EquityAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    return EquityAssetDetail(
        id=asset.id,
        ticker=asset.ticker,
        name=asset.name,
        exchange_code=asset.exchange.code if asset.exchange else "",
        sector=asset.sector,
        industry=asset.industry,
        metadata=asset.extra_metadata or {},
    )


@router.get("/candles", response_model=EquityCandleListResponse)
async def list_candles(
    session: AsyncSession = Depends(get_db),
    asset_id: int | None = Query(None, alias="assetId"),
    ticker: str | None = Query(None),
    exchange: str | None = Query(None),
    timeframe: str | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> EquityCandleListResponse:
    base_stmt = (
        select(db_models.EquityCandle)
        .options(
            selectinload(db_models.EquityCandle.asset).selectinload(db_models.EquityAsset.exchange),
        )
    )

    if asset_id is not None:
        base_stmt = base_stmt.where(db_models.EquityCandle.asset_id == asset_id)
    if ticker:
        base_stmt = base_stmt.join(db_models.EquityAsset).where(
            db_models.EquityAsset.ticker == ticker.upper()
        )
    if exchange:
        base_stmt = base_stmt.join(db_models.EquityExchange).where(
            db_models.EquityExchange.code == exchange.upper()
        )
    if timeframe:
        base_stmt = base_stmt.where(db_models.EquityCandle.timeframe == timeframe)
    if start:
        base_stmt = base_stmt.where(db_models.EquityCandle.timestamp >= start)
    if end:
        base_stmt = base_stmt.where(db_models.EquityCandle.timestamp <= end)

    total_result = await session.execute(base_stmt.with_only_columns(db_models.EquityCandle.id))
    total = len(total_result.scalars().all())

    stmt = base_stmt.order_by(desc(db_models.EquityCandle.timestamp)).offset(offset).limit(limit)
    results = await session.execute(stmt)
    candles: Sequence[db_models.EquityCandle] = results.scalars().unique().all()

    items = [
        EquityCandleSummary(
            id=c.id,
            asset_id=c.asset_id,
            exchange_code=c.exchange.code if c.exchange else "",
            ticker=c.asset.ticker if c.asset else "",
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
    return EquityCandleListResponse(candles=items, total=total, next_offset=next_offset)


@router.get("/candles/{candle_id}", response_model=EquityCandleSummary)
async def fetch_candle(
    candle_id: int,
    session: AsyncSession = Depends(get_db),
) -> EquityCandleSummary:
    result = await session.execute(
        select(db_models.EquityCandle)
        .options(
            selectinload(db_models.EquityCandle.asset).selectinload(db_models.EquityAsset.exchange),
        )
        .where(db_models.EquityCandle.id == candle_id)
    )
    candle = result.scalar_one_or_none()
    if not candle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candle not found")

    return EquityCandleSummary(
        id=candle.id,
        asset_id=candle.asset_id,
        exchange_code=candle.exchange.code if candle.exchange else "",
        ticker=candle.asset.ticker if candle.asset else "",
        timeframe=str(candle.timeframe),
        timestamp=candle.timestamp,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
    )


