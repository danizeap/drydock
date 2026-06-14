# Changelog

## 0.1.4
- Cross-platform fix: commands and docs now invoke `python3` (with a Windows `python` note) and state an interpreter-resolution rule, instead of bare `python` which dead-ends on modern macOS where no `python` exists. README now documents the Python 3.9+ prerequisite.
- Re-saved README.md as clean UTF-8, fixing mojibake (garbled `⚓`, em-dashes, apostrophes) that showed on the GitHub and marketplace listings.
- Synced the scaffold copies of CLAUDE.md and AGENTS.md with their authoritative versions (the scaffold CLAUDE.md had been shipping stale single-hook documentation to new installs).
- Refreshed stale "0.1.1" version reference in the AI operator guide.

## 0.1.3
- Archive sync gate now checks that a delta's ADDED requirements are actually present in the living capability spec, not merely that the capability file exists. Closes a silent gap where a change could archive with an unsynced delta after the capability's first sync. ADDED requirements only; MODIFIED/REMOVED/RENAMED remain a known limitation.

## 0.1.2
- Fix stale `/sdd:sync` reference in `sdd.py` archive gate → now `/drydock:sync` (both the plugin copy and the distributed scaffold copy).
- `init` now creates `sdd-plus/specs/capabilities/`, the directory the archive gate checks against; previously every delta read as unsynced on fresh installs.
- Move the script-resolution rule out of `status.md` YAML frontmatter into the command body where it takes effect.
- Verifier subagent now checks skill blocking-rules at both the plugin-root and portability-copy paths, instead of assuming `.claude/skills/`.
- Document both PreToolUse hooks (secrets-path and git-safety) in `CLAUDE.md`; previously only secrets protection was mentioned.

## 0.1.1

- Surface the optional LaunchGuardian scanner (`pip install launchguardian`) at first touch: scanner detection in `/drydock:init-project`, a pointer in `/drydock:onboard`'s closing recap, and an availability check in the launchguardian skill before any scan commands.


## 0.1.0 — first public release

- Drydock plugin: 12 governed skills, 9 lifecycle commands, independent `verifier` subagent.
- Safety hooks: secrets-file protection (Write/Edit) and destructive-git guard (Bash).
- `/drydock:init-project` scaffolds the SDD+ project structure into any repo (never overwrites).
- `/drydock:onboard` guided first change.
- Spec lifecycle: delta specs (SHALL + WHEN/THEN) merged into living capability specs via `spec-sync`; gated archive with API blocking rule.
- LaunchGuardian Framework (22 security gates) with templates; companion scanner: `launchguardian-cli`.
- Cross-platform `sdd.py` change-packet tool with placeholder and sync gates.
