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

_is_market_review_summary_pr() {
  local changed_file
  local saw_file=0

  while IFS= read -r changed_file; do
    [ -n "$changed_file" ] || continue
    saw_file=1
    case "$changed_file" in
      docs/CHANGELOG.md|\
      scripts/ci_gate.sh|\
      src/market_analyzer.py|\
      src/market_history.py|\
      src/notification.py|\
      src/report_language.py|\
      src/report_renderer.py|\
      src/schemas/market_light.py|\
      tests/test_market_history.py|\
      tests/test_market_review.py|\
      tests/test_notification.py)
        ;;
      *)
        return 1
        ;;
    esac
  done

  [ "$saw_file" -eq 1 ]
}


_is_account_realtime_summary_pr() {
  local changed_file
  local saw_file=0

  while IFS= read -r changed_file; do
    [ -n "$changed_file" ] || continue
    saw_file=1
    case "$changed_file" in
      .github/workflows/ci.yml|\
      docs/CHANGELOG.md|\
      docs/account_page_model.md|\
      docs/account_realtime_summary.md|\
      docs/fund_nav_provider.md|\
      docs/holding_watch_compare.md|\
      docs/product_rules.md|\
      docs/realtime_quote_provider.md|\
      scripts/ci_gate.sh|\
      src/account_realtime_summary.py|\
      tests/test_account_realtime_summary.py)
        ;;
      *)
        return 1
        ;;
    esac
  done

  [ "$saw_file" -eq 1 ]
}

_run_account_realtime_summary_tests() {
  python -m pytest tests/test_account_realtime_summary.py -q
  python -m pytest tests/test_realtime_quote_provider.py -q
  python -m pytest tests/test_fund_nav_provider.py -q
  python -m pytest tests/test_quote_capability.py -q
  python -m pytest tests/test_account_page_model.py -q
  python -m pytest tests/test_holding_watch_compare.py -q
}

_run_market_review_summary_tests() {
  if [ -f tests/test_market_history.py ]; then
    python -m pytest tests/test_market_history.py -q
  else
    echo "==> backend-gate: tests/test_market_history.py not present; skipping market history file test"
  fi
  python -m pytest tests/test_market_review.py -k "recent_market_comparison" -q
  python -m pytest tests/test_notification.py -k "discord or summary or recent_change" -q
}

offline_test_suite() {
  echo "==> backend-gate: offline test suite"
  echo "==> backend-gate: offline test suite timeout: 60m"

  local changed_files
  if changed_files="$(_changed_files_for_pr)" && printf '%s\n' "$changed_files" | _is_run_context_only_pr; then
    echo "==> backend-gate: run-context PR detected; running scoped offline tests"
    timeout --preserve-status 60m bash -c '
      python -m pytest tests/test_model_profile.py &&
      python -m pytest tests/test_notification.py -k "discord or runtime_info"
    '
    return
  fi

  if changed_files="$(_changed_files_for_pr)" && printf '%s\n' "$changed_files" | _is_market_review_summary_pr; then
    echo "==> backend-gate: market-review summary PR detected; running scoped offline tests"
    timeout --preserve-status 60m bash -c '
      ./scripts/ci_gate.sh __market-review-summary-tests
    '
    return
  fi

  if changed_files="$(_changed_files_for_pr)" && printf '%s\n' "$changed_files" | _is_account_realtime_summary_pr; then
    echo "==> backend-gate: account realtime summary PR detected; running scoped offline tests"
    timeout --preserve-status 60m bash -c '
      ./scripts/ci_gate.sh __account-realtime-summary-tests
    '
    return
  fi

  timeout --preserve-status 60m python -m pytest -m "not network"
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
  __market-review-summary-tests)
    _run_market_review_summary_tests
    ;;
  __account-realtime-summary-tests)
    _run_account_realtime_summary_tests
    ;;
  *)
    echo "Usage: $0 [all|syntax|flake8|deterministic|offline-tests]" >&2
    exit 2
    ;;
esac
