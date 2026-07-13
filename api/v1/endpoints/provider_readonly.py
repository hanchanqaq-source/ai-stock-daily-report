from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Request
from pydantic import BaseModel, Extra

from src.public_market_readonly import run_public_market_readonly, REDACTED_PROVIDER_LABEL

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


def _is_local(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return host in {"127.0.0.1", "::1", "testclient"}

@router.post("/akshare/dry-run")
async def akshare_public_market_dry_run(payload: PublicMarketReadonlyRequestModel, request: Request) -> Dict[str, Any]:
    if not _is_local(request):
        return {"status":"blocked","errorCode":"real-readonly.localhost-only","providerLabel":REDACTED_PROVIDER_LABEL,"readOnly":True,"redacted":True}
    return run_public_market_readonly(payload.dict())
