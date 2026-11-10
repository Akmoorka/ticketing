#!/usr/bin/env bash
# scripts/check_history.sh <диапазон> — каждый коммит проходит тесты и назван
# по Conventional Commits. Пример: bash scripts/check_history.sh origin/main..HEAD
range="${1:-origin/main..HEAD}"
fail=0
pattern='^(feat|fix|docs|test|refactor|chore|perf|build|ci)(\([a-z0-9_-]+\))?!?: .+'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"; git worktree prune' EXIT

for sha in $(git rev-list --reverse "$range"); do
  subject=$(git log -1 --format=%s "$sha")
  if ! echo "$subject" | grep -qE "$pattern"; then
    echo "Коммит ${sha:0:7}: имя не по Conventional Commits: $subject"
    fail=1
  fi
  wt="$tmp/wt"
  git worktree add --detach "$wt" "$sha" >/dev/null 2>&1
  (cd "$wt" && python -m pytest -q -p no:cacheprovider >/dev/null 2>&1)
  code=$?
  git worktree remove --force "$wt" >/dev/null 2>&1
  # 5 = тестов в коммите ещё нет (например, самый первый коммит каркаса)
  if [ "$code" -ne 0 ] && [ "$code" -ne 5 ]; then
    echo "Коммит ${sha:0:7}: тесты не проходят: $subject"
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then exit 1; fi
echo "check_history: OK ($range)"
