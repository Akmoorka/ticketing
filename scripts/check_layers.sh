#!/usr/bin/env bash
# scripts/check_layers.sh — падает, если хоть одна проверка что-то нашла (раздел 3 ТЗ)
modules="accounts organizations catalog sales payments ledger checkin notifications reports"

allowed() {  # от каких модулей можно зависеть (кроме common и самого себя)
  case "$1" in
    reports) echo "catalog sales ledger organizations" ;;
    checkin) echo "sales organizations" ;;
    payments) echo "sales ledger notifications" ;;
    sales) echo "catalog organizations notifications" ;;
    catalog) echo "organizations notifications" ;;
    organizations) echo "accounts notifications" ;;
    accounts) echo "notifications" ;;
  esac
}

out=$(
  for m in $modules; do
    [ -d "apps/$m" ] || continue
    # 1. чужие models, apis и tasks не импортируются
    grep -rnE "from apps\.[a-z_]+\.(models|apis|tasks) import" "apps/$m" --include='*.py' \
      | grep -v "from apps\.$m\."
    # 2. зависимости только вниз
    ok=" common $m $(allowed "$m") "
    for other in $modules; do
      [[ "$ok" == *" $other "* ]] && continue
      grep -rnE "from apps\.$other(\.| import)" "apps/$m" --include='*.py'
    done
  done
  # 3. домен без фреймворка
  grep -rnE "django|rest_framework" apps/sales/domain --include='*.py' 2>/dev/null
  # 4. common не зависит ни от одного модуля проекта
  for m in $modules; do
    grep -rnE "from apps\.$m(\.| import)" apps/common --include='*.py' 2>/dev/null
  done
)
if [ -n "$out" ]; then
  echo "$out"
  exit 1
fi
echo "check_layers: OK"
