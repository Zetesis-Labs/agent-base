#!/bin/bash
# Lintea solo los directorios de memoria con cambios staged.
dirs=$(git diff --cached --name-only | grep -oE '^projects/[^/]+/memory' | sort -u)
[ -z "$dirs" ] && exit 0
abs=""
for d in $dirs; do abs="$abs $HOME/.claude/$d"; done
python3 "$HOME/.claude/scripts/memory-lint.py" $abs || {
  echo; echo "memoria estructuralmente rota: arregla o commitea con --no-verify"; exit 1; }
