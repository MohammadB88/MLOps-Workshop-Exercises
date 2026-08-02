# ADR 0001 — RiverCast scope: gauge-only MVP for KAUB at 6 h and 12 h

- **Status:** accepted
- **Date:** 2026-08-02
- **Deciders:** RiverCast maintainers
- **Related:** [ADR 0002](0002-data-versioning.md), [ADR 0003](0003-pipeline-boundaries.md), `PLAN.md` §1–2

## Context

RiverCast is the Level-1 MLOps capstone for this workshop: a continuously running
loop that ingests river-gauge data, forecasts future water levels, evaluates
predictions when actual measurements arrive, retrains on a schedule, and promotes
only validated candidates. The hard part is not training a regressor — it is a
trustworthy time-series loop without timestamp/DST errors, data leakage, silent
gap filling, irreproducible datasets, fake "continuous training", or deployment
of unvalidated candidates. Every additional data source or model family multiplies
those risks before the loop itself is proven.

## Decision

1. **Prediction task.** Forecast the water level (`W`) at the **KAUB** gauge on
   the Rhine, **6 hours** and **12 hours** ahead, on an **hourly canonical time
   grid**. One registered model per horizon.
2. **Input stations.** A configurable Rhine corridor: MAINZ, OESTRICH, BINGEN,
   KAUB. Stations are resolved to and stored by immutable PEGELONLINE UUID, never
   by display name. The list lives in configuration (`configs/base.yaml`) so it
   can change after the Phase 2 data-viability spike without code changes.
3. **Data source.** PEGELONLINE stable REST API only (gauge water level). No DWD
   weather observations, no ICON forecast grids in the MVP — those are extension
   phases gated on the gauge-only loop working end to end.
4. **Features.** Only information available at forecast issue time `t`: current
   and lagged levels, rolling changes/statistics, upstream gauge values, calendar
   encodings, and missingness indicators.
5. **Models.** Persistence baseline (`ŷ(t+h) = level(t)`), linear/ridge
   regression, and scikit-learn `HistGradientBoostingRegressor` as the first
   serious candidate. No deep learning in the MVP.
6. **Educational system.** RiverCast is a teaching artifact. PEGELONLINE water
   level is relative to the local gauge zero, not river depth, and RiverCast
   forecasts must never be used for real-world decisions.

## Non-goals

Flood warnings or any safety-critical use; nationwide forecasting; deep learning
(LSTM/transformer); Kafka; Feast; Spark; Airflow; DWD ICON data in the MVP;
automatic deployment without validation.

## Consequences

- The MVP stays small enough that each phase can be verified against acceptance
  criteria before the next begins (`PLAN.md`, "Recommended implementation order").
- Horizons, stations, and thresholds are configuration, so the Phase 2 spike can
  change the corridor or even the target without reworking code.
- Extensions (DWD observations, ICON-D2, multi-station, canary rollout) attach
  later without invalidating these decisions; the gauge-only model remains the
  required fallback.
