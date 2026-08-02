# PEGELONLINE fixtures

Deterministic fixture data for offline (fixture-mode) runs. Populated in
Phase 2 by the data-viability spike; until then this directory is an empty
placeholder so environment checks can point at it.

Rules (ADR 0002): fixtures are committed, deterministic, and share the exact
output schema of the live adapter. Never edit a fixture in place — add a new
one and update the tests that reference it.
