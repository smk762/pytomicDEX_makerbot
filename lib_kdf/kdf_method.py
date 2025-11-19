#!/usr/bin/env python3
"""
KDF Method utilities - Helper functions for KDF API methods.

This module provides utilities for working with KDF API request/response structures.
"""

from typing import Any, Dict, Optional


def extract_ticker_from_request(request_data: Dict[str, Any]) -> Optional[str]:
    """Extract the ticker symbol from a KDF API request.
    
    This function attempts to extract the ticker/coin symbol from various
    locations in the request structure where it might be found.
    
    Args:
        request_data: The KDF API request dictionary
        
    Returns:
        The ticker string if found, None otherwise
    """
    if not isinstance(request_data, dict):
        return None
    
    # Direct ticker field at root level
    if "ticker" in request_data:
        return request_data["ticker"]
    
    # Coin field at root level (some methods use this)
    if "coin" in request_data:
        return request_data["coin"]
    
    # Check in params dictionary
    params = request_data.get("params", {})
    if isinstance(params, dict):
        if "ticker" in params:
            return params["ticker"]
        if "coin" in params:
            return params["coin"]
        
        # Check in activation_params if present
        activation_params = params.get("activation_params", {})
        if isinstance(activation_params, dict):
            if "ticker" in activation_params:
                return activation_params["ticker"]
            if "coin" in activation_params:
                return activation_params["coin"]
    
    # Check in method name (some methods include coin ticker)
    method = request_data.get("method", "")
    if method:
        # Extract from methods like "enable_KMD" or similar patterns
        if method.startswith("enable_") and len(method) > 7:
            possible_ticker = method[7:]
            if possible_ticker.isupper() or possible_ticker.isalpha():
                return possible_ticker
    
    return None

