#!/usr/bin/env python3
import os
import json
import time
import argparse
from typing import Any, Dict, Optional, Tuple, List

from const import COINS_CONFIG_FILE, SCRIPT_PATH


class CoinsConfigLoader:
    """Loads and caches coins_config.json from the local config directory."""

    _cache: Dict[str, Any] = {"ts": 0, "data": None}

    @classmethod
    def load(cls) -> Dict[str, Any]:
        try:
            if cls._cache.get("data"):
                return cls._cache["data"]
            if os.path.exists(COINS_CONFIG_FILE):
                with open(COINS_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    norm = {}
                    for entry in data:
                        if isinstance(entry, dict):
                            t = (
                                entry.get("ticker")
                                or entry.get("symbol")
                                or entry.get("coin")
                            )
                            if t:
                                norm[str(t).upper()] = entry
                    data = norm
                cls._cache.update({"ts": time.time(), "data": data or {}})
                return data or {}
        except Exception:
            pass
        return {}


def _find_coin_entry(cfg: Dict[str, Any], ticker: str) -> Optional[Dict[str, Any]]:
    t = str(ticker or "").upper()
    if t in cfg and isinstance(cfg[t], dict):
        return cfg[t]
    for _, val in (cfg.items() if isinstance(cfg, dict) else []):
        if not isinstance(val, dict):
            continue
        if val.get("ticker") == t or val.get("symbol") == t or val.get("coin") == t:
            return val
    return None


def get_all_coins_from_config() -> List[str]:
    cfg = CoinsConfigLoader.load()
    if isinstance(cfg, dict):
        return sorted(set([str(k).upper() for k in cfg.keys()]))
    return []


def get_coin_protocol(ticker: str) -> Tuple[Optional[str], Dict[str, Any]]:
    cfg = CoinsConfigLoader.load()
    entry = _find_coin_entry(cfg, ticker) or {}
    prot = entry.get("protocol") or {}
    ptype = prot.get("type") if isinstance(prot, dict) else None
    pdata = (
        prot.get("protocol_data")
        if isinstance(prot, dict)
        else None
    ) or {}

    if isinstance(entry.get("nodes"), list):
        pdata.setdefault("nodes", entry.get("nodes"))
    if isinstance(entry.get("electrum"), list):
        pdata.setdefault("electrum", entry.get("electrum"))
    if isinstance(entry.get("rpc_urls"), list):
        pdata.setdefault("rpc_urls", entry.get("rpc_urls"))
    if entry.get("swap_contract_address"):
        pdata.setdefault("swap_contract_address", entry.get("swap_contract_address"))
    if entry.get("fallback_swap_contract"):
        pdata.setdefault("fallback_swap_contract", entry.get("fallback_swap_contract"))
    if entry.get("chain_id") or entry.get("chainId") or entry.get("chain_registry_name"):
        pdata.setdefault(
            "chain_id", entry.get("chain_id") or entry.get("chainId") or entry.get("chain_registry_name")
        )
    if entry.get("denom"):
        pdata.setdefault("denom", entry.get("denom"))

    # Fallback: if electrum servers missing for UTXO, try legacy coins file
    if (ptype or "UTXO").upper() == "UTXO":
        if not pdata.get("electrum"):
            try:
                coins_path = os.path.join(SCRIPT_PATH, "coins")
                if os.path.exists(coins_path):
                    with open(coins_path, "r", encoding="utf-8") as f:
                        legacy = json.load(f)
                    if isinstance(legacy, list):
                        for row in legacy:
                            if not isinstance(row, dict):
                                continue
                            coin_sym = (row.get("ticker") or row.get("coin") or row.get("symbol") or "").upper()
                            if coin_sym == str(ticker).upper() and isinstance(row.get("electrum"), list):
                                pdata.setdefault("electrum", row.get("electrum"))
                                break
            except Exception:
                pass

    return ptype, pdata


def _normalize_eth_nodes(nodes: Optional[List[Any]]) -> List[Dict[str, str]]:
    norm: List[Dict[str, str]] = []
    for n in nodes or []:
        if isinstance(n, dict) and n.get("url"):
            norm.append({"url": n["url"]})
        elif isinstance(n, str):
            norm.append({"url": n})
    return norm


def _normalize_tendermint_nodes(pdata: Dict[str, Any]) -> List[Dict[str, str]]:
    nodes: List[Dict[str, str]] = []
    if isinstance(pdata.get("rpc_urls"), list):
        for e in pdata.get("rpc_urls"):
            if isinstance(e, dict):
                node: Dict[str, str] = {}
                if e.get("url"):
                    node["url"] = e.get("url")
                if e.get("api_url"):
                    node["api_url"] = e.get("api_url")
                if e.get("grpc_url"):
                    node["grpc_url"] = e.get("grpc_url")
                if e.get("ws_url"):
                    node["ws_url"] = e.get("ws_url")
                if node.get("url"):
                    nodes.append(node)
            elif isinstance(e, str):
                nodes.append({"url": e})
    if not nodes and isinstance(pdata.get("nodes"), list):
        for n in pdata.get("nodes"):
            if isinstance(n, dict) and n.get("url"):
                nodes.append({"url": n.get("url")})
    return nodes


def build_activate_command(coin: str) -> Dict[str, Any]:
    t = str(coin).upper()
    ptype, pdata = get_coin_protocol(t)
    ptype_l = (ptype or "UTXO").lower()

    if "eth" in ptype_l:
        method = "task::enable_eth::init"
        params: Dict[str, Any] = {
            "ticker": t,
            "tx_history": True,
            "get_balances": True,
            "erc20_tokens_requests": [],
        }
        nodes = _normalize_eth_nodes(pdata.get("nodes") or pdata.get("rpc"))
        if nodes:
            params["nodes"] = nodes
        sc = pdata.get("swap_contract_address") or pdata.get("swap_contract") or pdata.get("swap") or pdata.get("swap_contracts")
        if isinstance(sc, list) and sc:
            params["swap_contract_address"] = sc[0]
            if len(sc) > 1:
                params["fallback_swap_contract"] = sc[1]
        elif isinstance(sc, str):
            params["swap_contract_address"] = sc
        if pdata.get("fallback_swap_contract") and not params.get("fallback_swap_contract"):
            params["fallback_swap_contract"] = pdata.get("fallback_swap_contract")
    elif "tendermint" in ptype_l or "cosmos" in ptype_l:
        method = "task::enable_tendermint::init"
        params = {
            "ticker": t,
            "tx_history": True,
            "get_balances": True,
        }
        nodes = _normalize_tendermint_nodes(pdata)
        if nodes:
            params["nodes"] = nodes
        if pdata.get("chain_id"):
            params["chain_id"] = pdata.get("chain_id")
        if pdata.get("denom"):
            params["denom"] = pdata.get("denom")
    else:
        method = "task::enable_utxo::init"
        # Select electrum servers: drop WSS, prefer SSL over TCP, cap at 3
        def _filter_limit_electrum(servers: Optional[List[Any]]) -> List[Dict[str, Any]]:
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
            ordered = ssl_list + tcp_list + other_list
            return ordered[:3]

        electrum_servers = _filter_limit_electrum(pdata.get("electrum"))

        params = {
            "ticker": t,
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

    return {"mmrpc": "2.0", "method": method, "params": params, "id": 0}


def _cli():
    parser = argparse.ArgumentParser(
        description="Build KDF activation RPC payload from local coins_config.json"
    )
    parser.add_argument(
        "ticker",
        help="Ticker symbol to build activation payload for (e.g. KMD, ETH, ATOM)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Output compact JSON (no indentation)",
    )
    args = parser.parse_args()

    payload = build_activate_command(args.ticker)
    print(json.dumps(payload, indent=None if args.compact else 2))


if __name__ == "__main__":
    _cli()


