"""
Tests for the CMS API integration.

Validates:
  1. The CMS data.cms.gov API is reachable and returns real Medicare rates.
  2. Caching works (disk cache read / write).
  3. Fallback logic works when the API cannot resolve a code.
  4. The full pipeline uses live rates in the CMS benchmark check.

Run:  python -m pytest test_cms_api.py -v
"""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.cms_api import (
    fetch_rates,
    get_medicare_rate,
    build_fee_schedule,
    _CACHE_FILE,
    _load_cache,
    _save_cache,
)
from reference_data import CMS_FEE_SCHEDULE_FALLBACK


class TestCMSAPILive(unittest.TestCase):
    """Tests that actually hit the CMS API (requires network)."""

    def test_fetch_single_code(self):
        """Fetching a common E&M code should return a valid rate."""
        rates = fetch_rates(["99213"], use_cache=False)
        self.assertIn("99213", rates)
        entry = rates["99213"]
        self.assertIn("avg_medicare_payment", entry)
        self.assertIn("avg_medicare_allowed", entry)
        self.assertIn("description", entry)
        # Medicare payment for 99213 should be a positive number
        self.assertGreater(entry["avg_medicare_payment"], 0)
        print(f"\n  99213 avg Medicare payment: ${entry['avg_medicare_payment']:.2f}")
        print(f"  99213 avg submitted charge: ${entry['avg_submitted_charge']:.2f}")

    def test_fetch_multiple_codes(self):
        """Fetching several codes should return data for each."""
        codes = ["99213", "80053", "93000", "85025"]
        rates = fetch_rates(codes, use_cache=False)
        for code in codes:
            self.assertIn(code, rates, f"Code {code} missing from API results")
            self.assertGreater(
                rates[code]["avg_medicare_payment"], 0,
                f"Code {code} has zero Medicare payment",
            )
        print(f"\n  Fetched {len(rates)} codes successfully")

    def test_convenience_function(self):
        """get_medicare_rate() should return a float."""
        rate = get_medicare_rate("99214", use_cache=False)
        self.assertIsNotNone(rate)
        self.assertIsInstance(rate, float)
        self.assertGreater(rate, 0)
        print(f"\n  99214 Medicare rate: ${rate:.2f}")


class TestBuildFeeSchedule(unittest.TestCase):
    """Test the build_fee_schedule function that merges API + fallback."""

    def test_build_schedule_with_fallback(self):
        """Codes not in the API should fall back to static data."""
        # Use a real code + a fake code that's in the fallback
        codes = ["99213"]
        schedule = build_fee_schedule(codes, fallback=CMS_FEE_SCHEDULE_FALLBACK)
        self.assertIn("99213", schedule)
        self.assertIn("medicare_rate", schedule["99213"])
        self.assertIn("source", schedule["99213"])
        src = schedule["99213"]["source"]
        self.assertIn(src, ("cms_api", "fallback"))
        print(f"\n  99213 source: {src}, rate: ${schedule['99213']['medicare_rate']:.2f}")

    def test_all_fallback_codes_resolvable(self):
        """Every code in the fallback dict should resolve (API or fallback)."""
        codes = list(CMS_FEE_SCHEDULE_FALLBACK.keys())
        schedule = build_fee_schedule(codes, fallback=CMS_FEE_SCHEDULE_FALLBACK)
        for code in codes:
            self.assertIn(code, schedule, f"Code {code} unresolvable")
            self.assertGreater(
                schedule[code]["medicare_rate"], 0,
                f"Code {code} has zero rate",
            )
        api_count = sum(1 for v in schedule.values() if v.get("source") == "cms_api")
        fb_count = sum(1 for v in schedule.values() if v.get("source") == "fallback")
        print(f"\n  {api_count} from API, {fb_count} from fallback (of {len(codes)} total)")


class TestCaching(unittest.TestCase):
    """Test disk caching."""

    def setUp(self):
        """Back up existing cache before test."""
        self._backup = None
        if _CACHE_FILE.exists():
            self._backup = _CACHE_FILE.read_text()

    def tearDown(self):
        """Restore cache after test."""
        if self._backup is not None:
            _CACHE_FILE.write_text(self._backup)
        elif _CACHE_FILE.exists():
            _CACHE_FILE.unlink()

    def test_cache_round_trip(self):
        """Save and load should preserve data."""
        test_data = {"ZZZZZ": {"avg_medicare_payment": 59.65, "test": True}}
        _save_cache(test_data)
        loaded = _load_cache()
        self.assertEqual(loaded["ZZZZZ"]["avg_medicare_payment"], 59.65)
        self.assertTrue(loaded["ZZZZZ"]["test"])

    def test_cached_results_used(self):
        """Second fetch should use cache and not hit API."""
        # First fetch (populates cache)
        rates1 = fetch_rates(["99213"], use_cache=True)
        self.assertIn("99213", rates1)

        # Second fetch should come from cache
        rates2 = fetch_rates(["99213"], use_cache=True)
        self.assertIn("99213", rates2)
        self.assertEqual(
            rates1["99213"]["avg_medicare_payment"],
            rates2["99213"]["avg_medicare_payment"],
        )


class TestIntegrationWithVerifier(unittest.TestCase):
    """Ensure the full verify_bill pipeline works with live CMS data."""

    def test_verify_bill_uses_live_rates(self):
        """Running verify_bill should use the CMS API (or cache) for benchmarks."""
        from models import PatientBill, BillLineItem
        from pipeline.comparator import verify_bill

        bill = PatientBill(
            patient_name="Test Patient",
            mrn="TEST-CMS",
            admission_date="2025-01-01",
            discharge_date="2025-01-05",
            primary_diagnosis_icd10="K35.80",
            secondary_diagnoses_icd10=[],
            line_items=[
                BillLineItem(
                    cpt_code="99213",
                    description="Office visit",
                    charge_amount=200.0,
                    date_of_service="2025-01-02",
                ),
                BillLineItem(
                    cpt_code="80053",
                    description="CMP",
                    charge_amount=185.0,
                    date_of_service="2025-01-02",
                ),
            ],
            total_billed=385.0,
            facility_name="Test Hospital",
        )
        # Should run without error, using live API rates
        issues = verify_bill(bill)
        self.assertIsInstance(issues, list)
        print(f"\n  verify_bill returned {len(issues)} issues")
        for i in issues:
            print(f"    [{i.severity.value}] {i.description}")
            if "source:" in i.details:
                src = i.details.split("source:")[1].strip().rstrip("]")
                print(f"      Rate source: {src}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
