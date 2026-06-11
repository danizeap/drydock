# Changelog

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
