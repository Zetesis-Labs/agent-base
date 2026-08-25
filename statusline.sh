#!/usr/bin/env python3
"""Statusline de Claude Code: modelo, directorio, rama y contexto usado.

Además de pintar, deja el porcentaje en un fichero por sesión para que el hook
de UserPromptSubmit (checkpoint-nudge) pueda avisar dentro de la conversación
cuando toca hacer /checkpoint — la statusline es el único sitio que recibe
`context_window.used_percentage`, los hooks no lo reciben.
"""

import json
import os
import subprocess
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

model = data.get("model", {}).get("display_name", "?")
cwd = data.get("workspace", {}).get("current_dir") or data.get("cwd") or ""
pct_raw = data.get("context_window", {}).get("used_percentage")
pct = int(pct_raw) if isinstance(pct_raw, (int, float)) else None
session = data.get("session_id", "")

branch = ""
try:
    branch = subprocess.run(
        ["git", "-C", cwd or ".", "branch", "--show-current"],
        capture_output=True, text=True, timeout=1
    ).stdout.strip()
except Exception:
    pass

if session and pct is not None:
    try:
        d = os.path.expanduser("~/.claude/tmp/ctx")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, session), "w") as f:
            f.write(str(pct))
    except Exception:
        pass

parts = [f"[{model}]", f"📁 {os.path.basename(cwd) or '?'}"]
if branch:
    parts.append(f"⎇ {branch}")
if pct is not None:
    filled = min(8, round(pct / 12.5))
    bar = "▓" * filled + "░" * (8 - filled)
    ctx = f"{bar} {pct}%"
    if pct >= 70:
        ctx += "  ⚠️ /checkpoint"
    parts.append(ctx)

print(" | ".join(parts))
