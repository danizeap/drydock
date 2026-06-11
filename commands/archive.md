---
description: Archive a completed SDD+ change after all gates pass
---
Archive the SDD+ change: $ARGUMENTS

Gates, in order — stop at the first failure:
1. **Verification**: run `/drydock:verify` logic for this change. BLOCKED verdict → do not archive.
2. **Spec sync**: if the change has delta specs, confirm they are synced into `sdd-plus/specs/capabilities/`; if not, offer to run the `spec-sync` skill now. Recommend syncing; archiving unsynced requires the Owner's explicit choice.
3. **API blocking rule**: if the change introduced or modified any API contract (endpoints, request/response shapes, auth behavior, status codes, webhooks), the relevant capability spec and any API documentation MUST be updated before archive. No undocumented API changes ship.
4. **Documentation**: update README, standards, or specs affected by the change per `sdd-plus/standards/documentation-standards.md`.
5. Run `python scripts/sdd.py archive <name>` (it independently re-checks tasks and placeholders; `--force` only with the Owner's explicit approval).
6. For deployable changes, remind the Owner whether LaunchGuardian review has happened.
