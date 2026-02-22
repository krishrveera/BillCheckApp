# BillCheck

A rule-based, deterministic medical billing verification engine built on FastAPI. BillCheck programmatically audits inpatient and outpatient hospital bills by cross-referencing line-item charges against the CMS Medicare Physician Fee Schedule (queried live via the `data.cms.gov` public API), NCCI Correct Coding Initiative bundling edits, ICD-10-to-CPT clinical plausibility mappings, and FDA-sourced maximum daily drug dosage thresholds. The system produces structured, dollar-quantified discrepancy reports with zero reliance on large language models for the verification logic itself, ensuring full auditability and reproducibility of every flag raised.

## Architecture

```
                   ┌─────────────────┐
                   │   FastAPI App    │
                   │   (main.py)      │
                   └────────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
     ┌────────▼──────┐ ┌───▼────┐ ┌──────▼───────┐
     │  OAuth 2.0    │ │ Static │ │  REST API    │
     │  (auth.py)    │ │   UI   │ │  Endpoints   │
     └───────────────┘ └────────┘ └──────┬───────┘
                                         │
                              ┌──────────▼──────────┐
                              │  Verification        │
                              │  Pipeline            │
                              │  (pipeline/)         │
                              ├──────────────────────┤
                              │  extractor.py        │
                              │  comparator.py       │
                              │  cms_api.py          │
                              │  scorer.py           │
                              └──────────┬───────────┘
                                         │
                       ┌─────────────────┼─────────────────┐
                       │                 │                 │
              ┌────────▼──────┐ ┌────────▼──────┐ ┌───────▼───────┐
              │ CMS Fee       │ │ NCCI Edit     │ │ Drug Dosage   │
              │ Schedule API  │ │ Lookup Table  │ │ Limits Table  │
              │ + Fallback    │ │               │ │               │
              └───────────────┘ └───────────────┘ └───────────────┘
```

## Verification Pipeline

The comparator module executes 7 independent, composable verification engines in sequence. Each engine operates on the structured `PatientBill` model and emits zero or more `VerificationIssue` objects with typed severity levels, CPT/HCPCS code references, and dollar-denominated overcharge estimates.

| Engine | Name | Detection Logic |
|--------|------|-----------------|
| 1 | **Duplicate Charge Detection** | Groups line items by `(cpt_code, date_of_service)` tuples and flags any group with cardinality > 1. Computes overcharge as `charge_amount * (n - 1)`. |
| 2 | **Date-of-Service Validation** | Parses admission and discharge dates, then flags any line item whose `date_of_service` falls outside the `[admission, discharge]` interval. |
| 3 | **Arithmetic Verification** | Computes `sum(charge_amount)` across all line items and compares against the stated `total_billed`. Flags discrepancies above configurable thresholds ($0.01 for warnings, $100 for critical). |
| 4 | **CMS Fee Schedule Benchmarking** | Queries the CMS Medicare Physician & Other Practitioners API (`data.cms.gov`, dataset UUID `6fea9d79-0129-4e4c-b1b8-23cd86a4f435`) for national average payment rates per HCPCS code. Falls back to a static schedule when the API is unreachable. Flags charges at 3x (warning) or 5x (critical) the Medicare rate. Results are cached to disk with a 7-day TTL. |
| 5 | **NCCI Unbundling Detection** | Maintains a lookup table of CMS National Correct Coding Initiative column 1/column 2 edit pairs. For each date of service, checks whether any pair of billed codes constitutes an unbundling violation (i.e., a component code billed separately from its comprehensive code). |
| 6 | **ICD-10 Clinical Plausibility** | Maps ICD-10 diagnosis prefixes to sets of plausible and implausible CPT codes. A procedure is flagged only if it appears in the implausible set for at least one diagnosis and in the plausible set for none. Supports hierarchical prefix matching (full code, then 5-, 4-, and 3-character prefixes). |
| 7 | **Drug Dosage Anomaly Detection** | Aggregates total billing units per HCPCS J-code per calendar day, converts to milligrams using a reference table of per-unit dosages, and compares against FDA-informed maximum daily dose thresholds. Severity tiers: warning (>1x limit), critical (>=2x), critical/dangerously high (>=5x). Reference drugs include morphine, fentanyl, ketorolac, ampicillin, and promethazine. |

## Scoring and Report Generation

The `scorer` module consumes the list of `VerificationIssue` objects and produces a `VerificationReport` containing:

- **Safety Score**: Integer 0-100 computed by deducting 5 points per critical issue, 3 per warning, and 1 per informational finding. Clamped to [0, 100].
- **Letter Grade**: A (>=90), B (>=75), C (>=60), D (>=40), F (<40).
- **Total Flagged Amount**: De-duplicated sum of `potential_overcharge` values, grouped by `line_item_index` (max overcharge per line) to prevent double-counting across engines.
- **Dispute Letter**: Auto-generated formal letter addressed to the facility billing department, itemizing each finding with CPT codes and dollar amounts.
- **Phone Script**: Structured call script for verbal dispute with the billing department.

## Bill Extraction (Vision Pipeline)

For uploaded bill images (PNG, JPEG, WebP, GIF, PDF), the extractor module sends the document to the Anthropic Claude Vision API with a specialized medical billing prompt. The model extracts structured line items (CPT/HCPCS codes, charges, dates, quantities) into the `PatientBill` schema, which then flows through the same deterministic verification pipeline. The LLM is used exclusively for OCR/extraction, never for verification logic.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web Framework | FastAPI with Starlette ASGI |
| Data Validation | Pydantic v2 models with strict typing |
| Authentication | Google OAuth 2.0 via Authlib, session-backed with `itsdangerous` signed cookies |
| External APIs | CMS `data.cms.gov` (Medicare fee data), Anthropic Claude (vision extraction) |
| HTTP Client | `httpx` (async-capable) |
| Server | Uvicorn with hot reload |

## Project Structure

```
BillCheckApp/
  main.py                  FastAPI application, middleware stack, API route handlers
  auth.py                  Google OAuth 2.0 flow (login/callback/logout/session)
  models.py                Pydantic schemas: PatientBill, BillLineItem, VerificationIssue, VerificationReport
  reference_data.py        Static reference: CMS fee schedule fallback, NCCI edits, ICD-10 mappings, drug dosage limits
  run.py                   Uvicorn entry point (localhost:8000, reload enabled)
  requirements.txt         Python dependencies
  pipeline/
    comparator.py          7 deterministic verification engines (core business logic)
    cms_api.py             CMS data.cms.gov API client with disk-based caching (7-day TTL)
    extractor.py           Bill-to-text formatter and Claude Vision extraction pipeline
    scorer.py              Safety scoring algorithm, report builder, dispute letter/phone script generator
  data/
    synthetic_bills.py     3 synthetic patient bills with 16+ seeded billing errors across all 7 engine types
  static/
    index.html             Single-page frontend
```

## Setup

### Prerequisites

- Python 3.11+

### Installation

```bash
git clone https://github.com/sreeram0407/BillCheckApp.git
cd BillCheckApp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
# Required for image/PDF bill extraction via Claude Vision (optional for synthetic data)
ANTHROPIC_API_KEY=your_anthropic_api_key

# Required for Google OAuth 2.0 (omit for unauthenticated dev mode)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
APP_SECRET_KEY=a_cryptographically_random_secret
OAUTH_REDIRECT_URI=http://localhost:8000/auth/callback
```

When OAuth credentials are absent, the application operates in dev mode: all protected endpoints pass through without authentication, returning a synthetic dev user context.

### Running

```bash
python run.py
```

The server binds to `http://localhost:8000` with hot reload enabled.

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/api/patients` | List synthetic patients with summary metadata |
| `GET` | `/api/patients/{id}` | Full bill payload and known error annotations for a patient |
| `GET` | `/api/patients/{id}/bill-text` | Formatted plaintext rendering of a bill |
| `POST` | `/api/verify/{id}` | Execute full 7-engine verification pipeline on a synthetic bill |
| `POST` | `/api/verify-custom` | Verify an arbitrary bill submitted as JSON (`PatientBill` schema) |
| `POST` | `/api/verify-upload` | Upload a bill image/PDF, extract via Claude Vision, then verify |
| `GET` | `/auth/login` | Initiate Google OAuth 2.0 authorization code flow |
| `GET` | `/auth/callback` | OAuth redirect handler (exchanges code for token, creates session) |
| `GET` | `/auth/logout` | Destroy session and redirect to root |
| `GET` | `/auth/me` | Return authenticated user profile (`email`, `name`, `picture`) |
| `GET` | `/auth/status` | OAuth configuration and session status |

## Synthetic Test Data

Three synthetic patient bills are loaded at startup, each seeded with intentional billing errors spanning all 7 engine categories:

| Patient | Diagnosis | Seeded Errors |
|---------|-----------|---------------|
| Maria Garcia | Acute appendicitis (K35.80) | Math error (+$840 inflation), CT unbundling (74176 alongside 74177), duplicate IV hydration (96360), implausible cardiac stress test (93015), post-discharge CMP |
| Robert Thompson | CHF exacerbation (I50.23) | ECG unbundling (93010 alongside 93000), creatinine unbundling (82565 alongside 80053), implausible appendectomy (44970), post-discharge CMP, duplicate echocardiography (93306), morphine dosage anomaly (500 mg vs 100 mg max) |
| Dorothy Chen | Knee osteoarthritis (M17.11) | Math error (+$1,250 inflation), potassium unbundling (84132 alongside 80053), implausible surgical pathology (88305), duplicate morphine (J2270), post-discharge cardiac stress test (93015) |

## CMS Data Integration

The `cms_api` module queries the CMS Medicare Physician & Other Practitioners by Geography and Service dataset (dataset ID `6fea9d79-0129-4e4c-b1b8-23cd86a4f435`) at `data.cms.gov`. It retrieves national-level average Medicare allowed amounts per HCPCS/CPT code, caches responses to disk with a 7-day TTL to minimize API calls, and falls back to the static `CMS_FEE_SCHEDULE_FALLBACK` dictionary in `reference_data.py` for any codes not returned by the API or when the service is unreachable.
