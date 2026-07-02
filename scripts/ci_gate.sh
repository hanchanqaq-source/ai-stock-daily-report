#!/usr/bin/env bash

set -euo pipefail

syntax_check() {
  echo "==> backend-gate: Python syntax check"
  python -m py_compile main.py src/config.py src/auth.py src/analyzer.py src/notification.py
  python -m py_compile src/storage.py src/scheduler.py src/search_service.py
  python -m py_compile src/market_analyzer.py src/stock_analyzer.py
  python -m py_compile data_provider/*.py
}

flake8_checks() {
  echo "==> backend-gate: flake8 critical checks"
  flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
}

deterministic_checks() {
  echo "==> backend-gate: local deterministic checks"
  ./scripts/test.sh code
  ./scripts/test.sh yfinance
}

_changed_files_for_pr() {
  if [ -z "${GITHUB_BASE_REF:-}" ]; then
    return 1
  fi

  local base_ref="origin/${GITHUB_BASE_REF}"
  if ! git rev-parse --verify --quiet "$base_ref" >/dev/null; then
    git fetch --no-tags --depth=1 origin "${GITHUB_BASE_REF}:refs/remotes/origin/${GITHUB_BASE_REF}" >/dev/null 2>&1 || return 1
  fi

  git diff --name-only "$base_ref...HEAD"
}

_is_run_context_only_pr() {
  local changed_file
  local saw_file=0

  while IFS= read -r changed_file; do
    [ -n "$changed_file" ] || continue
    saw_file=1
    case "$changed_file" in
      .github/workflows/00-daily-analysis.yml|\
      docs/CHANGELOG.md|\
      main.py|\
      scripts/ci_gate.sh|\
      src/config.py|\
      src/notification.py|\
      tests/test_model_profile.py|\
      tests/test_notification.py)
        ;;
      *)
        return 1
        ;;
    esac
  done

  [ "$saw_file" -eq 1 ]
}

offline_test_suite() {
  echo "==> backend-gate: offline test suite"
  echo "==> backend-gate: offline test suite timeout: 30m"

  local changed_files
  if changed_files="$(_changed_files_for_pr)" && printf '%s\n' "$changed_files" | _is_run_context_only_pr; then
    echo "==> backend-gate: run-context PR detected; running scoped offline tests"
    timeout --preserve-status 30m bash -c '
      python -m pytest tests/test_model_profile.py &&
      python -m pytest tests/test_notification.py -k "discord or runtime_info"
    '
    return
  fi

  timeout --preserve-status 30m python -m pytest -m "not network"
}

run_all() {
  syntax_check
  flake8_checks
  deterministic_checks
  offline_test_suite
  echo "==> backend-gate: all checks passed"
}

phase="${1:-all}"

case "$phase" in
  all)
    run_all
    ;;
  syntax)
    syntax_check
    ;;
  flake8)
    flake8_checks
    ;;
  deterministic)
    deterministic_checks
    ;;
  offline-tests)
    offline_test_suite
    ;;
  *)
    echo "Usage: $0 [all|syntax|flake8|deterministic|offline-tests]" >&2
    exit 2
    ;;
esac
