from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, Request
from pydantic import BaseModel, Extra

from src.public_market_readonly import run_public_market_readonly_with_timeout, REDACTED_PROVIDER_LABEL
from src.fund_data_akshare_provider import run_akshare_fund_readonly_with_timeout
from src.fund_comparison import run_akshare_fund_comparison_with_timeout

router = APIRouter()

class PublicMarketReadonlyRequestModel(BaseModel, extra=Extra.forbid):
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


class FundPublicReadonlyRequestModel(BaseModel, extra=Extra.forbid):
    mode: str
    provider: str
    code: str
    sections: List[str]
    humanApproved: bool
    readOnly: bool
    allowAccountRead: bool
    allowTrading: bool
    allowNotificationSend: bool
    allowAiCall: bool
    allowPersistence: bool


class FundComparisonReadonlyRequestModel(BaseModel, extra=Extra.forbid):
    mode: str
    provider: str
    codes: List[str]
    sections: List[str]
    humanApproved: bool
    readOnly: bool
    allowAccountRead: bool
    allowTrading: bool
    allowNotificationSend: bool
    allowAiCall: bool
    allowPersistence: bool


def _is_local(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return host in {"127.0.0.1", "::1", "testclient"}

@router.post("/akshare/dry-run")
async def akshare_public_market_dry_run(payload: PublicMarketReadonlyRequestModel, request: Request) -> Dict[str, Any]:
    if not _is_local(request):
        return {"status":"blocked","errorCode":"real-readonly.localhost-only","providerLabel":REDACTED_PROVIDER_LABEL,"readOnly":True,"redacted":True}
    return await run_public_market_readonly_with_timeout(payload.dict())


@router.post("/akshare/fund")
async def akshare_fund_public_readonly(payload: FundPublicReadonlyRequestModel, request: Request) -> Dict[str, Any]:
    if not _is_local(request):
        return {
            "status": "blocked",
            "errorCode": "fund-readonly.localhost-only",
            "providerLabel": "AKShare 公开基金数据",
            "readOnly": True,
        }
    return await run_akshare_fund_readonly_with_timeout(payload.dict())


@router.post("/akshare/funds/compare")
async def akshare_fund_comparison_readonly(
    payload: FundComparisonReadonlyRequestModel,
    request: Request,
) -> Dict[str, Any]:
    if not _is_local(request):
        return {
            "status": "blocked",
            "errorCode": "fund-comparison.localhost-only",
            "providerLabel": "AKShare 公开基金数据",
            "readOnly": True,
        }
    return await run_akshare_fund_comparison_with_timeout(payload.dict())
