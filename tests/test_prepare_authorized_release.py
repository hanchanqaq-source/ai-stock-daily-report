from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / ".github" / "scripts" / "prepare_authorized_release.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("prepare_authorized_release", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_workflow_dispatch_requires_exact_confirmation() -> None:
    module = _load_module()
    env = {
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_DEFAULT_BRANCH": "main",
        "GITHUB_REF_NAME": "main",
        "INPUT_RELEASE_TAG": "v3.21.1",
        "INPUT_CONFIRMATION": "PUBLISH v3.21.1",
    }

    assert module.resolve_release_tag(env) == "v3.21.1"

    env["INPUT_CONFIRMATION"] = "v3.21.1"
    with pytest.raises(ValueError, match="confirmation must exactly equal"):
        module.resolve_release_tag(env)


def test_owner_issue_request_requires_marker_and_exact_title() -> None:
    module = _load_module()
    env = {
        "GITHUB_EVENT_NAME": "issues",
        "GITHUB_DEFAULT_BRANCH": "main",
        "GITHUB_REF_NAME": "main",
        "ISSUE_AUTHOR_ASSOCIATION": "OWNER",
        "ISSUE_TITLE": "[release] v3.21.1",
        "ISSUE_BODY": "<!-- authorized-release-request -->\nExplicit approval recorded.",
    }

    assert module.resolve_release_tag(env) == "v3.21.1"

    env["ISSUE_AUTHOR_ASSOCIATION"] = "COLLABORATOR"
    with pytest.raises(ValueError, match="repository owner"):
        module.resolve_release_tag(env)


def test_release_must_use_default_branch() -> None:
    module = _load_module()
    env = {
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_DEFAULT_BRANCH": "main",
        "GITHUB_REF_NAME": "feature",
        "INPUT_RELEASE_TAG": "v3.21.1",
        "INPUT_CONFIRMATION": "PUBLISH v3.21.1",
    }

    with pytest.raises(ValueError, match="default branch"):
        module.resolve_release_tag(env)


def test_release_version_must_be_new_and_monotonic() -> None:
    module = _load_module()

    module.ensure_version_is_new("v3.21.1", ["v3.20.9", "v3.21.0", "not-semver"])

    with pytest.raises(ValueError, match="already exists"):
        module.ensure_version_is_new("v3.21.0", ["v3.21.0"])
    with pytest.raises(ValueError, match="must be newer"):
        module.ensure_version_is_new("v3.20.9", ["v3.21.0"])
