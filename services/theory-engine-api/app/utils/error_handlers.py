"""Common error handling utilities."""

import json

from fastapi import HTTPException, status


def create_parse_error_response(
    message: str = "Unable to understand your request. Please try rephrasing your query.",
    detail: str | None = None,
    suggestions: list[str] | None = None,
) -> HTTPException:
    """Create a standardized parse error response.
    
    Args:
        message: User-friendly error message
        detail: Additional details
        suggestions: List of suggestions for the user
    
    Returns:
        HTTPException with formatted error response
    """
    if suggestions is None:
        suggestions = [
            "Include a sport name (e.g., NFL, NBA, MLB)",
            "Specify a time period (e.g., 'last night', 'this week', 'November 2024')",
            "Be clear about what you want (e.g., 'highlights', 'bloopers', 'top plays')",
        ]
    
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=json.dumps({
            "error_code": "PARSE_ERROR",
            "message": message,
            "detail": detail or "We couldn't parse your request. Try being more specific about the sport, date, or content type.",
            "suggestions": suggestions,
        }),
        headers={"Content-Type": "application/json"},
    )


def create_configuration_error_response(
    message: str = "Service configuration error. Please contact support.",
    detail: str = "There was an issue with the AI parsing service.",
) -> HTTPException:
    """Create a standardized configuration error response.
    
    Args:
        message: User-friendly error message
        detail: Technical detail
    
    Returns:
        HTTPException with formatted error response
    """
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=json.dumps({
            "error_code": "CONFIGURATION_ERROR",
            "message": message,
            "detail": detail,
        }),
        headers={"Content-Type": "application/json"},
    )


def create_not_found_error_response(
    message: str = "Resource not found",
    detail: str | None = None,
) -> HTTPException:
    """Create a standardized not found error response.
    
    Args:
        message: User-friendly error message
        detail: Additional details
    
    Returns:
        HTTPException with formatted error response
    """
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=json.dumps({
            "error_code": "NOT_FOUND",
            "message": message,
            "detail": detail,
        }),
        headers={"Content-Type": "application/json"},
    )

