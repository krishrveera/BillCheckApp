# BillCheck

Deterministic medical bill verification system. BillCheck analyzes hospital bills against CMS Medicare fee schedules, NCCI bundling edits, clinical plausibility rules, and drug dosage safety limits to flag billing errors, overcharges, and anomalies.

No LLM is used for verification. Every flag maps to a specific rule, a specific CPT/HCPCS code, and a specific dollar amount.

## Verification Engines

BillCheck runs 7 independent verification engines against each bill:

1. **Duplicate Charge Detection** - Flags the same CPT code billed more than once on the same date of service.
2. **Date Validation** - Flags charges with a date of service outside the admission-to-discharge window.
3. **Math Verification** - Checks that the billed total matches the sum of individual line items.
4. **CMS Benchmark Comparison** - Compares each charge against Medicare fee schedule rates (live CMS API with static fallback). Flags charges exceeding 3x or 5x the Medicare rate.
5. **NCCI Unbundling Detection** - Detects pairs of codes that should be bundled together per CMS National Correct Coding Initiative edits.
6. **Clinical Plausibility** - Checks whether billed procedures are clinically plausible given the patient's ICD-10 diagnoses.
7. **Dosage Anomaly Detection** - Flags when total daily medication dosage (by HCPCS J-code) exceeds clinically accepted maximum daily limits.

## Project Structure

```
BillCheckApp/
  main.py                  FastAPI application and API routes
  auth.py                  Google OAuth 2.0 authentication
  models.py                Pydantic models (bill, issues, report)
  reference_data.py        CMS fee schedule, NCCI edits, ICD-10 mappings, drug dosage limits
  run.py                   Uvicorn entry point
  requirements.txt         Python dependencies
  pipeline/
    comparator.py          7 deterministic verification engines
    cms_api.py             Live CMS Medicare fee schedule API client
    extractor.py           Bill text formatting and image extraction (Claude Vision)
    scorer.py              Safety scoring, report generation, dispute letter and phone script
  data/
    synthetic_bills.py     3 synthetic patient bills with intentional billing errors
  static/
    index.html             Frontend UI
```

## Setup

### Prerequisites

- Python 3.11+
- A virtual environment is recommended

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

```
# Required for image upload extraction (optional otherwise)
ANTHROPIC_API_KEY=your_anthropic_api_key

# Required for Google OAuth (optional in dev mode)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
APP_SECRET_KEY=a_random_secret_string
OAUTH_REDIRECT_URI=http://localhost:8000/auth/callback
```

When Google OAuth credentials are not set, the app runs in dev mode and allows all requests without authentication.

### Running

```bash
python run.py
```

The server starts at `http://localhost:8000`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/patients` | List all synthetic patients |
| GET | `/api/patients/{id}` | Get full bill details for a patient |
| GET | `/api/patients/{id}/bill-text` | Get formatted text version of a bill |
| POST | `/api/verify/{id}` | Run verification on a synthetic bill |
| POST | `/api/verify-custom` | Verify a custom bill submitted as JSON |
| POST | `/api/verify-upload` | Extract bill from an uploaded image and verify |
| GET | `/auth/login` | Redirect to Google OAuth consent screen |
| GET | `/auth/callback` | OAuth callback handler |
| GET | `/auth/logout` | Clear session |
| GET | `/auth/me` | Get current user info |
| GET | `/auth/status` | Check OAuth config and login status |

## Synthetic Test Data

The app ships with 3 synthetic patient bills, each containing intentional billing errors for demonstration:

- **Patient 1 (Maria Garcia)** - Appendectomy with math error, unbundling, duplicate charge, implausible procedure, and post-discharge billing.
- **Patient 2 (Robert Thompson)** - CHF exacerbation with unbundling violations, implausible procedure, post-discharge billing, duplicate charge, and a dosage anomaly (500 mg morphine on a single day vs 100 mg safe limit).
- **Patient 3 (Dorothy Chen)** - Total knee replacement with math error, unbundling, implausible procedure, duplicate charge, and post-discharge billing.

## Verification Report Output

Each verification run produces:

- A list of flagged issues with severity (critical/warning/info), CPT code, description, and potential overcharge amount
- A safety score (0-100) and letter grade (A through F)
- A human-readable summary
- A generated formal dispute letter
- A generated phone script for calling the billing department

## CMS API Integration

BillCheck queries the CMS Medicare Physician and Other Practitioners dataset at `data.cms.gov` for real Medicare payment rates. Results are cached locally for 7 days. When the API is unreachable, a static fallback fee schedule is used.
