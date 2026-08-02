# CLAUDE.md — RiverCast (labs/03_advanced/rivercast)

Operating rules for coding agents (Claude Code and equivalents) working in this directory. Read this file and `PROGRESS.md` before starting any task.

## Scope

You build under maintainer review, the same as any other contribution — see rule 21. You are not expected to run inside a trainee's OpenShift AI workbench: that environment has no Node.js runtime or package-registry egress by design (plan §2.6). Do your work in whatever environment you're invoked from; trainees only see the finished notebooks, package, and pipelines once merged.

## Source of truth

- Full plan: `PLAN.md` — phase definitions, acceptance criteria, and deliverables live there. This file only carries operating rules.
- Phase status: `PROGRESS.md` in this directory. Read it first — it says which phase is active and what's already merged.

## Operating rules

1. One phase per pull request. Do not bundle phases.
2. Do not proceed to the next phase until the current phase's acceptance criteria (in the plan) pass.
3. No network calls in unit tests.
4. All external calls require timeout, retry with backoff, and explicit error messages.
5. Every live data adapter must have a deterministic fixture adapter with the same output schema.
6. Store timestamps internally in UTC.
7. Preserve original source timestamps and offsets.
8. Never use future observations to construct features.
9. Never overwrite raw data.
10. Every dataset and model must be traceable to: source window, station UUIDs, schema version, feature version, Git commit, container image digest.
11. Use immutable image tags or digests in pipeline specs.
12. Keep thresholds and station selections in configuration, not code.
13. Fail closed: invalid data must stop training and promotion.
14. A deployment failure must not move the `champion` alias.
15. Fixture mode is the default for workshops and CI.
16. Write notebooks and docs for the trainee's JupyterLab workbench, but don't assume you (the agent) run there yourself — see Scope above.
17. Keep notebook cells thin: configuration, function calls, visualizations, explanations. No business logic in cells.
18. A notebook is not accepted unless it passes a fresh-kernel run-all smoke test. Verify this headlessly with `jupyter nbconvert --to notebook --execute` (or `papermill`) before opening a PR — do not rely on a human clicking "Restart & Run All" to catch this.
19. Do not assume Docker is available inside the workbench.
20. Compile pipeline YAML in the workbench; build immutable images in CI or an approved cluster build service.
21. Every phase's pull request requires explicit maintainer review and approval before merge. Open the PR and stop: do not self-merge, do not merge on green CI alone, and do not mark a phase `done` in `PROGRESS.md` — only the maintainer does that, after merging.

## Before starting a session

1. Read `PROGRESS.md` for the current phase.
2. Read that phase's section in the plan (`## Phase N — ...`) for Build steps, acceptance criteria, and deliverables.
3. Confirm required external connections for this phase (object storage, MLflow, cluster API) are configured in your environment. If they're not, stop and flag it rather than mocking around it.

## Before opening a PR

- `make lint`, `make typecheck`, `make test` all pass.
- Fixture-mode tests pass with no network access.
- The phase's acceptance criteria (in the plan) are met — self-check against them, and call out any you couldn't verify (e.g. ones needing live cluster infra you don't have).
- Update `PROGRESS.md`: set the phase to `in review`, link the PR. Leave `done` for the maintainer to set after merge.
