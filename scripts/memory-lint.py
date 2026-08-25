#!/usr/bin/env python3
"""Lint estructural de la memoria persistente. Uso: memory-lint.py [dir ...]
Sin args lintea todos los projects/*/memory. Sale 1 si hay errores."""
import re, sys
from pathlib import Path

TYPES = {"user", "feedback", "project", "reference"}
ROOT = Path.home() / ".claude/projects"

def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else None

def lint_dir(d):
    errors, files = [], sorted(p for p in d.glob("*.md") if p.name != "MEMORY.md")
    names = {p.stem for p in files}
    for p in files:
        text = p.read_text(encoding="utf-8")
        rel = f"{d.parent.name}/{p.name}"
        fm = frontmatter(text)
        if fm is None:
            errors.append(f"{rel}: sin frontmatter"); continue
        name = re.search(r"^name:\s*(\S+)", fm, re.M)
        if not name: errors.append(f"{rel}: falta name:")
        elif name.group(1) != p.stem: errors.append(f"{rel}: name '{name.group(1)}' != fichero '{p.stem}'")
        if not re.search(r"^description:\s*\S", fm, re.M): errors.append(f"{rel}: falta description:")
        t = re.search(r"^\s*type:\s*(\S+)", fm, re.M)
        if not t: errors.append(f"{rel}: falta metadata.type")
        elif t.group(1) not in TYPES: errors.append(f"{rel}: type '{t.group(1)}' invalido")
        elif t.group(1) in ("feedback", "project") and "**Why:**" not in text:
            errors.append(f"{rel}: type {t.group(1)} sin **Why:**")
        prose = re.sub(r"```.*?```", "", text, flags=re.S)
        prose = re.sub(r"`[^`\n]*`", "", prose)
        for link in re.findall(r"\[\[([^\]|#]+)", prose):
            if link.strip() not in names: errors.append(f"{rel}: wikilink roto [[{link.strip()}]]")
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
    return errors, len(files)

dirs = [Path(a) for a in sys.argv[1:]] or sorted(ROOT.glob("*/memory"))
total_err, total_files = [], 0
for d in dirs:
    if not d.is_dir(): continue
    errs, n = lint_dir(d)
    total_err += errs; total_files += n
for e in total_err: print(f"ERROR  {e}")
print(f"\n{total_files} memorias, {len(total_err)} errores")
sys.exit(1 if total_err else 0)
