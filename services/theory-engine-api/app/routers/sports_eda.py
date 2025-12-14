"""Admin EDA endpoints for sports data.

This module mounts sub-routers for feature generation, analysis, modeling,
and walk-forward evaluation. All endpoints are admin-only.
"""
from __future__ import annotations

from fastapi import APIRouter

from .sports_eda_feature import router as feature_router
from .sports_eda_analyze import router as analyze_router
from .sports_eda_model import router as model_router
from .sports_eda_walkforward import router as walkforward_router

# Main router that includes all sub-routers
router = APIRouter()
router.include_router(feature_router)
router.include_router(analyze_router)
router.include_router(model_router)
router.include_router(walkforward_router)
