# RiverCast data-viability report (Phase 2 spike)

- **Spike executed:** 2026-08-02 (live, from a development machine; ~20 HTTP requests)
- **Tooling:** `scripts/source_spike.py` (`--live`); offline reproduction: `notebooks/01_source_and_data_quality.ipynb` over committed fixtures
- **Decision: PROCEED** — all gate criteria met (details below)

## 1. Final station UUIDs

Resolved from the stable REST API by exact `shortname` match against the
configured corridor; pinned in `configs/stations.yaml` and `configs/base.yaml`.
River kilometers confirm all inputs are upstream of the target.

| Station | UUID | Gauge no. | Rhine km | Role |
|---|---|---|---|---|
| MAINZ | `a37a9aa3-45e9-4d90-9df6-109f3a28a5af` | 25100100 | 498.27 | input |
| OESTRICH | `665be0fe-5e38-43f6-8b04-02a93bdbeeb4` | 25100300 | 518.08 | input |
| BINGEN | `0309cd61-90c9-470e-99d4-2ee4fb2c5f84` | 25300200 | 528.36 | input |
| KAUB | `1d26e504-7f9e-480a-b52c-5932be6549ab` | 25700100 | 546.23 | **target** |

## 2. Exact source endpoints

| Purpose | Endpoint | Auth | Notes |
|---|---|---|---|
| Station list / metadata | `GET https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations.json?waters=RHEIN` | none | 36 Rhine stations |
| Live measurements (~31-day window) | `GET .../stations/{uuid}/W/measurements.json?start=P31D` | none | 15-min cadence; JSON `{timestamp, value}` with ISO-8601 offsets |
| Current measurement (latency) | `GET .../stations/{uuid}.json?includeTimeseries=true&includeCurrentMeasurement=true` | none | |
| Historical raw data since 2000-01-01 | `POST https://www.pegelonline.wsv.de/gast/historische-zeitreihen/prepare-download` — form fields `uuid`, `parameter="WASSERSTAND ROHDATEN"`, `start`, `end` (ISO-8601), `format=json` | none | Synchronous `application/zip` containing one JSON member + terms of use + series info |
| HyDAS API (`/api/v1`) | — | none | **Beta, recent data only** (verified: empty ≥ 6 months back). Evaluation-only per plan; not used |

Confirmed *not* viable for history: the stable REST API returns HTTP 200 with
zero rows outside its ~31-day window; HyDAS likewise. Long history comes only
from the historical download endpoint above.

## 3. Chosen historical window

**Training bootstrap: 2023-01-01 → present (≈ 3.6 years), all four stations.**
Data exists back to 2000-01-01 (verified: KAUB rows from
`2000-01-01T01:00:00+01:00`), so the window comfortably exceeds the required
two years and can be widened later without renegotiating the source. The
bootstrap download is a one-time Phase 3/4 step archived immutably into
`bronze/`; ongoing collection uses the REST API's 31-day window on the hourly
schedule.

Spike sample windows (committed as fixtures under `data_fixtures/pegelonline/`):

| Window | Stations | Purpose |
|---|---|---|
| last 7 days (of live 31-day fetch) | all 4 | recent cadence/gap/latency analysis |
| 2024-08-01 → 2024-08-08 | all 4 | historical overlap check |
| 2025-03-29 → 2025-03-31 | KAUB | DST spring-forward |
| 2025-10-25 → 2025-10-27 | KAUB | DST fall-back |
| 2000-01-01 → 2000-01-04 | KAUB | earliest-history check |

## 4. Missingness and quality findings

Live 31-day fetch (2026-07-02 → 2026-08-02), gap tolerance 20 min:

| Station | Rows | Cadence (mode) | Gaps > 20 min | Max gap | Duplicates | Conflicts | Range (cm) | Offsets seen |
|---|---|---|---|---|---|---|---|---|
| MAINZ | 2976 | 15 min | 0 | 15 min | 0 | 0 | 122–226 | +02:00 |
| OESTRICH | 2976 | 15 min | 0 | 15 min | 0 | 0 | 49–133 | +02:00 |
| BINGEN | 2976 | 15 min | 0 | 15 min | 0 | 0 | 46–134 | +02:00 |
| KAUB | 2976 | 15 min | 0 | 15 min | 0 | 0 | 25–126 | +02:00 |

- 2976 rows = a complete 31-day 15-minute grid for every station.
- **Source latency:** 7.8–7.9 minutes at spike time (newest value vs. UTC now).
- **Historical overlap (2024-08 week):** coverage fraction 1.0 for all four
  stations on the common grid (673/673 points each).
- **DST:** both 2025 transition windows are gap-free and conflict-free; raw
  timestamps switch offset explicitly (`+01:00` ↔ `+02:00`), so UTC
  normalization is deterministic (spring window: 141 rows; fall: 149 rows —
  exactly the wall-clock-shortened/lengthened grids).
- **Upstream signal (spike question §6):** correlation of a station's current
  6-hour change with KAUB's *future* 6-hour change, on the recent window
  (n = 624): OESTRICH **0.85**, BINGEN **0.68**, MAINZ **0.44**, vs. KAUB's own
  past change **0.17** (the persistence view). Upstream gauges carry
  substantial predictive signal that persistence lacks.

## 5. Data-quality risks

1. **Historical data is unvalidated raw data** ("ungeprüfte Rohdaten") — may
   contain outliers, sensor errors, revisions. Mitigation: Phase 4 value-bounds
   and plausibility checks; never treat bronze as clean.
2. **The 31-day REST window is a hard wall.** An ingestion outage longer than
   31 days loses live-path data permanently (recoverable later only via the
   historical endpoint). Mitigation: hourly scheduled ingestion + staleness
   alarms (Phase 9/12); the wall is why ingestion must be reliable, which is a
   feature for a workshop about exactly that.
3. **The historical endpoint is browser-oriented, not a documented API** (it
   backs a download modal; terms-of-use checkbox is client-side). It may change
   without notice. Mitigation: use it only for the one-time bootstrap and
   fixture refresh, archive results immutably, never put it in the hourly path.
4. **`Aktueller Monat`/CSV variants use legal time (CET/CEST), daily files
   year-round CET** — only the JSON format carries explicit per-row offsets.
   Mitigation: JSON format is mandatory everywhere (enforced in the Phase 3
   adapter).
5. **Value ranges are seasonal.** The spike's July–August range (25–226 cm) is
   low-water; flood levels reach several hundred cm. The Phase 4 plausibility
   bounds in `base.yaml` (−200…1500 cm) must not be tightened to spike-observed
   ranges.
6. **No credentials required — also no SLA.** Free access without registration
   means no availability guarantee. Fixture mode keeps the workshop functional
   during outages (rule 15).

## 6. Spike questions from the plan — answers

| Question | Answer |
|---|---|
| All stations available for the same historical window? | Yes — 100% overlap coverage in the sampled 2024 week; history since 2000 advertised for W raw data |
| Nominal cadence consistently 15 minutes? | Yes — mode 15 min, zero deviation in 31 days × 4 stations and all historical samples |
| Parseable directly as JSON/CSV? | Yes — JSON with ISO-8601 offset timestamps on both live and historical paths |
| Timestamps ambiguous around DST? | No — explicit offsets make both transitions deterministic (verified on 2025 windows) |
| Station metadata changes or long outages? | None observed in samples; UUIDs are documented as immutable; long-outage risk handled by fail-closed freshness checks |
| Does upstream data improve on 6-h persistence? | Strong evidence yes — upstream delta correlations 0.44–0.85 vs. 0.17 for persistence-style information |
| Is KAUB still the right target? | Yes — mid-Rhine narrows, three upstream inputs with 20–48 km lead distance, clean data, and the corridor is configurable if this changes |

## 7. Gate criteria

- ≥ 2 years of usable overlapping history can be assembled: **yes** (since 2000; chosen bootstrap 2023 → present).
- Target has sufficient data for 6 h / 12 h labels: **yes** (complete 15-min grid resamples cleanly to hourly).
- Timestamps normalize deterministically: **yes** (explicit ISO-8601 offsets; DST verified both directions).
- Collectable without credentials: **yes** (all endpoints anonymous).

**Decision: PROCEED to Phase 3** (source adapters and immutable raw storage)
with the corridor unchanged. No configuration changes required beyond pinning
the UUIDs (done in this phase).
