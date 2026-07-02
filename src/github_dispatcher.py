# -*- coding: utf-8 -*-
"""Lightweight GitHub repository_dispatch client for channel commands."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

DEFAULT_DISPATCH_REPO = "hanchanqaq-source/ai-stock-daily-report"
DEFAULT_DISPATCH_EVENT_TYPE = "run-stock-report"
GITHUB_DISPATCH_API = "https://api.github.com/repos/{repo}/dispatches"


@dataclass(frozen=True)
class GitHubDispatchResult:
    status: str
    message: str
    payload: Dict[str, Any]
    repo: str
    event_type: str
    http_status: Optional[int] = None
    error: Optional[str] = None


def mask_token(token: Optional[str]) -> str:
    """Return a log-safe token preview without exposing the full secret."""
    value = str(token or "")
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


def get_dispatch_config() -> Dict[str, str]:
    """Load dispatch configuration from environment with safe defaults."""
    return {
        "token": (os.getenv("GITHUB_DISPATCH_TOKEN") or "").strip(),
        "repo": (os.getenv("GITHUB_DISPATCH_REPO") or DEFAULT_DISPATCH_REPO).strip(),
        "event_type": (os.getenv("GITHUB_DISPATCH_EVENT_TYPE") or DEFAULT_DISPATCH_EVENT_TYPE).strip(),
    }


def build_repository_dispatch_payload(
    *,
    run_mode: str,
    model_profile: str,
    request_id: str,
    command_text: str,
    event_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the GitHub repository_dispatch payload for rerun requests."""
    safe_event_type = (event_type or get_dispatch_config()["event_type"] or DEFAULT_DISPATCH_EVENT_TYPE).strip()
    return {
        "event_type": safe_event_type,
        "client_payload": {
            "run_mode": run_mode,
            "model_profile": model_profile,
            "trigger_source": "channel_command",
            "request_id": request_id,
            "command_text": str(command_text or ""),
        },
    }


def send_repository_dispatch(payload: Dict[str, Any], *, timeout: int = 15) -> GitHubDispatchResult:
    """Send a GitHub repository_dispatch request and convert failures to results."""
    config = get_dispatch_config()
    token = config["token"]
    repo = config["repo"] or DEFAULT_DISPATCH_REPO
    event_type = str(payload.get("event_type") or config["event_type"] or DEFAULT_DISPATCH_EVENT_TYPE)

    if not token:
        return GitHubDispatchResult(
            status="missing_token",
            message="缺少 GITHUB_DISPATCH_TOKEN，无法提交 GitHub Actions 重跑",
            payload=payload,
            repo=repo,
            event_type=event_type,
        )

    url = GITHUB_DISPATCH_API.format(repo=repo)
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "ai-stock-daily-report-command-executor",
        },
    )
    logger.info("Submitting repository_dispatch repo=%s event_type=%s token=%s", repo, event_type, mask_token(token))
    try:
        with urlopen(request, timeout=timeout) as response:  # nosec B310 - fixed GitHub API URL
            http_status = getattr(response, "status", None)
        return GitHubDispatchResult(
            status="submitted",
            message="已提交到 GitHub Actions",
            payload=payload,
            repo=repo,
            event_type=event_type,
            http_status=http_status,
        )
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        logger.warning("repository_dispatch failed status=%s repo=%s event_type=%s error=%s", exc.code, repo, event_type, detail)
        return GitHubDispatchResult(
            status="request_failed",
            message=f"GitHub repository_dispatch 请求失败：HTTP {exc.code}",
            payload=payload,
            repo=repo,
            event_type=event_type,
            http_status=exc.code,
            error=detail,
        )
    except (URLError, OSError) as exc:
        logger.warning("repository_dispatch failed repo=%s event_type=%s error=%s", repo, event_type, exc)
        return GitHubDispatchResult(
            status="request_failed",
            message=f"GitHub repository_dispatch 请求失败：{exc}",
            payload=payload,
            repo=repo,
            event_type=event_type,
            error=str(exc),
        )
