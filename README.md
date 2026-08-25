# agent-base

Base tooling for a versioned, single-source `~/.claude` — the home directory of
your AI coding agents — consumed from your own private dotfiles repo.

Three independent pieces. Take what you need.

## 1. `scripts/sync-agents.py` — one agent definition, every CLI

You write agents once, in Claude Code's format (`~/.claude/agents/*.md`).
The script publishes them to the other CLIs, **translating the parts each tool
defines differently** instead of symlinking files that would fail their
validators:

| Target | What it does |
|---|---|
| opencode | real subagents in `~/.config/opencode/agent/` — frontmatter rewritten (`mode`, color palette mapping, write-tools disabled for read-only agents) |
| Codex | skills in `~/.codex/skills/` — Codex's validator rejects any frontmatter key beyond `name`/`description`, so everything else is stripped and the description flattened to one line |
| Antigravity (`agy`) | the published directory registered once in `~/.gemini/config/skills.json` |

Generated files carry a marker line and are overwritten on every run; files
without the marker are never touched. Agents removed from the source are
retired from the targets. `--dry-run` shows the plan.

Skills in `~/.claude/skills/` are published as-is (same format everywhere).

## 2. `scripts/memory-lint.py` — structural validation of persistent memory

For the file-based memory layout `projects/*/memory/*.md` (one fact per file,
frontmatter with `name`/`description`/`metadata.type`, a `MEMORY.md` index).
Checks: name matches filename, valid type, `**Why:**` present where the type
demands it, no broken `[[wikilinks]]`, index complete, index small enough to
load without truncation.

`scripts/pre-commit-memory-lint.sh` wires it as a git pre-commit hook that
lints only the staged memory directories.

## 3. Session checkpoints — a criteria-driven alternative to blind compaction

Long agent sessions accumulate context until an automatic compaction summarizes
them with no criteria of yours. This layer replaces that with an auditable
file:

- **`skills/checkpoint/SKILL.md`** — a `/checkpoint` skill that distills the
  session into `SESSION.md` at the repo root: goal, verified state, decisions
  with their why, **discarded hypotheses with the evidence that killed them**,
  actionable pendings, gotchas. Consolidates instead of appending. Any agent
  (Claude Code, Codex, opencode) resumes from it: kill the session, start a
  fresh one with "read SESSION.md and continue".
- **`statusline.sh`** — Claude Code statusline showing model, dir, branch and
  context usage; past 70% it shows a `/checkpoint` warning. It also writes the
  percentage to a per-session file, because hooks don't receive context usage —
  the statusline does.
- **`hooks/checkpoint-nudge.py`** — `UserPromptSubmit` hook that reads that
  file and, past the threshold, injects a note asking the assistant to propose
  `/checkpoint`. Fails open: it can never break a prompt.

## Install

Consume it as a submodule of your private `~/.claude` repo and symlink:

```bash
cd ~/.claude
git submodule add https://github.com/Zetesis-Labs/agent-base base
ln -s base/scripts/sync-agents.py scripts/sync-agents.py
ln -s base/scripts/memory-lint.py scripts/memory-lint.py
ln -s ../base/hooks/checkpoint-nudge.py hooks/checkpoint-nudge.py
ln -s base/statusline.sh statusline.sh
ln -s ../base/skills/checkpoint skills/checkpoint
```

Then reference the hook and statusline in `settings.json`:

```json
{
  "statusLine": { "type": "command", "command": "~/.claude/statusline.sh" },
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [{ "type": "command", "command": "~/.claude/hooks/checkpoint-nudge.py" }] }
    ]
  }
}
```

## Agents included

`agents/` ships ready-to-use agents in Claude Code format — `sync-agents.py`
publishes them to the other CLIs like any of yours:

| Agent | What it does |
|---|---|
| `code-reviewer` | reviews the branch diff against your house rules (encoded in the prompt — edit them to match yours) and hunts bugs, reporting only ≥80% confidence findings |
| `silent-failure-hunter` | hunts places where errors vanish silently: empty catches, unchecked fetch, fallbacks hiding bugs, streams swallowing errors |
| `pr-test-analyzer` | catalogs which behaviors in a PR deserve tests, prioritized by risk (P0 money/auth/data-integrity → P3 UI) |
| `commit-prep` | turns raw changes into atomic conventional commits with a full PR description |
| `docs-updater` | brings the repo docs (CLAUDE.md, READMEs, architecture docs) in line with the code after a change |
| `memory-gardener` | audits the persistent memory this repo's layout defines: stale or false memories (verified against disk), duplicates, broken indexes |

These are copies, not symlinks, on purpose: Claude Code appends
machine-specific sections (agent memory paths) to agent files in
`~/.claude/agents/`, so a live link would leak local paths into this repo.

Code comments are in Spanish.

## License

MIT
