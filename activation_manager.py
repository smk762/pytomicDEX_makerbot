#!/usr/bin/env python3
"""
Activation Manager - Comprehensive coin and token activation for KDF.

This module provides intelligent coin activation based on protocol detection
and proper handling of tokens, platform dependencies, and task lifecycles.
"""

import os
import json
import time
import threading
import random
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List, Callable
from dataclasses import dataclass

# Import the coins config manager
try:
    # Try relative import first (when used as module)
    from .coins_config_manager import CoinsConfigManager, CoinProtocolInfo
    from ..lib_kdf.kdf_method import extract_ticker_from_request
except ImportError:
    # Fall back to absolute import (when run directly)
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    from coins_config_manager import CoinsConfigManager, CoinProtocolInfo
    sys.path.append(str(Path(__file__).parent.parent))
    from lib_kdf.kdf_method import extract_ticker_from_request

logger = logging.getLogger(__name__)



# Configuration for activation state tracking
ACTIVATION_STATE: Dict[str, Dict[str, Any]] = {}

@dataclass
class ActivationRequest:
    """Represents a coin activation request."""
    method: str
    params: Dict[str, Any]
    timeout: int = 60
    is_task: bool = False
    
@dataclass  
class ActivationResult:
    """Result of a coin activation attempt."""
    success: bool
    response: Dict[str, Any]
    task_id: Optional[str] = None
    error: Optional[str] = None
    already_enabled: bool = False


class ActivationRequestBuilder:
    """Builds activation requests for different coin types and protocols."""
    
    def __init__(self, coins_config_manager: CoinsConfigManager, userpass: str):
        self.coins_config = coins_config_manager
        self.userpass = userpass
        self.logger = logger
    
    def _select_preferred_servers(self, servers: List[Dict[str, Any]], max_count: int = 3) -> List[Dict[str, Any]]:
        """Select up to max_count servers, preferring cipig/komodo domains."""
        if len(servers) <= max_count:
            return servers
        
        # Separate servers into priority and non-priority
        priority_servers = []
        regular_servers = []
        
        for server in servers:
            url = server.get('url', '')
            if 'cipig' in url.lower() or 'komodo' in url.lower():
                priority_servers.append(server)
            else:
                regular_servers.append(server)
        
        selected_servers = []
        
        # First, add priority servers (up to max_count)
        if priority_servers:
            if len(priority_servers) <= max_count:
                selected_servers.extend(priority_servers)
            else:
                selected_servers.extend(random.sample(priority_servers, max_count))
        
        # If we need more servers and have regular ones available
        remaining_slots = max_count - len(selected_servers)
        if remaining_slots > 0 and regular_servers:
            if len(regular_servers) <= remaining_slots:
                selected_servers.extend(regular_servers)
            else:
                selected_servers.extend(random.sample(regular_servers, remaining_slots))
        
        self.logger.info(f"Selected {len(selected_servers)} servers from {len(servers)} available")
        return selected_servers

    # Public wrappers for reuse outside activation requests
    def select_preferred_servers(self, servers: List[Dict[str, Any]], max_count: int = 3) -> List[Dict[str, Any]]:
        """Public helper to select preferred servers (cipig/komodo prioritized)."""
        return self._select_preferred_servers(servers, max_count)

    def select_preferred_urls(self, urls: List[str], max_count: int = 3) -> List[str]:
        """Select up to max_count URLs, preferring cipig/komodo domains."""
        if len(urls) <= max_count:
            return urls
        priority_urls: List[str] = []
        regular_urls: List[str] = []
        for url in urls:
            if isinstance(url, str) and ("cipig" in url.lower() or "komodo" in url.lower()):
                priority_urls.append(url)
            else:
                regular_urls.append(url)
        selected: List[str] = []
        if priority_urls:
            if len(priority_urls) <= max_count:
                selected.extend(priority_urls)
            else:
                selected.extend(random.sample(priority_urls, max_count))
        remaining = max_count - len(selected)
        if remaining > 0 and regular_urls:
            if len(regular_urls) <= remaining:
                selected.extend(regular_urls)
            else:
                selected.extend(random.sample(regular_urls, remaining))
        return selected

    # -------- Generic request node update helpers (for CLI/tools reuse) --------

    def update_tendermint_nodes_in_request(self, request_data: Dict[str, Any], protocol_info: CoinProtocolInfo, ticker: str) -> bool:
        if not protocol_info.rpc_urls:
            self.logger.warning(f"No rpc_urls found for Tendermint ticker '{ticker}' in coins configuration")
            return False
        selected_rpc_urls = self.select_preferred_servers(protocol_info.rpc_urls, max_count=3)
        new_nodes: List[Dict[str, Any]] = []
        for rpc_url in selected_rpc_urls:
            node: Dict[str, Any] = {"url": rpc_url.get("url")}
            for field in ['api_url', 'grpc_url', 'ws_url', 'komodo_proxy']:
                if rpc_url.get(field):
                    node[field] = rpc_url.get(field)
            if node.get("url"):
                new_nodes.append(node)
        if 'params' in request_data and isinstance(request_data['params'], dict):
            params = request_data['params']
            if 'nodes' in params:
                old_nodes = params['nodes']
                params['nodes'] = new_nodes
                self.logger.info(f"Updated Tendermint nodes for '{ticker}': {len(old_nodes)} -> {len(new_nodes)} nodes")
                return True
        if 'nodes' in request_data:
            old_nodes = request_data['nodes']
            request_data['nodes'] = new_nodes
            self.logger.info(f"Updated Tendermint nodes for '{ticker}': {len(old_nodes)} -> {len(new_nodes)} nodes")
            return True
        return False

    def update_utxo_electrum_in_request(self, request_data: Dict[str, Any], protocol_info: CoinProtocolInfo, ticker: str) -> bool:
        if not protocol_info.electrum:
            self.logger.warning(f"No electrum servers found for UTXO ticker '{ticker}' in coins configuration")
            return False
        # Wasm requests should use WSS servers; others prefer SSL then TCP
        prefer_wss = self._is_wasm_mode(request_data)
        selected = self._filter_electrum_servers_with_mode(protocol_info.electrum, prefer_wss=prefer_wss)
        new_servers: List[Dict[str, Any]] = []
        for e in selected:
            server: Dict[str, Any] = {"url": e.get("url")}
            if e.get('protocol'):
                server['protocol'] = e.get('protocol')
            for field in ['ws_url', 'disable_cert_verification']:
                if e.get(field) is not None:
                    server[field] = e.get(field)
            new_servers.append(server)
        if 'params' in request_data and isinstance(request_data['params'], dict):
            params = request_data['params']
            if 'activation_params' in params and 'mode' in params['activation_params']:
                mode = params['activation_params']['mode']
                if 'rpc_data' in mode and 'servers' in mode['rpc_data']:
                    old = mode['rpc_data']['servers']
                    mode['rpc_data']['servers'] = new_servers
                    self.logger.info(f"Updated UTXO electrum servers for '{ticker}': {len(old)} -> {len(new_servers)} servers")
                    return True
            if 'mode' in params and 'rpc_data' in params['mode'] and 'servers' in params['mode']['rpc_data']:
                old = params['mode']['rpc_data']['servers']
                params['mode']['rpc_data']['servers'] = new_servers
                self.logger.info(f"Updated UTXO electrum servers for '{ticker}': {len(old)} -> {len(new_servers)} servers")
                return True
        else:
            if request_data.get('method') == 'electrum' and 'servers' in request_data:
                old = request_data['servers']
                request_data['servers'] = new_servers
                self.logger.info(f"Updated UTXO electrum servers for '{ticker}': {len(old)} -> {len(new_servers)} servers")
                return True
            if request_data.get('method') == 'enable' and 'urls' in request_data:
                old = request_data['urls']
                request_data['urls'] = [s['url'] for s in new_servers]
                self.logger.info(f"Updated UTXO electrum urls for '{ticker}': {len(old)} -> {len(new_servers)} servers")
                return True
        return False

    def update_zhtlc_in_request(self, request_data: Dict[str, Any], protocol_info: CoinProtocolInfo, ticker: str) -> bool:
        updated = False
        # Detect Wasm vs non-Wasm
        prefer_wss = self._is_wasm_mode(request_data)
        # light_wallet_d_servers
        light_servers: List[str] = []
        try:
            coin_config = self.coins_config.get_coin_config(ticker)
            if coin_config:
                lw_key = 'light_wallet_d_servers_wss' if prefer_wss else 'light_wallet_d_servers'
                lw_servers = coin_config.get(lw_key) or []
                if isinstance(lw_servers, list) and lw_servers:
                    light_servers = self.select_preferred_urls(lw_servers, max_count=3)
        except Exception:
            pass
        if light_servers:
            if 'params' in request_data and isinstance(request_data['params'], dict):
                params = request_data['params']
                if 'activation_params' in params and 'mode' in params['activation_params']:
                    mode = params['activation_params']['mode']
                    if 'rpc_data' in mode and 'light_wallet_d_servers' in mode['rpc_data']:
                        old = mode['rpc_data']['light_wallet_d_servers']
                        mode['rpc_data']['light_wallet_d_servers'] = light_servers
                        self.logger.info(f"Updated ZHTLC light_wallet_d_servers for '{ticker}': {len(old)} -> {len(light_servers)} servers")
                        updated = True
                elif 'mode' in params and 'rpc_data' in params['mode'] and 'light_wallet_d_servers' in params['mode']['rpc_data']:
                    old = params['mode']['rpc_data']['light_wallet_d_servers']
                    params['mode']['rpc_data']['light_wallet_d_servers'] = light_servers
                    self.logger.info(f"Updated ZHTLC light_wallet_d_servers for '{ticker}': {len(old)} -> {len(light_servers)} servers")
                    updated = True
        # electrum_servers
        if protocol_info.electrum:
            # Wasm requests should use WSS servers; others prefer SSL then TCP
            selected = self._filter_electrum_servers_with_mode(protocol_info.electrum, prefer_wss=prefer_wss)
            new_electrum: List[Dict[str, Any]] = []
            for e in selected:
                server: Dict[str, Any] = {"url": e.get("url")}
                if e.get('protocol'):
                    server['protocol'] = e.get('protocol')
                if e.get('ws_url'):
                    server['ws_url'] = e.get('ws_url')
                new_electrum.append(server)
            if 'params' in request_data and isinstance(request_data['params'], dict):
                params = request_data['params']
                if 'activation_params' in params and 'mode' in params['activation_params']:
                    mode = params['activation_params']['mode']
                    if 'rpc_data' in mode and 'electrum_servers' in mode['rpc_data']:
                        old = mode['rpc_data']['electrum_servers']
                        mode['rpc_data']['electrum_servers'] = new_electrum
                        self.logger.info(f"Updated ZHTLC electrum_servers for '{ticker}': {len(old)} -> {len(new_electrum)} servers")
                        updated = True
                elif 'mode' in params and 'rpc_data' in params['mode'] and 'electrum_servers' in params['mode']['rpc_data']:
                    old = params['mode']['rpc_data']['electrum_servers']
                    params['mode']['rpc_data']['electrum_servers'] = new_electrum
                    self.logger.info(f"Updated ZHTLC electrum_servers for '{ticker}': {len(old)} -> {len(new_electrum)} servers")
                    updated = True
        return updated

    def update_eth_nodes_in_request(self, request_data: Dict[str, Any], protocol_info: CoinProtocolInfo, ticker: str) -> bool:
        if not protocol_info.nodes:
            self.logger.warning(f"No nodes found for ETH ticker '{ticker}' in coins configuration")
            return False
        selected = self.select_preferred_servers(protocol_info.nodes, max_count=3)
        new_nodes: List[Dict[str, Any]] = []
        for n in selected:
            node: Dict[str, Any] = {"url": n.get("url")}
            for field in ['ws_url', 'komodo_proxy']:
                if n.get(field):
                    node[field] = n.get(field)
            new_nodes.append(node)
        if 'params' in request_data and isinstance(request_data['params'], dict):
            params = request_data['params']
            if 'nodes' in params:
                old = params['nodes']
                params['nodes'] = new_nodes
                self.logger.info(f"Updated ETH nodes for '{ticker}': {len(old)} -> {len(new_nodes)} nodes")
                return True
        if 'nodes' in request_data:
            old = request_data['nodes']
            request_data['nodes'] = new_nodes
            self.logger.info(f"Updated ETH nodes for '{ticker}': {len(old)} -> {len(new_nodes)} nodes")
            return True
        if request_data.get('method') == 'enable' and 'urls' in request_data:
            old_urls = request_data['urls']
            request_data['urls'] = [i['url'] for i in new_nodes]
            self.logger.info(f"Updated ETH urls for '{ticker}': {len(old_urls)} -> {len(new_nodes)} nodes")
            return True
        return False

    def update_nodes_in_request(self, request_data: Dict[str, Any], request_name: str = "Unknown") -> bool:
        ticker = extract_ticker_from_request(request_data)
        if not ticker:
            self.logger.info(f"No ticker found in request '{request_name}'")
            return False
        # Preserve original ticker case for special suffixes like -segwit
        protocol_info = self.coins_config.get_protocol_info(ticker)
        protocol = protocol_info.protocol_type or 'UNKNOWN'
        self.logger.info(f"Detected protocol '{protocol}' for ticker '{ticker}' via CoinsConfigManager")
        if protocol == 'TENDERMINT':
            return self.update_tendermint_nodes_in_request(request_data, protocol_info, ticker)
        if protocol == 'UTXO':
            return self.update_utxo_electrum_in_request(request_data, protocol_info, ticker)
        if protocol == 'ZHTLC':
            return self.update_zhtlc_in_request(request_data, protocol_info, ticker)
        if protocol == 'ETH':
            return self.update_eth_nodes_in_request(request_data, protocol_info, ticker)
        self.logger.warning(f"Unknown or unsupported protocol '{protocol}' for ticker '{ticker}'")
        return False


    def _normalize_eth_nodes(self, nodes: Optional[List[Any]]) -> List[Dict[str, str]]:
        """Normalize ETH node list format."""
        norm: List[Dict[str, str]] = []
        for n in nodes or []:
            if isinstance(n, dict) and n.get("url"):
                node = {"url": n["url"]}
                # Preserve additional fields
                for field in ['ws_url', 'komodo_proxy']:
                    if field in n:
                        node[field] = n[field]
                norm.append(node)
            elif isinstance(n, str):
                norm.append({"url": n})
        return norm
    
    def _normalize_tendermint_nodes(self, protocol_info: CoinProtocolInfo) -> List[Dict[str, str]]:
        """Normalize Tendermint node list format."""
        nodes: List[Dict[str, str]] = []
        
        if protocol_info.rpc_urls:
            for e in protocol_info.rpc_urls:
                if isinstance(e, dict):
                    node: Dict[str, str] = {}
                    if e.get("url"):
                        node["url"] = e.get("url")
                    # Preserve additional fields
                    for field in ['api_url', 'grpc_url', 'ws_url', 'komodo_proxy']:
                        if e.get(field):
                            node[field] = e.get(field)
                    if node.get("url"):
                        nodes.append(node)
                elif isinstance(e, str):
                    nodes.append({"url": e})
        
        # Fallback to nodes field if no rpc_urls
        if not nodes and protocol_info.nodes:
            for n in protocol_info.nodes:
                if isinstance(n, dict) and n.get("url"):
                    nodes.append({"url": n.get("url")})
        
        return nodes
    
    def _is_wasm_mode(self, request_data: Dict[str, Any]) -> bool:
        """Detect whether the incoming request should be treated as Wasm.
        
        The updater script sets a transient flag `__wasm` on request objects whose
        names include "Wasm". We rely exclusively on that flag here.
        """
        try:
            if request_data.get("__wasm") is True:
                return True
            params = request_data.get("params", {})
            if isinstance(params, dict) and params.get("__wasm") is True:
                return True
        except Exception:
            pass
        return False

    def _filter_electrum_servers_with_mode(self, servers: Optional[List[Any]], prefer_wss: bool) -> List[Dict[str, Any]]:
        """Filter electrum servers based on whether WSS is preferred (Wasm) or not.
        
        - When prefer_wss is True: include only WSS servers, prioritize cipig/komodo, cap at 3.
        - When prefer_wss is False: exclude WSS, prefer SSL then TCP, prioritize cipig/komodo, cap at 3.
        """
        if not isinstance(servers, list):
            return []
        
        wss_list: List[Dict[str, Any]] = []
        ssl_list: List[Dict[str, Any]] = []
        tcp_list: List[Dict[str, Any]] = []
        other_list: List[Dict[str, Any]] = []
        
        for s in servers:
            if not isinstance(s, dict):
                continue
            url = s.get("url")
            proto_val = s.get("protocol") or s.get("proto") or ""
            proto = str(proto_val).upper()
            if not url:
                continue
            if proto == "WSS":
                wss_list.append(s)
            elif proto == "SSL":
                ssl_list.append(s)
            elif proto == "TCP":
                tcp_list.append(s)
            else:
                other_list.append(s)
        
        def prioritize_cipig(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            cipig: List[Dict[str, Any]] = []
            rest: List[Dict[str, Any]] = []
            for item in items:
                url_val = str(item.get("url", "")).lower()
                if "cipig" in url_val or "komodo" in url_val:
                    cipig.append(item)
                else:
                    rest.append(item)
            return cipig + rest
        
        if prefer_wss:
            return prioritize_cipig(wss_list)[:3]
        
        ssl_ordered = prioritize_cipig(ssl_list)
        tcp_ordered = prioritize_cipig(tcp_list)
        ordered = ssl_ordered + tcp_ordered + prioritize_cipig(other_list)
        return ordered[:3]

    def _filter_electrum_servers(self, servers: Optional[List[Any]]) -> List[Dict[str, Any]]:
        """Filter and limit electrum servers: drop WSS, prefer SSL over TCP, prioritize cipig, cap at 3."""
        if not isinstance(servers, list):
            return []
        
        ssl_list: List[Dict[str, Any]] = []
        tcp_list: List[Dict[str, Any]] = []
        other_list: List[Dict[str, Any]] = []
        
        for s in servers:
            if not isinstance(s, dict):
                continue
            url = s.get("url")
            proto_val = s.get("protocol") or s.get("proto") or ""
            proto = str(proto_val).upper()
            if not url:
                continue
            if proto == "WSS":
                continue
            if proto == "SSL":
                ssl_list.append(s)
            elif proto == "TCP":
                tcp_list.append(s)
            else:
                other_list.append(s)
        
        def prioritize_cipig(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            cipig: List[Dict[str, Any]] = []
            rest: List[Dict[str, Any]] = []
            for item in items:
                url_val = str(item.get("url", "")).lower()
                if "cipig" in url_val:
                    cipig.append(item)
                else:
                    rest.append(item)
            return cipig + rest
        
        ssl_ordered = prioritize_cipig(ssl_list)
        tcp_ordered = prioritize_cipig(tcp_list)
        ordered = ssl_ordered + tcp_ordered + prioritize_cipig(other_list)
        return ordered[:3]


    def build_activation_request(self, ticker: str, enable_hd: bool = True) -> ActivationRequest:
        """Build activation request for a coin based on its protocol.
        
        Args:
            ticker: The coin ticker to activate.
            enable_hd: Whether to use HD wallet mode (for non-HD instances, set False).
            
        Returns:
            ActivationRequest object with method and parameters.
        """
        # Preserve original ticker case for special suffixes like -segwit
        protocol_info = self.coins_config.get_protocol_info(ticker)
        
        if protocol_info.protocol_type == "ETH":
            return self._build_eth_activation(ticker, protocol_info)
        elif protocol_info.protocol_type == "TENDERMINT":
            return self._build_tendermint_activation(ticker, protocol_info)
        elif protocol_info.protocol_type == "UTXO":
            return self._build_utxo_activation(ticker, protocol_info, enable_hd)
        elif protocol_info.protocol_type == "ZHTLC":
            return self._build_zhtlc_activation(ticker, protocol_info, enable_hd)
        elif protocol_info.protocol_type == "SIA":
            return self._build_sia_activation(ticker, protocol_info)
        else:
            raise ValueError(f"Unsupported protocol type: {protocol_info.protocol_type} for ticker: {ticker}")
    
    def _build_eth_activation(self, ticker: str, protocol_info: CoinProtocolInfo) -> ActivationRequest:
        """Build ETH-like coin activation request."""
        params = {
            "ticker": ticker,
            "tx_history": True,
            "get_balances": True,
            "erc20_tokens_requests": [],
        }
        
        # Add nodes if available
        if protocol_info.nodes:
            nodes = self._normalize_eth_nodes(protocol_info.nodes)
            selected_nodes = self._select_preferred_servers(nodes, max_count=3)
            if selected_nodes:
                params["nodes"] = selected_nodes
        
        # Add swap contract addresses
        if protocol_info.swap_contract_address:
            params["swap_contract_address"] = protocol_info.swap_contract_address
        if protocol_info.fallback_swap_contract:
            params["fallback_swap_contract"] = protocol_info.fallback_swap_contract
        
        return ActivationRequest(
            method="task::enable_eth::init",
            params=params,
            timeout=60,
            is_task=True
        )
    
    def _build_tendermint_activation(self, ticker: str, protocol_info: CoinProtocolInfo) -> ActivationRequest:
        """Build Tendermint-like coin activation request."""
        params = {
            "ticker": ticker,
            "tx_history": False,
            "get_balances": True,
            "tokens_params": []
        }
        
        # Add nodes from rpc_urls or nodes
        nodes = self._normalize_tendermint_nodes(protocol_info)
        if nodes:
            selected_nodes = self._select_preferred_servers(nodes, max_count=3)
            if selected_nodes:
                params["nodes"] = selected_nodes
                
        return ActivationRequest(
            method="task::enable_tendermint::init",
            params=params,
            timeout=60,
            is_task=True
        )

    def _build_sia_activation(self, ticker: str, protocol_info: CoinProtocolInfo) -> ActivationRequest:
        """Build SIA coin activation request."""
        # Get server URL from nodes configuration
        server_url = "Not found for {ticker} in coins_config.json!"
        
        if protocol_info.nodes:
            # Use the first node URL from configuration
            nodes = self._normalize_eth_nodes(protocol_info.nodes)
            if nodes and nodes[0].get("url"):
                server_url = nodes[0]["url"]
        
        # Get required confirmations from protocol info or use default
        required_confirmations = protocol_info.required_confirmations or 3
        
        # Use params aligned with v2 request template
        params = {
            "activation_params": {
                "client_conf": {
                    "headers": {},
                    "server_url": server_url
                },
                "required_confirmations": required_confirmations,
                "tx_history": True
            },
            "client_id": 0,
            "ticker": ticker
        }
        return ActivationRequest(
            method="task::enable_sia::init",
            params=params,
            timeout=60,
            is_task=True
        )
    
    def _build_utxo_activation(self, ticker: str, protocol_info: CoinProtocolInfo, enable_hd: bool = True) -> ActivationRequest:
        """Build UTXO coin activation request."""
        # Filter and select electrum servers
        electrum_servers = self._filter_electrum_servers(protocol_info.electrum)
        
        params = {
            "ticker": ticker,
            "tx_history": True,
            "get_balances": True,
            "activation_params": {
                "mode": {
                    "rpc": "Electrum",
                    "rpc_data": {
                        "servers": electrum_servers
                    },
                }
            },
        }
        
        # Add HD wallet parameters for HD instances
        if enable_hd:
            params["activation_params"]["path_to_address"] = {
                "account_id": 0,  # This is where account_id should be
                "address_id": 0,
                "chain": "External"
            }
            params["activation_params"]["scan_policy"] = "scan_if_new_wallet"
            params["activation_params"]["gap_limit"] = 20
            params["activation_params"]["min_addresses_number"] = 3
            params["activation_params"]["priv_key_policy"] = "ContextPrivKey"
        
        return ActivationRequest(
            method="task::enable_utxo::init",
            params=params,
            timeout=60,
            is_task=True
        )
    
    def _build_zhtlc_activation(self, ticker: str, protocol_info: CoinProtocolInfo, enable_hd: bool = True) -> ActivationRequest:
        """Build ZHTLC coin activation request."""
        activation_params = {
            "mode": {
                "rpc": "Native",
                "rpc_data": {}
            }
        }
        
        # Add light wallet servers if available
        if hasattr(protocol_info, 'light_wallet_d_servers') and protocol_info.light_wallet_d_servers:
            # Get from coin config since it's not in CoinProtocolInfo
            coin_config = self.coins_config.get_coin_config(ticker)
            light_wallet_servers = coin_config.get('light_wallet_d_servers', [])
            if light_wallet_servers:
                # Select up to 3 servers
                selected_servers = light_wallet_servers[:3]
                activation_params["mode"]["rpc_data"]["light_wallet_d_servers"] = selected_servers
        
        # Add electrum servers if available
        if protocol_info.electrum:
            electrum_servers = self._filter_electrum_servers(protocol_info.electrum)
            if electrum_servers:
                activation_params["mode"]["rpc_data"]["electrum_servers"] = electrum_servers
        
        params = {
            "ticker": ticker,
            "tx_history": True,
            "get_balances": True,
            "activation_params": activation_params,
        }
        
        # Add HD wallet parameters for HD instances
        if enable_hd:
            params["activation_params"]["path_to_address"] = {
                "account_id": 0,
                "address_id": 0,
                "chain": "External"
            }
            params["activation_params"]["scan_policy"] = "scan_if_new_wallet"
            params["activation_params"]["gap_limit"] = 20
            params["activation_params"]["min_addresses_number"] = 3
            params["activation_params"]["priv_key_policy"] = "ContextPrivKey"
        
        return ActivationRequest(
            method="task::enable_utxo::init",  # ZHTLC uses UTXO activation
            params=params,
            timeout=60,
            is_task=True
        )


# ----- Token activation helpers -----

    def build_token_activation_request(self, ticker: str) -> Tuple[ActivationRequest, Optional[str]]:
        """Build token activation request and return parent coin.
        
        Args:
            ticker: The token ticker to activate.
            
        Returns:
            Tuple of (ActivationRequest, parent_coin_ticker)
        """
        # Preserve original ticker case
        is_token, parent_coin = self.coins_config.is_token(ticker)
        
        if not is_token:
            raise ValueError(f"Ticker {ticker} is not recognized as a token")
        
        protocol_info = self.coins_config.get_protocol_info(ticker)
        
        # Determine if it's an ERC20-like token or Tendermint token
        is_evm_token = (
            ticker.upper().endswith("-ERC20") or 
            protocol_info.contract_address is not None or
            parent_coin == "ETH"
        )
        
        if is_evm_token:
            params = {
                "ticker": ticker,
                "activation_params": {},
            }
            
            # Add required confirmations if specified
            if protocol_info.required_confirmations is not None:
                try:
                    params["activation_params"]["required_confirmations"] = int(protocol_info.required_confirmations)
                except (ValueError, TypeError):
                    pass
            
            return ActivationRequest(
                method="enable_erc20",
                params=params,
                timeout=30,
                is_task=False
            ), parent_coin
        else:
            # Tendermint token (IBC)
            params = {
                "ticker": ticker,
                "activation_params": {},
            }
            
            # Add required confirmations if specified
            if protocol_info.required_confirmations is not None:
                try:
                    params["activation_params"]["required_confirmations"] = int(protocol_info.required_confirmations)
                except (ValueError, TypeError):
                    pass
            
            return ActivationRequest(
                method="enable_tendermint_token",
                params=params,
                timeout=30,
                is_task=False
            ), parent_coin


class ActivationManager:
    """Manages coin and token activation with intelligent protocol detection."""

    def __init__(self, rpc_func: Callable[[str, Dict[str, Any]], Dict[str, Any]], 
                 userpass: str, workspace_root: Optional[Path] = None,
                 instance_name: str = "default"):
        """Initialize the activation manager.
        
        Args:
            rpc_func: Callable for making RPC requests (method, params) -> response
            userpass: The userpass for RPC authentication
            workspace_root: Path to workspace root for config management
        """
        self.rpc_func = rpc_func
        self.userpass = userpass
        self.logger = logger
        self.instance_name = instance_name
        
        # Initialize config and request builder
        self.coins_config = CoinsConfigManager(workspace_root)
        self.request_builder = ActivationRequestBuilder(self.coins_config, userpass)

    def _state_key(self, ticker: str) -> str:
        """Namespaced activation state key per instance."""
        return f"{self.instance_name}:{str(ticker).upper()}"

    @staticmethod
    def _status_method_for_init(method: str) -> Optional[str]:
        """Get the status method for a task init method."""
        if "enable_eth::init" in method:
            return "task::enable_eth::status"
        if "enable_tendermint::init" in method:
            return "task::enable_tendermint::status"
        if "enable_utxo::init" in method:
            return "task::enable_utxo::status"
        if "enable_sia::init" in method:
            return "task::enable_sia::status"
        return None

    def _poll_task(self, ticker: str, status_method: str, task_id: Any) -> None:
        """Poll task status until completion or failure."""
        key = self._state_key(ticker)
        max_polls = 40  # 200 seconds at 5 second intervals
        poll_count = 0
        
        while poll_count < max_polls:
            try:
                # Make status request
                status_params = {"task_id": task_id, "forget_if_finished": False}
                status_response = self.rpc_func(status_method, status_params) or {}
                
                # Update state
                ACTIVATION_STATE.setdefault(key, {})
                ACTIVATION_STATE[key].update({"status_raw": status_response, "poll_count": poll_count})
                
                # Extract status
                status_val = None
                if isinstance(status_response, dict):
                    result = status_response.get("result")
                    if isinstance(result, dict):
                        status_val = result.get("status") or result.get("state")
                        
                        # Check if task is complete
                        if status_val == "Ok":
                            ACTIVATION_STATE[key].update({
                                "status": "enabled", 
                                "completed_at": time.time(), 
                                "result": status_response
                            })
                            self.logger.info(f"Coin {ticker} activation completed successfully")
                            return
                        elif status_val == "Error":
                            error_details = result.get("details", "Unknown error")
                            ACTIVATION_STATE[key].update({
                                "status": "failed", 
                                "failed_at": time.time(), 
                                "result": status_response,
                                "error": error_details
                            })
                            self.logger.error(f"Coin {ticker} activation failed: {error_details}")
                            return
                    else:
                        # Handle case where result is the final response
                        ACTIVATION_STATE[key].update({
                            "status": "enabled", 
                            "completed_at": time.time(), 
                            "result": status_response
                        })
                        self.logger.info(f"Coin {ticker} activation completed")
                        return
                        
            except Exception as e:
                self.logger.info(f"Polling error for {ticker}: {e}")
                # Continue polling on transient errors
                
            poll_count += 1
            time.sleep(5)
        
        # Timeout
        ACTIVATION_STATE[key].update({
            "status": "timeout", 
            "failed_at": time.time(),
            "error": f"Task polling timed out after {max_polls * 5} seconds"
        })
        self.logger.error(f"Coin {ticker} activation timed out")

    def is_coin_enabled(self, ticker: str) -> bool:
        """Check if a coin is currently enabled."""
        ticker_upper = str(ticker).upper()
        state = ACTIVATION_STATE.get(self._state_key(ticker_upper), {})
        return state.get("status") == "enabled"

    def activate_coin(self, ticker: str, enable_hd: bool = True, 
                     wait_for_completion: bool = True) -> ActivationResult:
        """Activate a coin using appropriate protocol method.
        
        Args:
            ticker: The coin ticker to activate
            enable_hd: Whether to use HD wallet mode  
            wait_for_completion: Whether to wait for task completion
            
        Returns:
            ActivationResult with success status and response
        """
        # Preserve original ticker case for config lookups
        # Use uppercase only for state keys and enabled coin checks
        ticker_upper = str(ticker).upper()
        key = self._state_key(ticker_upper)
        
        # Check if already enabled
        if self.is_coin_enabled(ticker_upper):
            self.logger.info(f"Coin {ticker} is already enabled")
            return ActivationResult(
                success=True,
                response=ACTIVATION_STATE.get(key, {}).get("result", {}),
                error=None
            )
        
        try:
            # Check if already activated via get_enabled_coins first
            enabled_coins_response = self.rpc_func("get_enabled_coins", {})
            if isinstance(enabled_coins_response, dict) and "result" in enabled_coins_response:
                enabled_coins = enabled_coins_response["result"]
                if isinstance(enabled_coins, list):
                    enabled_tickers = [coin.get("ticker", "").upper() for coin in enabled_coins if isinstance(coin, dict)]
                    if ticker_upper in enabled_tickers:
                        self.logger.info(f"Coin {ticker_upper} is already enabled")
                        ACTIVATION_STATE[key] = {
                            "status": "enabled",
                            "last_started": time.time(),
                            "result": {"status": "already_enabled"}
                        }
                        return ActivationResult(
                            success=True,
                            response={"status": "already_enabled"},
                            already_enabled=True
                        )
            
            # Build activation request (preserve original ticker case)
            activation_request = self.request_builder.build_activation_request(ticker, enable_hd)
            
            # Update state
            ACTIVATION_STATE[key] = {
                "status": "in_progress", 
                "last_started": time.time(),
                "method": activation_request.method
            }
            
            # Make the activation request
            request_params = {
                "userpass": self.userpass,
                "mmrpc": "2.0",
                "method": activation_request.method,
                "params": activation_request.params,
                "id": 0
            }
            
            response = self.rpc_func(activation_request.method, activation_request.params) or {}
            
            # Check if it's the "already activated" error and handle gracefully
            if (isinstance(response, dict) and "error" in response and 
                "raw_response" in response):
                raw_response = response.get("raw_response", "")
                if "CoinIsAlreadyActivated" in raw_response or "is activated already" in raw_response:
                    self.logger.info(f"Coin {ticker} is already activated")
                    ACTIVATION_STATE[key] = {
                        "status": "enabled",
                        "last_started": time.time(),
                        "result": {"status": "already_enabled"}
                    }
                    return ActivationResult(
                        success=True,
                        response={"status": "already_enabled"},
                        already_enabled=True
                    )
            
            
            # Handle task-based methods
            if activation_request.is_task:
                task_id = None
                # Extract response dict from tuple if needed
                response_dict = response
                if isinstance(response, tuple) and len(response) >= 2:
                    response_dict = response[1]
                
                if isinstance(response_dict, dict):
                    result = response_dict.get("result")
                    if isinstance(result, dict):
                        task_id = result.get("task_id")
                
                if task_id is not None:
                    status_method = self._status_method_for_init(activation_request.method)
                    if status_method:
                        ACTIVATION_STATE[key].update({
                            "task_id": task_id, 
                            "status_method": status_method
                        })
                        
                        # Start polling in background
                        poll_thread = threading.Thread(
                            target=self._poll_task, 
                            args=(ticker_upper, status_method, task_id), 
                            daemon=True
                        )
                        poll_thread.start()
                        
                        # Wait for completion if requested
                        if wait_for_completion:
                            poll_thread.join(timeout=300)  # 5 minute timeout
                            
                            final_state = ACTIVATION_STATE.get(key, {})
                            final_status = final_state.get("status")
                            
                            if final_status == "enabled":
                                self.logger.info(f"Successfully activated {ticker}")
                                return ActivationResult(
                                    success=True,
                                    response=final_state.get("result", {}),
                                    task_id=task_id
                                )
                            else:
                                error_msg = final_state.get("error", f"Activation failed with status: {final_status}")
                                self.logger.warning(f"Failed to activate {ticker}: {error_msg}")
                                return ActivationResult(
                                    success=False,
                                    response=final_state.get("result", {}),
                                    task_id=task_id,
                                    error=error_msg
                                )
                        else:
                            return ActivationResult(
                                success=True,
                                response=response,
                                task_id=task_id
                            )
                    else:
                        self.logger.error(f"No status method available for {activation_request.method}")
                        ACTIVATION_STATE[key].update({
                            "status": "failed", 
                            "error": "No status method available"
                        })
                        return ActivationResult(
                            success=False,
                            response=response,
                            error="No status method available for task"
                        )
                else:
                    # Provide more context for debugging: include the raw init response
                    try:
                        self.logger.warning(
                            f"No task ID returned from {ticker} activation request. "
                            f"Init response: {json.dumps(response) if isinstance(response, (dict, list)) else str(response)}"
                        )
                    except Exception:
                        self.logger.warning(f"No task ID returned from {ticker} activation request. Init response: <unserializable>")
                    ACTIVATION_STATE[key].update({
                        "status": "failed", 
                        "error": "No task ID returned"
                    })
                    return ActivationResult(
                        success=False,
                        response=response,
                        error="No task ID returned from activation request"
                    )
            else:
                # Non-task method - immediate response
                if isinstance(response, dict) and response.get("result"):
                    ACTIVATION_STATE[key].update({
                        "status": "enabled", 
                        "result": response, 
                        "completed_at": time.time()
                    })
                    return ActivationResult(success=True, response=response)
                else:
                    ACTIVATION_STATE[key].update({
                        "status": "failed", 
                        "result": response
                    })
                    return ActivationResult(
                        success=False, 
                        response=response,
                        error="Activation request failed"
                    )
                    
        except Exception as e:
            error_msg = f"Failed to activate {ticker}: {str(e)}"
            self.logger.error(error_msg)
            ACTIVATION_STATE[key] = {
                "status": "failed", 
                "error": error_msg,
                "failed_at": time.time()
            }
            return ActivationResult(success=False, response={}, error=error_msg)

    def activate_token(self, ticker: str, parent_override: Optional[str] = None,
                      enable_hd: bool = True) -> ActivationResult:
        """Activate a token, ensuring its parent coin is enabled first.
        
        Args:
            ticker: The token ticker to activate
            parent_override: Override for parent coin detection
            enable_hd: Whether to use HD wallet mode for parent coin
            
        Returns:
            ActivationResult with success status and response
        """
        # Preserve original ticker case for config lookups
        # Use uppercase only for state keys
        ticker_upper = str(ticker).upper()
        key = self._state_key(ticker_upper)
        
        # Check if already enabled
        if self.is_coin_enabled(ticker_upper):
            self.logger.info(f"Token {ticker} is already enabled")
            return ActivationResult(
                success=True,
                response=ACTIVATION_STATE.get(key, {}).get("result", {}),
                error=None
            )
        
        try:
            # Build token activation request and get parent coin (preserve original ticker case)
            token_request, parent_coin = self.request_builder.build_token_activation_request(ticker)
            parent_coin = parent_override or parent_coin
            
            # Ensure parent coin is enabled first
            if parent_coin:
                parent_result = self.activate_coin(parent_coin, enable_hd, wait_for_completion=True)
                if not parent_result.success:
                    return ActivationResult(
                        success=False,
                        response=parent_result.response,
                        error=f"Failed to enable parent coin {parent_coin}: {parent_result.error}"
                    )
                self.logger.info(f"Parent coin {parent_coin} is enabled, proceeding with token {ticker}")
            
            # Activate the token
            ACTIVATION_STATE[key] = {
                "status": "in_progress", 
                "last_started": time.time(),
                "parent": parent_coin,
                "method": token_request.method
            }
            
            response = self.rpc_func(token_request.method, token_request.params) or {}
            
            if isinstance(response, dict) and response.get("result"):
                ACTIVATION_STATE[key].update({
                    "status": "enabled", 
                    "result": response, 
                    "completed_at": time.time()
                })
                self.logger.info(f"Token {ticker} activated successfully")
                return ActivationResult(success=True, response=response)
            else:
                ACTIVATION_STATE[key].update({
                    "status": "failed", 
                    "result": response
                })
                return ActivationResult(
                    success=False, 
                    response=response,
                    error="Token activation request failed"
                )
                
        except Exception as e:
            error_msg = f"Failed to activate token {ticker}: {str(e)}"
            self.logger.error(error_msg)
            ACTIVATION_STATE[key] = {
                "status": "failed", 
                "error": error_msg,
                "failed_at": time.time()
            }
            return ActivationResult(success=False, response={}, error=error_msg)

    def get_activation_status(self, ticker: str) -> Dict[str, Any]:
        """Get current activation status for a ticker."""
        ticker_upper = str(ticker).upper()
        return ACTIVATION_STATE.get(self._state_key(ticker_upper), {"status": "not_started"})

