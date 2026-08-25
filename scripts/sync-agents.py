#!/usr/bin/env python3
"""Publica los agentes de ~/.claude al resto de CLIs de agentes.

Fuente única: ~/.claude/agents/*.md (formato Claude Code).

Se publica UNA vez en ~/.claude/cli/skills-publicadas/ y de ahí consumen varias
CLIs, en vez de escribir una copia por herramienta:
  - opencode:    ~/.config/opencode/agent/<name>.md   (subagente de verdad)
  - Codex:       ~/.codex/skills -> el directorio publicado
  - Antigravity: registrado en ~/.gemini/config/skills.json

El cuerpo del prompt se copia tal cual; lo único que cambia es el frontmatter,
que cada herramienta define a su manera. Los destinos son ficheros generados:
se sobrescriben en cada pasada y llevan una marca en cabecera. Editar la fuente,
nunca el destino.

Nota sobre Codex (verificado en codex-cli 0.148.0): sus subagentes son
herramientas del modelo (`spawn_agent`/`resume_agent`), genéricas y sin fichero
de definición, así que no hay donde declarar uno propio. Lo que sí carga son
skills en `~/.codex/skills/<name>/SKILL.md`, mismo formato que Anthropic, con
`skill_search` activo. Publicamos ahí: el agente deja de ser un proceso aparte y
pasa a ser un procedimiento que Codex carga cuando aplica — puede combinarlo con
su propio `spawn_agent`. Su validador exige `name` en hyphen-case y
`description`, y RECHAZA cualquier otra clave de frontmatter.

Antigravity (CLI `agy`) usa el mismo formato SKILL.md y admite registrar
directorios externos por `skills.json`, así que consume el publicado sin copia.
Sus reglas salen de GEMINI.md / AGENTS.md, ya symlinkeados.

Gemini CLI y qwen solo comparten instrucciones (GEMINI.md / QWEN.md, symlink).

Uso:  python3 sync-agents.py [--dry-run]
"""

import json
import re
import sys
from pathlib import Path

HOME = Path.home()
SRC = HOME / ".claude/agents"
SKILLS = HOME / ".claude/skills"
OPENCODE = HOME / ".config/opencode/agent"

# Un solo directorio publicado, N consumidores: Codex lo monta como su
# ~/.codex/skills y Antigravity lo registra en skills.json. Es contenido
# generado, así que va ignorado por git.
PUBLICADAS = HOME / ".claude/cli/skills-publicadas"
CODEX = PUBLICADAS
CODEX_ENLACE = HOME / ".codex/skills"
ANTIGRAVITY_CFG = HOME / ".gemini/config/skills.json"

RE_NOMBRE_CODEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

MARCA = "<!-- generado por agent-base (sync-agents.py) — no editar aquí -->"

# Herramientas de escritura de opencode, verificadas contra su binario 1.18.15.
ESCRITURA_OPENCODE = ("write", "edit", "patch")

# opencode rechaza los nombres de color de Claude Code: exige hex o su paleta
# semántica. Lo que no se pueda traducir se omite, que es cosmético.
COLOR_OPENCODE = {
    "red": "error",
    "orange": "warning",
    "yellow": "warning",
    "green": "success",
    "blue": "info",
    "cyan": "info",
    "purple": "accent",
    "magenta": "accent",
    "pink": "accent",
}


def parsear(texto):
    """Devuelve (frontmatter como dict de strings, cuerpo). Parseo deliberadamente
    simple: el frontmatter de un agente es plano, sin anidamiento ni listas YAML."""
    if not texto.startswith("---"):
        return {}, texto
    cierre = texto.find("\n---", 3)
    if cierre == -1:
        return {}, texto
    cabecera = texto[3:cierre]
    cuerpo = texto[cierre + 4 :].lstrip("\n")
    campos = {}
    for linea in cabecera.splitlines():
        if ":" in linea and not linea.startswith((" ", "\t", "#")):
            clave, _, valor = linea.partition(":")
            campos[clave.strip()] = valor.strip().strip("\"'")
    return campos, cuerpo


def escapa(valor):
    return valor.replace("\\", "\\\\").replace('"', '\\"')


def es_solo_lectura(tools_claude):
    """Un agente de Claude declarado con una lista de tools que no incluye
    ninguna de escritura debe seguir sin poder escribir en opencode."""
    if not tools_claude:
        return False
    declaradas = {t.strip().lower() for t in tools_claude.split(",")}
    if "*" in declaradas or "all tools" in tools_claude.lower():
        return False
    return not declaradas & {"write", "edit", "notebookedit"}


def aplanar(texto, tope=900):
    """Codex carga la description en contexto para decidir relevancia: debe caber
    en una línea. Las de Claude traen ejemplos con saltos escapados."""
    plano = re.sub(r"\s+", " ", texto.replace("\\n", " ")).strip()
    if len(plano) > tope:
        corte = plano.rfind(". ", 0, tope)
        plano = plano[: corte + 1] if corte > tope // 2 else plano[:tope].rstrip() + "…"
    return plano


def a_codex(nombre, campos, cuerpo):
    lineas = [
        "---",
        f"name: {nombre}",
        f'description: "{escapa(aplanar(campos.get("description", "")))}"',
        "---",
        "",
        MARCA,
        "",
    ]
    if es_solo_lectura(campos.get("tools", "")):
        lineas += ["> Procedimiento de solo lectura: analiza y propone, no aplica cambios.", ""]
    lineas += [cuerpo.rstrip(), ""]
    return "\n".join(lineas)


def a_opencode(campos, cuerpo):
    lineas = ["---", f'description: "{escapa(campos.get("description", ""))}"', "mode: subagent"]
    color = COLOR_OPENCODE.get(campos.get("color", "").lower())
    if color:
        lineas.append(f"color: {color}")
    if es_solo_lectura(campos.get("tools", "")):
        lineas.append("tools:")
        for t in ESCRITURA_OPENCODE:
            lineas.append(f"  {t}: false")
    lineas += ["---", "", MARCA, "", cuerpo.rstrip(), ""]
    return "\n".join(lineas)


def leer_agentes():
    agentes, saltados = [], []
    for fuente in sorted(SRC.glob("*.md")):
        campos, cuerpo = parsear(fuente.read_text())
        nombre = campos.get("name") or fuente.stem
        if not campos.get("description"):
            saltados.append((fuente.name, "sin description: no se registraría"))
            continue
        agentes.append((nombre, campos, cuerpo))
    return agentes, saltados


def publicar_opencode(agentes, seco):
    OPENCODE.mkdir(parents=True, exist_ok=True)
    hechos, avisos = [], []
    for nombre, campos, cuerpo in agentes:
        destino = OPENCODE / f"{nombre}.md"
        if destino.exists() and MARCA not in destino.read_text():
            avisos.append(f"{destino.name}: existe y no lo generamos nosotros")
            continue
        if not seco:
            destino.write_text(a_opencode(campos, cuerpo))
        hechos.append(nombre + (" (solo lectura)" if es_solo_lectura(campos.get("tools", "")) else ""))

    vivos = {h.split(" (")[0] for h in hechos}
    retirados = []
    for viejo in sorted(OPENCODE.glob("*.md")):
        if viejo.stem not in vivos and MARCA in viejo.read_text():
            retirados.append(viejo.stem)
            if not seco:
                viejo.unlink()
    return hechos, retirados, avisos


def publicar_codex(agentes, seco):
    CODEX.mkdir(parents=True, exist_ok=True)
    hechos, avisos = [], []
    for nombre, campos, cuerpo in agentes:
        if not RE_NOMBRE_CODEX.match(nombre):
            avisos.append(f"{nombre}: Codex exige hyphen-case, se omite")
            continue
        skill = CODEX / nombre / "SKILL.md"
        if skill.exists() and MARCA not in skill.read_text():
            avisos.append(f"{nombre}: ya existe una skill que no generamos nosotros")
            continue
        if not seco:
            skill.parent.mkdir(parents=True, exist_ok=True)
            skill.write_text(a_codex(nombre, campos, cuerpo))
        hechos.append(nombre + (" (solo lectura)" if es_solo_lectura(campos.get("tools", "")) else ""))

    vivos = {h.split(" (")[0] for h in hechos}
    retirados = []
    for viejo in sorted(p for p in CODEX.glob("*/SKILL.md")):
        if viejo.parent.name not in vivos and MARCA in viejo.read_text():
            retirados.append(viejo.parent.name)
            if not seco:
                viejo.unlink()
                try:
                    viejo.parent.rmdir()
                except OSError:
                    pass
    return hechos, retirados, avisos


def publicar_skills_codex(seco):
    """Codex usa el mismo formato SKILL.md que Claude Code, así que las skills van
    por symlink al directorio: sin copia, sin desincronización. Verificado que
    carga incluso las que traen `license` en el frontmatter."""
    if not SKILLS.is_dir():
        return [], [], []
    CODEX.mkdir(parents=True, exist_ok=True)
    hechos, avisos = [], []
    for origen in sorted(SKILLS.iterdir()):
        if not (origen / "SKILL.md").is_file():
            continue
        if origen.is_symlink():
            avisos.append(f"{origen.name}: es un symlink externo, se omite")
            continue
        destino = CODEX / origen.name
        if destino.exists() and not destino.is_symlink():
            avisos.append(f"{origen.name}: ya existe como directorio propio en Codex")
            continue
        if not seco:
            if destino.is_symlink():
                destino.unlink()
            destino.symlink_to(origen)
        hechos.append(origen.name)
    return hechos, [], avisos


def montar_codex(seco):
    """Codex escanea ~/.codex/skills, donde tambien viven sus propias skills de
    sistema (.system): no se puede sustituir el directorio por un symlink, asi
    que enlazamos entrada por entrada al directorio publicado."""
    if not CODEX_ENLACE.parent.is_dir():
        return None
    CODEX_ENLACE.mkdir(parents=True, exist_ok=True)
    enlazados, ajenos = 0, []
    publicadas = {d.name for d in PUBLICADAS.iterdir() if (d / "SKILL.md").is_file()} if PUBLICADAS.is_dir() else set()

    for nombre in sorted(publicadas):
        destino = CODEX_ENLACE / nombre
        if destino.is_symlink():
            if destino.readlink() == PUBLICADAS / nombre:
                enlazados += 1
                continue
            if not seco:
                destino.unlink()
        elif destino.exists():
            skill = destino / "SKILL.md"
            propio = skill.is_file() and MARCA in skill.read_text()
            if not propio:
                ajenos.append(nombre)
                continue
            if not seco:  # copia de una version anterior del script: se sustituye
                for resto in sorted(destino.rglob("*"), reverse=True):
                    resto.rmdir() if resto.is_dir() else resto.unlink()
                destino.rmdir()
        if not seco:
            destino.symlink_to(PUBLICADAS / nombre)
        enlazados += 1

    # Retirar enlaces nuestros que ya no tienen origen.
    for viejo in sorted(CODEX_ENLACE.iterdir()):
        if viejo.is_symlink() and str(viejo.readlink()).startswith(str(PUBLICADAS)):
            if viejo.name not in publicadas and not seco:
                viejo.unlink()

    aviso = f"; ajenas respetadas: {', '.join(ajenos)}" if ajenos else ""
    return f"{enlazados} skills enlazadas (sus .system intactas){aviso}"


def registrar_antigravity(seco):
    """Antigravity admite registrar directorios externos en skills.json, así que
    no hace falta copiar nada. Se conserva lo que ya hubiera declarado."""
    if not ANTIGRAVITY_CFG.parent.is_dir():
        return None
    ruta = str(PUBLICADAS)
    cfg = {}
    if ANTIGRAVITY_CFG.is_file():
        try:
            cfg = json.loads(ANTIGRAVITY_CFG.read_text() or "{}")
        except json.JSONDecodeError:
            return "NO registrado: skills.json existe y no es JSON válido"
    entradas = cfg.setdefault("entries", [])
    if any(e.get("path") == ruta for e in entradas if isinstance(e, dict)):
        return "ya registrado"
    entradas.append({"path": ruta})
    if not seco:
        ANTIGRAVITY_CFG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    return "registrado"


def main():
    seco = "--dry-run" in sys.argv
    if not SRC.is_dir():
        sys.exit(f"no existe la fuente: {SRC}")

    agentes, saltados = leer_agentes()
    prefijo = "[dry-run] " if seco else ""

    for etiqueta, dir_padre, publicar in (
        ("opencode", OPENCODE.parent, publicar_opencode),
        ("publicadas como skills", PUBLICADAS.parent, publicar_codex),
    ):
        if not dir_padre.is_dir():
            print(f"{prefijo}{etiqueta}: no instalado, se omite")
            continue
        hechos, retirados, avisos = publicar(agentes, seco)
        print(f"{prefijo}{etiqueta}: {len(hechos)} agentes publicados")
        for h in hechos:
            print(f"  + {h}")
        for r in retirados:
            print(f"  - {r} (retirado: ya no está en la fuente)")
        for a in avisos:
            print(f"  ! {a}")

    if PUBLICADAS.parent.is_dir():
        hechos, _, avisos = publicar_skills_codex(seco)
        print(f"{prefijo}publicadas (skills de Claude Code): {len(hechos)} enlazadas")
        for h in hechos:
            print(f"  + {h}")
        for a in avisos:
            print(f"  ! {a}")

    for etiqueta, resultado in (
        ("Codex", montar_codex(seco)),
        ("Antigravity (agy)", registrar_antigravity(seco)),
    ):
        if resultado is None:
            print(f"{prefijo}{etiqueta}: no instalado, se omite")
        else:
            print(f"{prefijo}{etiqueta}: {resultado}")

    for nombre, motivo in saltados:
        print(f"! {nombre}: {motivo}")


if __name__ == "__main__":
    main()
