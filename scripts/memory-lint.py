#!/usr/bin/env python3
"""Lint estructural de la memoria persistente. Uso: memory-lint.py [dir ...]
Sin args lintea todos los projects/*/memory. Sale 1 si hay errores; los avisos
se muestran pero no hacen fallar."""
import re, sys
from pathlib import Path

TYPES = {"user", "feedback", "project", "reference"}
ROOT = Path.home() / ".claude/projects"
# Claude Code escribe `name` como slug con guiones y enlaza por él ([[slug]]);
# las memorias antiguas usan el nombre del fichero. Valen las dos formas.
RE_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else None

def lint_dir(d):
    errors, warnings = [], []
    files = sorted(p for p in d.glob("*.md") if p.name != "MEMORY.md")
    declared = {}
    for p in files:
        fm = frontmatter(p.read_text(encoding="utf-8")) or ""
        n = re.search(r"^name:\s*(\S+)", fm, re.M)
        if n: declared.setdefault(n.group(1), []).append(p.name)
    names = {p.stem for p in files} | set(declared)
    for name, owners in declared.items():
        if len(owners) > 1: errors.append(f"{d.parent.name}: name '{name}' repetido en {', '.join(owners)}")
    for p in files:
        text = p.read_text(encoding="utf-8")
        rel = f"{d.parent.name}/{p.name}"
        fm = frontmatter(text)
        if fm is None:
            errors.append(f"{rel}: sin frontmatter"); continue
        name = re.search(r"^name:\s*(\S+)", fm, re.M)
        if not name: errors.append(f"{rel}: falta name:")
        elif name.group(1) != p.stem and not RE_SLUG.match(name.group(1)):
            errors.append(f"{rel}: name '{name.group(1)}' no es un slug con guiones ni el nombre del fichero")
        if not re.search(r"^description:\s*\S", fm, re.M): errors.append(f"{rel}: falta description:")
        t = re.search(r"^\s*type:\s*(\S+)", fm, re.M)
        if not t: errors.append(f"{rel}: falta metadata.type")
        elif t.group(1) not in TYPES: errors.append(f"{rel}: type '{t.group(1)}' invalido")
        elif t.group(1) in ("feedback", "project") and "**Why:**" not in text:
            errors.append(f"{rel}: type {t.group(1)} sin **Why:**")
        prose = re.sub(r"```.*?```", "", text, flags=re.S)
        prose = re.sub(r"`[^`\n]*`", "", prose)
        for link in re.findall(r"\[\[([^\]|#]+)", prose):
            # Un enlace sin destino marca una memoria por escribir, no un error.
            if link.strip() not in names: warnings.append(f"{rel}: [[{link.strip()}]] sin memoria")
    idx = d / "MEMORY.md"
    if files and not idx.exists():
        errors.append(f"{d.parent.name}: falta MEMORY.md")
    elif idx.exists():
        itext = idx.read_text(encoding="utf-8")
        nlines, nbytes = itext.count("\n") + 1, len(itext.encode())
        if nlines > 200 or nbytes > 25_000:
            errors.append(f"{d.parent.name}/MEMORY.md: indice demasiado grande ({nlines} lineas, {nbytes}B) — riesgo de truncado en la carga")
        linked = set(re.findall(r"\]\(([^)]+\.md)\)", itext))
        for l in linked:
            if not (d / l).exists(): errors.append(f"{d.parent.name}/MEMORY.md: apunta a {l} inexistente")
        for p in files:
            if p.name not in linked: errors.append(f"{d.parent.name}/MEMORY.md: {p.name} sin entrada en el indice")
    return errors, warnings, len(files)

dirs = [Path(a) for a in sys.argv[1:]] or sorted(ROOT.glob("*/memory"))
total_err, total_warn, total_files = [], [], 0
for d in dirs:
    if not d.is_dir(): continue
    errs, warns, n = lint_dir(d)
    total_err += errs; total_warn += warns; total_files += n
for w in total_warn: print(f"AVISO  {w}")
for e in total_err: print(f"ERROR  {e}")
print(f"\n{total_files} memorias, {len(total_err)} errores, {len(total_warn)} avisos")
sys.exit(1 if total_err else 0)
