#!/usr/bin/env python3
"""
Coins Config Manager - Manages coin configuration data from coins_config.json

This module provides access to coin configurations including protocol information,
server URLs, and other metadata needed for coin activation.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class CoinProtocolInfo:
    """Protocol information for a coin."""
    protocol_type: str
    nodes: Optional[List[Dict[str, Any]]] = None
    rpc_urls: Optional[List[Dict[str, Any]]] = None
    electrum: Optional[List[Dict[str, Any]]] = None
    swap_contract_address: Optional[str] = None
    fallback_swap_contract: Optional[str] = None
    contract_address: Optional[str] = None
    required_confirmations: Optional[int] = None
    light_wallet_d_servers: Optional[List[str]] = None


class CoinsConfigManager:
    """Manages coin configuration data."""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """Initialize the config manager.
        
        Args:
            workspace_root: Path to workspace root (defaults to script directory)
        """
        if workspace_root is None:
            workspace_root = Path(__file__).parent
        
        self.workspace_root = Path(workspace_root)
        self.coins_config_path = self.workspace_root / "mm2" / "coins_config.json"
        
        # Fallback to alternative location if mm2/coins_config.json doesn't exist
        if not self.coins_config_path.exists():
            self.coins_config_path = self.workspace_root / "coins_config.json"
        
        self._coins_config: Optional[Dict[str, Any]] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load coins configuration from file."""
        if not self.coins_config_path.exists():
            raise FileNotFoundError(
                f"Coins config file not found at {self.coins_config_path}"
            )
        
        with open(self.coins_config_path, 'r', encoding='utf-8') as f:
            self._coins_config = json.load(f)
    
    def get_coin_config(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific coin.
        
        Args:
            ticker: The coin ticker (e.g., 'BTC', 'ETH', 'DGB-segwit')
            
        Returns:
            Dict with coin configuration or None if not found
        """
        if self._coins_config is None:
            return None
        
        # First try exact match (preserves case for special suffixes like -segwit)
        config = self._coins_config.get(ticker)
        if config:
            return config
        
        # Fallback to uppercase for backwards compatibility
        return self._coins_config.get(ticker.upper())
    
    def get_protocol_info(self, ticker: str) -> CoinProtocolInfo:
        """Get protocol information for a coin.
        
        Args:
            ticker: The coin ticker
            
        Returns:
            CoinProtocolInfo object with protocol details
        """
        config = self.get_coin_config(ticker)
        
        if not config:
            return CoinProtocolInfo(protocol_type="UNKNOWN")
        
        # Extract protocol type
        protocol_type = "UNKNOWN"
        protocol_data = config.get("protocol", {})
        
        if isinstance(protocol_data, dict):
            protocol_type = protocol_data.get("type", "UNKNOWN")
        
        # Map protocol types
        if protocol_type in ["UTXO", "UTXOSTANDARD"]:
            protocol_type = "UTXO"
        elif protocol_type in ["ERC20", "ETH", "ETHEREUM"]:
            protocol_type = "ETH"
        elif protocol_type in ["TENDERMINT", "TENDERMINTTOKEN"]:
            protocol_type = "TENDERMINT"
        elif protocol_type in ["ZHTLC", "ZCOIN"]:
            protocol_type = "ZHTLC"
        elif protocol_type == "SIA":
            protocol_type = "SIA"
        
        # Extract node/server information
        nodes = config.get("nodes", [])
        rpc_urls = config.get("rpc_urls", [])
        electrum = config.get("electrum", [])
        
        # Extract contract addresses
        swap_contract = config.get("swap_contract_address")
        fallback_swap = config.get("fallback_swap_contract")
        contract_address = config.get("contract_address")
        
        # Extract confirmations
        confirmations = config.get("required_confirmations")
        
        # Extract light wallet servers
        light_wallet_servers = config.get("light_wallet_d_servers", [])
        
        return CoinProtocolInfo(
            protocol_type=protocol_type,
            nodes=nodes if nodes else None,
            rpc_urls=rpc_urls if rpc_urls else None,
            electrum=electrum if electrum else None,
            swap_contract_address=swap_contract,
            fallback_swap_contract=fallback_swap,
            contract_address=contract_address,
            required_confirmations=confirmations,
            light_wallet_d_servers=light_wallet_servers if light_wallet_servers else None
        )
    
    def is_token(self, ticker: str) -> Tuple[bool, Optional[str]]:
        """Check if a ticker is a token and return its parent coin.
        
        Args:
            ticker: The coin/token ticker
            
        Returns:
            Tuple of (is_token: bool, parent_coin: Optional[str])
        """
        config = self.get_coin_config(ticker)
        
        if not config:
            return False, None
        
        # Check for parent_coin field (direct indicator)
        parent_coin = config.get("parent_coin")
        if parent_coin:
            return True, parent_coin
        
        # Check protocol type - tokens have specific protocol types
        protocol_data = config.get("protocol", {})
        if isinstance(protocol_data, dict):
            protocol_type = protocol_data.get("type", "")
            
            # ERC20 and similar token types
            if protocol_type in ["ERC20", "BEP20", "QRC20", "PLG20", "FTM20", "HRC20", "MVR20", "AVAX20", "AVX20"]:
                # Try to extract platform/parent from protocol_data
                protocol_info = protocol_data.get("protocol_data", {})
                platform = protocol_info.get("platform")
                if platform:
                    return True, platform
                # Fallback: try to infer from token suffix
                if "-" in ticker:
                    suffix = ticker.split("-")[-1]
                    if suffix == "ERC20":
                        return True, "ETH"
                    elif suffix == "BEP20":
                        return True, "BNB"
                    elif suffix == "PLG20":
                        return True, "MATIC"
                    # Add more mappings as needed
                return True, None
            
            # Tendermint tokens
            elif protocol_type == "TENDERMINTTOKEN":
                # Tendermint tokens usually have a platform field
                protocol_info = protocol_data.get("protocol_data", {})
                platform = protocol_info.get("platform")
                return True, platform
        
        return False, None
    
    def get_all_coins(self) -> List[str]:
        """Get list of all coin tickers.
        
        Returns:
            List of coin ticker strings
        """
        if self._coins_config is None:
            return []
        
        return list(self._coins_config.keys())
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        self._load_config()

