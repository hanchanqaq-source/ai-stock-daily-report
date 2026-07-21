"""Validate an explicit, owner-authorized GitHub release request."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
ISSUE_TITLE_PATTERN = re.compile(r"^\[release\] (v\d+\.\d+\.\d+)$")
ISSUE_MARKER = "<!-- authorized-release-request -->"


def parse_version(tag: str) -> tuple[int, int, int]:
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        raise ValueError(f"release tag must use vMAJOR.MINOR.PATCH: {tag!r}")
    return tuple(int(part) for part in match.groups())


def resolve_release_tag(env: dict[str, str]) -> str:
    event_name = env.get("GITHUB_EVENT_NAME", "")
    default_branch = env.get("GITHUB_DEFAULT_BRANCH", "")
    ref_name = env.get("GITHUB_REF_NAME", "")

    if not default_branch or ref_name != default_branch:
        raise ValueError("authorized releases must run from the repository default branch")

    if event_name == "workflow_dispatch":
        tag = env.get("INPUT_RELEASE_TAG", "").strip()
        parse_version(tag)
        if env.get("INPUT_CONFIRMATION", "") != f"PUBLISH {tag}":
            raise ValueError(f"confirmation must exactly equal: PUBLISH {tag}")
        return tag

    if event_name == "issues":
        if env.get("ISSUE_AUTHOR_ASSOCIATION", "") != "OWNER":
            raise ValueError("release request issue must be created by the repository owner")
        title_match = ISSUE_TITLE_PATTERN.fullmatch(env.get("ISSUE_TITLE", "").strip())
        if not title_match:
            raise ValueError("release request title must exactly match: [release] vMAJOR.MINOR.PATCH")
        if ISSUE_MARKER not in env.get("ISSUE_BODY", ""):
            raise ValueError("release request issue is missing the authorization marker")
        tag = title_match.group(1)
        parse_version(tag)
        return tag

    raise ValueError(f"unsupported release event: {event_name!r}")


def ensure_version_is_new(tag: str, existing_tags: list[str]) -> None:
    requested = parse_version(tag)
    versions = [parse_version(item) for item in existing_tags if TAG_PATTERN.fullmatch(item)]
    if requested in versions:
        raise ValueError(f"release tag already exists: {tag}")
    if versions and requested <= max(versions):
        latest = "v" + ".".join(str(part) for part in max(versions))
        raise ValueError(f"release tag {tag} must be newer than the latest tag {latest}")


def git_output(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).strip()


def write_output(name: str, value: str, output_path: str) -> None:
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write(f"{name}={value}\n")


def main() -> None:
    tag = resolve_release_tag(dict(os.environ))
    existing_tags = [line for line in git_output("tag", "--list").splitlines() if line]
    ensure_version_is_new(tag, existing_tags)
    commit = git_output("rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("could not resolve the exact release commit")

    output_path = os.environ.get("GITHUB_OUTPUT", "")
    if not output_path:
        raise ValueError("GITHUB_OUTPUT is required")
    write_output("release_tag", tag, output_path)
    write_output("release_commit", commit, output_path)
    print(f"Authorized release candidate: {tag} at {commit}")


if __name__ == "__main__":
    main()
