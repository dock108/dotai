"""Common router utilities and patterns."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException
from pydantic import BaseModel

from py_core import (
    Domain,
    TheoryRequest,
    TheoryResponse,
    DataSource,
    evaluate_guardrails,
    has_hard_block,
    summarize_guardrails,
    compute_domain_verdict,
    ContextResult,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def evaluate_guardrails_and_context(
    req: TheoryRequest,
    domain: Domain,
    context_fetcher: Callable[[str], ContextResult] | None = None,
) -> tuple[list[str], ContextResult]:
    """Common pattern for evaluating guardrails and fetching context.
    
    Args:
        req: Theory request
        domain: Domain for evaluation
        context_fetcher: Optional context fetcher function
        
    Returns:
        Tuple of (guardrail_flags, context_result)
        
    Raises:
        HTTPException: If hard block detected
    """
    guardrail_results = evaluate_guardrails(req.text, domain)
    
    # Check for hard blocks
    if has_hard_block(guardrail_results):
        raise HTTPException(
            status_code=400,
            detail="This theory cannot be evaluated due to guardrail restrictions.",
        )
    
    guardrail_flags = summarize_guardrails(guardrail_results)
    
    # Fetch context if fetcher provided
    context = context_fetcher(req.text) if context_fetcher else ContextResult()
    
    return guardrail_flags, context


def build_data_used_list(context: ContextResult) -> list[DataSource]:
    """Build data_used list from context result.
    
    Args:
        context: Context result from fetcher
        
    Returns:
        List of data sources
    """
    data_used: list[DataSource] = []
    if context.data_source_name:
        data_used.append(DataSource(name=context.data_source_name, count=context.count))
    return data_used

