---
name: checkpoint
description: Use when the user asks to consolidate session state ("/checkpoint", "consolida la sesión", "guarda el estado", "haz checkpoint"), when a [checkpoint-nudge] message reports high context usage, or before ending a long working session. Distills the CURRENT conversation into SESSION.md at the repo root so a fresh session — Claude Code, Codex, or opencode — can resume the work without dragging the old context.
---

# Checkpoint de sesión

Destila el estado de la conversación actual en un `SESSION.md` versionable, para
matar la sesión y arrancar una nueva barata en lugar de arrastrar contexto o
confiar en un compact sin criterio.

## Dónde escribir

1. La raíz del repo git en el que se está trabajando (el principal de la tarea,
   no el multi-repo `Developer`).
2. Si no hay repo, el cwd.
3. Si ya existe `SESSION.md`, **consolidar, no pisar**: conservar lo aún
   vigente, mover lo resuelto a una línea breve en «Hecho», eliminar lo que ya
   no aplica. El fichero es el estado vivo, no un log acumulativo.

## Estructura obligatoria

```markdown
# Sesión: <tema en una frase> — actualizado <YYYY-MM-DD HH:MM>

## Objetivo
Qué se está intentando conseguir, en 1-3 líneas.

## Estado actual
Qué está hecho Y VERIFICADO (con commit/PR si aplica) y qué está a medias.
Separar siempre «hecho» de «hecho y comprobado».

## Decisiones y porqués
Cada decisión con su porqué en una línea. Sin el porqué no vale.

## Hipótesis descartadas
Con la evidencia que las mató. Esta sección evita re-investigar callejones
sin salida — es la más valiosa cuando la sesión fue de diagnóstico.

## Pendientes
Accionables, cada uno con su siguiente paso concreto (comando, fichero, PR).

## Gotchas descubiertos
Trampas del entorno/stack encontradas en esta sesión que costaría redescubrir.

## Referencias
Commits, PRs, ficheros clave, URLs. Nada de prosa.
```

## Criterios de destilado

- **Verificable sobre narrativo**: «X arreglado en commit abc123» sí; «estuvimos
  arreglando X» no.
- **Fechas absolutas** siempre (nunca «hoy», «esta noche»).
- Estado ≠ historia: lo que ya no condiciona el futuro se cae.
- Máximo ~150 líneas. Si crece más, se está acumulando en vez de consolidar.
- **Nunca secretos** (tokens, contraseñas, URLs firmadas).
- Lo que sea un hecho DURABLE del proyecto (no de la tarea) va a la memoria
  persistente o al CLAUDE.md del repo, no aquí.

## Después de escribir

1. Decir al usuario en una línea qué se consolidó y dónde.
2. Recordarle el flujo: matar esta sesión y arrancar una nueva con
   «Lee SESSION.md y continúa con <pendiente>».
3. Si el SESSION.md revela un hecho durable no registrado, proponer (no
   ejecutar) guardarlo en memoria persistente.
