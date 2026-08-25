#!/usr/bin/env python3
"""Hook UserPromptSubmit: aviso de checkpoint cuando el contexto se llena.

Lee el porcentaje que la statusline deja en ~/.claude/tmp/ctx/<session_id>
(los hooks no reciben el uso de contexto; la statusline sí) y, al cruzar el
umbral, emite texto plano por stdout — que en UserPromptSubmit entra como
contexto para el asistente — pidiéndole que proponga /checkpoint al usuario.

Rate-limit: un aviso al cruzar 70 y otro por cada +10 puntos, guardando el
último porcentaje avisado por sesión. Falla siempre abierto: cualquier error
sale con 0 y sin ruido — este hook jamás debe romper un prompt.
"""

import json
import os
import sys

UMBRAL = 70
PASO = 10

try:
    data = json.load(sys.stdin)
    session = data.get("session_id", "")
    if not session:
        sys.exit(0)

    base = os.path.expanduser("~/.claude/tmp/ctx")
    pct_file = os.path.join(base, session)
    mark_file = pct_file + ".avisado"

    with open(pct_file) as f:
        pct = int(f.read().strip())

    avisado = -1
    if os.path.exists(mark_file):
        with open(mark_file) as f:
            avisado = int(f.read().strip() or -1)

    if pct >= UMBRAL and pct >= avisado + PASO:
        with open(mark_file, "w") as f:
            f.write(str(pct))
        print(
            f"[checkpoint-nudge] El contexto de esta sesión está al {pct}%. "
            "Sugiere al usuario hacer /checkpoint AHORA para consolidar el "
            "estado en SESSION.md antes de que el auto-compact lo resuma sin "
            "criterio; si estás en mitad de una acción, termina esa acción "
            "primero y proponlo justo después. No repitas este aviso si el "
            "usuario lo declina."
        )
except Exception:
    pass
sys.exit(0)
