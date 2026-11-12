# 2026-11-12 — Infra: session logging + GitHub push setup

## User request
- Make session logging + push-to-GitHub part of the standing loop (Claude.md).
- Push everything (code, docs, roadmap, next steps, dataset reports) to
  https://github.com/devg81/SYSDAG; clearly report anything kept out of git.
- Status question: where we stand, steps left to ECG, then SaaS.

## Done
- `docs/Claude.md`: added §24.1 (mandatory session log every session),
  §37.1 (commit + push every session, what never gets committed), and the
  log+push steps to the §16 loop and §41 loop command.
- Root `CLAUDE.md` restored as a pointer that imports `docs/Claude.md`
  (Claude Code only auto-loads the root file).
- `.gitignore`: added secrets patterns and `syngen/SynGen.zip`.
- First full push of the project.

## Kept out of git (deliberately)
| Path | Why |
|---|---|
| `outputs/` | Full generated datasets (100K JSON, v0.8/v0.9). Too big; reproducible from code+seed+config. Reports are in `docs/`. |
| `syngen/SynGen.zip` (4.9 GB) | Over GitHub 100 MB limit; legacy archive incl. PTB-XL. |
| `syngen/**/dataset/`, `*.npy`, `*.pt`, `checkpoints/` | PTB-XL download + GAN weights; re-downloadable / large. |
| `.env*`, keys | Secrets (none exist today). |

## Status summary given to user
Patient-record layer ~85-90% done (100K validated, v0.8 frozen; v0.9 package
built). Remaining before ECG: sign-off on family-history + AQI plans, apply
D019 lipid fix, single re-freeze + validate. Then ECG: license check on
SSSD-ECG weights, model decision (M6), integration, generation, validation.

## Commit
See `git log` for this session's commit hash.
