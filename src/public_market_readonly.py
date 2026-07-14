"""Core-M3 public A-share readonly dry-run service."""
from __future__ import annotations

import asyncio
import math, os, re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

import pandas as pd

from data_provider.base import DataFetcherManager
from data_provider.base import DataFetchError

REDACTED_PROVIDER_LABEL = "REDACTED_PROVIDER_LABEL"
SYMBOL_RE = re.compile(r"^\d{6}$")
SNAPSHOT_FIELDS = {
    "schemaVersion","sourceType","providerLabel","market","instrumentType","symbol","instrumentName","tradeDate",
    "open","high","low","close","previousClose","changePercent","volume","amount","delayed","readOnly","redacted",
}
ERROR_INVALID_PROVIDER_RESULT = "real-readonly.invalid-provider-result"
ERROR_INVALID_SYMBOL = "real-readonly.invalid-symbol"
ERROR_INVALID_DATE = "real-readonly.invalid-date"
ERROR_INVALID_NUMBER = "real-readonly.invalid-number"
ERROR_INVALID_PRICE_RANGE = "real-readonly.invalid-price-range"
ERROR_PROVIDER_UNAVAILABLE = "real-readonly.provider-unavailable"
ERROR_PROVIDER_TIMEOUT = "real-readonly.provider-timeout"
ERROR_PROVIDER_FAILED = "real-readonly.provider-failed"
ERROR_PROVIDER_IDENTITY_MISMATCH = "real-readonly.provider-identity-mismatch"
PUBLIC_MARKET_READONLY_TIMEOUT_SECONDS = 10

@dataclass(frozen=True)
class PublicMarketReadonlyRequest:
    mode: str
    provider: str
    market: str
    instrumentType: str
    symbol: str
    humanApproved: bool
    readOnly: bool
    allowAccountRead: bool
    allowTrading: bool
    allowNotificationSend: bool
    allowAiCall: bool
    allowPersistence: bool

class PublicMarketReadonlyError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def real_readonly_provider_enabled() -> bool:
    return (os.getenv("REAL_READONLY_PROVIDER_ENABLED") or "false").strip().lower() == "true"


def validate_symbol(symbol: Any) -> str:
    if not isinstance(symbol, str) or not SYMBOL_RE.fullmatch(symbol):
        raise PublicMarketReadonlyError(ERROR_INVALID_SYMBOL)
    return symbol


def validate_request(payload: Mapping[str, Any]) -> PublicMarketReadonlyRequest:
    allowed = set(PublicMarketReadonlyRequest.__annotations__)
    if set(payload) != allowed:
        raise PublicMarketReadonlyError(ERROR_INVALID_PROVIDER_RESULT)
    try:
        req = PublicMarketReadonlyRequest(**payload)
    except TypeError as exc:
        raise PublicMarketReadonlyError(ERROR_INVALID_PROVIDER_RESULT) from exc
    validate_symbol(req.symbol)
    if not (req.humanApproved is True and req.mode == "real-readonly-dry-run" and req.provider == "akshare-public-market"):
        raise PublicMarketReadonlyError(ERROR_INVALID_PROVIDER_RESULT)
    if not (req.market == "cn-a" and req.instrumentType == "stock" and req.readOnly is True):
        raise PublicMarketReadonlyError(ERROR_INVALID_PROVIDER_RESULT)
    if any([req.allowAccountRead, req.allowTrading, req.allowNotificationSend, req.allowAiCall, req.allowPersistence]):
        raise PublicMarketReadonlyError(ERROR_INVALID_PROVIDER_RESULT)
    return req


def _finite(value: Any, code: str = ERROR_INVALID_NUMBER) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError) as exc:
        raise PublicMarketReadonlyError(code) from exc
    if not math.isfinite(num):
        raise PublicMarketReadonlyError(code)
    return num


def sanitize_public_market_readonly_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping) or set(snapshot) != SNAPSHOT_FIELDS:
        raise PublicMarketReadonlyError(ERROR_INVALID_PROVIDER_RESULT)
    if snapshot.get("providerLabel") != REDACTED_PROVIDER_LABEL or snapshot.get("sourceType") != "real-readonly":
        raise PublicMarketReadonlyError(ERROR_INVALID_PROVIDER_RESULT)
    if snapshot.get("market") != "cn-a" or snapshot.get("instrumentType") != "stock":
        raise PublicMarketReadonlyError(ERROR_INVALID_PROVIDER_RESULT)
    validate_symbol(snapshot.get("symbol"))
    name = snapshot.get("instrumentName")
    if not isinstance(name, str) or not (1 <= len(name) <= 40) or any(x in name.lower() for x in ["http", "token", "cookie", "authorization"]):
        raise PublicMarketReadonlyError(ERROR_INVALID_PROVIDER_RESULT)
    trade_date = snapshot.get("tradeDate")
    if not isinstance(trade_date, str):
        raise PublicMarketReadonlyError(ERROR_INVALID_DATE)
    try:
        datetime.strptime(trade_date, "%Y-%m-%d")
    except ValueError as exc:
        raise PublicMarketReadonlyError(ERROR_INVALID_DATE) from exc
    clean = dict(snapshot)
    for field in ["open", "high", "low", "close", "volume", "amount"]:
        clean[field] = _finite(clean[field])
    for field in ["previousClose", "changePercent"]:
        clean[field] = None if clean[field] is None else _finite(clean[field])
    if any(clean[f] < 0 for f in ["open", "high", "low", "close", "volume", "amount"]):
        raise PublicMarketReadonlyError(ERROR_INVALID_NUMBER)
    if clean["high"] < clean["low"] or not (clean["low"] <= clean["close"] <= clean["high"]):
        raise PublicMarketReadonlyError(ERROR_INVALID_PRICE_RANGE)
    if clean.get("delayed") is not True or clean.get("readOnly") is not True or clean.get("redacted") is not True:
        raise PublicMarketReadonlyError(ERROR_INVALID_PROVIDER_RESULT)
    return clean


def _latest_row_to_snapshot(symbol: str, df: pd.DataFrame, provider_name: str) -> dict[str, Any]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise PublicMarketReadonlyError(ERROR_PROVIDER_UNAVAILABLE)
    row = df.sort_values("date").iloc[-1]
    prev = None
    if len(df) >= 2:
        prev = float(df.sort_values("date").iloc[-2].get("close"))
    close = float(row.get("close"))
    change = None if not prev or prev == 0 else (close - prev) / prev * 100
    date_value = row.get("date")
    trade_date = pd.to_datetime(date_value).strftime("%Y-%m-%d")
    name = symbol
    try:
        from src.data.stock_mapping import STOCK_NAME_MAP
        name = STOCK_NAME_MAP.get(symbol) or symbol
    except Exception:
        name = symbol
    return sanitize_public_market_readonly_snapshot({
        "schemaVersion":"core-m3.public-market-readonly.v1","sourceType":"real-readonly","providerLabel":REDACTED_PROVIDER_LABEL,
        "market":"cn-a","instrumentType":"stock","symbol":symbol,"instrumentName":name,"tradeDate":trade_date,
        "open":row.get("open"),"high":row.get("high"),"low":row.get("low"),"close":close,"previousClose":prev,
        "changePercent":change,"volume":row.get("volume"),"amount":row.get("amount",0),"delayed":True,"readOnly":True,"redacted":True,
    })


def create_akshare_only_manager() -> DataFetcherManager:
    from data_provider.akshare_fetcher import AkshareFetcher

    return DataFetcherManager(fetchers=[AkshareFetcher(enable_eastmoney_patch=False)])


def fetch_public_market_readonly_snapshot(req: PublicMarketReadonlyRequest, manager: Any | None = None) -> dict[str, Any]:
    manager = manager or create_akshare_only_manager()
    try:
        df, provider_name = manager.get_daily_data(req.symbol, days=8)
    except TimeoutError as exc:
        raise PublicMarketReadonlyError(ERROR_PROVIDER_TIMEOUT) from exc
    except DataFetchError as exc:
        text = str(exc).lower()
        code = ERROR_PROVIDER_TIMEOUT if "timeout" in text or "timed out" in text else ERROR_PROVIDER_UNAVAILABLE
        raise PublicMarketReadonlyError(code) from exc
    except Exception as exc:
        text = str(exc).lower()
        code = ERROR_PROVIDER_TIMEOUT if "timeout" in text or "timed out" in text else ERROR_PROVIDER_FAILED
        raise PublicMarketReadonlyError(code) from exc
    if provider_name != "AkshareFetcher":
        raise PublicMarketReadonlyError(ERROR_PROVIDER_IDENTITY_MISMATCH)
    return _latest_row_to_snapshot(req.symbol, df, provider_name)


def run_public_market_readonly(payload: Mapping[str, Any], manager: Any | None = None) -> dict[str, Any]:
    try:
        req = validate_request(payload)
        if not real_readonly_provider_enabled():
            return {"status":"blocked","errorCode":"real-readonly.disabled","providerLabel":REDACTED_PROVIDER_LABEL,"readOnly":True,"redacted":True}
        snapshot = fetch_public_market_readonly_snapshot(req, manager=manager)
        return {"status":"completed-real-readonly","snapshot":snapshot,"providerLabel":REDACTED_PROVIDER_LABEL,"readOnly":True,"redacted":True}
    except PublicMarketReadonlyError as exc:
        status = "timeout" if exc.code == ERROR_PROVIDER_TIMEOUT else "unavailable" if exc.code == ERROR_PROVIDER_UNAVAILABLE else "invalid-response" if exc.code.startswith("real-readonly.invalid") else "blocked"
        return {"status":status,"errorCode":exc.code,"providerLabel":REDACTED_PROVIDER_LABEL,"readOnly":True,"redacted":True}


async def run_public_market_readonly_with_timeout(
    payload: Mapping[str, Any],
    manager: Any | None = None,
    timeout_seconds: float = PUBLIC_MARKET_READONLY_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(run_public_market_readonly, payload, manager),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "errorCode": ERROR_PROVIDER_TIMEOUT,
            "providerLabel": REDACTED_PROVIDER_LABEL,
            "readOnly": True,
            "redacted": True,
        }
