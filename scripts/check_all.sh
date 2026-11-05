#!/usr/bin/env bash
# scripts/check_all.sh — все проверки перед PR (раздел 8, P-15)
cd "$(dirname "$0")/.." || exit 1
fail=0

run() {
  echo "== $*"
  "$@" || { echo "ПРОВАЛ: $*"; fail=1; }
}

check_openapi() {
  tmp=$(mktemp)
  python manage.py spectacular --file "$tmp" || return 1
  diff -u openapi.yaml "$tmp"
}

run python manage.py check
run python -m pytest -q
run python manage.py makemigrations --check --dry-run
run bash scripts/check_layers.sh
run check_openapi
run bash scripts/check_history.sh "${BASE_RANGE:-origin/main..HEAD}"

if [ "$fail" -ne 0 ]; then
  echo "check_all: КРАСНЫЙ"
  exit 1
fi
echo "check_all: ЗЕЛЁНЫЙ"
