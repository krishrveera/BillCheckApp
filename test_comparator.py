"""
Unit tests for all 6 deterministic verification engines + integration tests.
No API key needed — all tests are deterministic.

Run: python test_comparator.py
"""

import sys
import os
import unittest

from models import PatientBill, BillLineItem, IssueSeverity, IssueType
from pipeline.comparator import (
    verify_bill,
    _check_duplicates,
    _check_dates,
    _check_math,
    _check_cms_benchmarks,
    _check_unbundling,
    _check_plausibility,
)
from data.synthetic_bills import get_synthetic_bills


def _make_bill(**kwargs) -> PatientBill:
    """Helper to create a minimal bill for testing."""
    defaults = {
        "patient_name": "Test Patient",
        "mrn": "TEST-001",
        "admission_date": "2025-01-01",
        "discharge_date": "2025-01-05",
        "primary_diagnosis_icd10": "K35.80",
        "secondary_diagnoses_icd10": [],
        "line_items": [],
        "total_billed": 0.0,
        "facility_name": "Test Hospital",
    }
    defaults.update(kwargs)
    return PatientBill(**defaults)


class TestDuplicateDetection(unittest.TestCase):
    def test_duplicate_found(self):
        """Same CPT twice on same date should be flagged."""
        bill = _make_bill(
            line_items=[
                BillLineItem(cpt_code="96360", description="IV hydration", charge_amount=380.0, date_of_service="2025-01-01"),
                BillLineItem(cpt_code="96360", description="IV hydration", charge_amount=380.0, date_of_service="2025-01-01"),
            ],
            total_billed=760.0,
        )
        issues = _check_duplicates(bill)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, IssueType.duplicate_charge)
        self.assertEqual(issues[0].severity, IssueSeverity.critical)
        self.assertEqual(issues[0].potential_overcharge, 380.0)

    def test_same_cpt_different_dates_ok(self):
        """Same CPT on different dates should NOT be flagged."""
        bill = _make_bill(
            line_items=[
                BillLineItem(cpt_code="80053", description="CMP", charge_amount=185.0, date_of_service="2025-01-01"),
                BillLineItem(cpt_code="80053", description="CMP", charge_amount=185.0, date_of_service="2025-01-02"),
            ],
            total_billed=370.0,
        )
        issues = _check_duplicates(bill)
        self.assertEqual(len(issues), 0)


class TestDateValidation(unittest.TestCase):
    def test_charges_outside_stay(self):
        """Charges before admission and after discharge should be flagged."""
        bill = _make_bill(
            admission_date="2025-01-02",
            discharge_date="2025-01-04",
            line_items=[
                BillLineItem(cpt_code="80053", description="CMP", charge_amount=185.0, date_of_service="2025-01-01"),  # before
                BillLineItem(cpt_code="85025", description="CBC", charge_amount=120.0, date_of_service="2025-01-03"),  # during - OK
                BillLineItem(cpt_code="80053", description="CMP", charge_amount=185.0, date_of_service="2025-01-05"),  # after
            ],
            total_billed=490.0,
        )
        issues = _check_dates(bill)
        self.assertEqual(len(issues), 2)
        self.assertTrue(all(i.issue_type == IssueType.date_outside_stay for i in issues))
        self.assertTrue(all(i.severity == IssueSeverity.critical for i in issues))

    def test_charges_within_stay_ok(self):
        """Charges within admission-discharge window should not be flagged."""
        bill = _make_bill(
            admission_date="2025-01-01",
            discharge_date="2025-01-05",
            line_items=[
                BillLineItem(cpt_code="80053", description="CMP", charge_amount=185.0, date_of_service="2025-01-01"),
                BillLineItem(cpt_code="80053", description="CMP", charge_amount=185.0, date_of_service="2025-01-03"),
                BillLineItem(cpt_code="80053", description="CMP", charge_amount=185.0, date_of_service="2025-01-05"),
            ],
            total_billed=555.0,
        )
        issues = _check_dates(bill)
        self.assertEqual(len(issues), 0)


class TestMathValidation(unittest.TestCase):
    def test_math_error_detected(self):
        """Total that doesn't match sum should be flagged."""
        bill = _make_bill(
            line_items=[
                BillLineItem(cpt_code="99213", description="Office visit", charge_amount=200.0, date_of_service="2025-01-01"),
                BillLineItem(cpt_code="85025", description="CBC", charge_amount=120.0, date_of_service="2025-01-01"),
            ],
            total_billed=1200.0,  # actual sum is 320
        )
        issues = _check_math(bill)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, IssueType.math_error)
        self.assertEqual(issues[0].severity, IssueSeverity.critical)
        self.assertEqual(issues[0].potential_overcharge, 880.0)

    def test_correct_math_ok(self):
        """Correct total should not be flagged."""
        bill = _make_bill(
            line_items=[
                BillLineItem(cpt_code="99213", description="Office visit", charge_amount=200.0, date_of_service="2025-01-01"),
                BillLineItem(cpt_code="85025", description="CBC", charge_amount=120.0, date_of_service="2025-01-01"),
            ],
            total_billed=320.0,
        )
        issues = _check_math(bill)
        self.assertEqual(len(issues), 0)


class TestCMSBenchmark(unittest.TestCase):
    def test_extreme_overcharge_flagged(self):
        """ECG at $310 vs Medicare $17 (18.2x) should be flagged."""
        bill = _make_bill(
            line_items=[
                BillLineItem(cpt_code="93000", description="ECG complete", charge_amount=310.0, date_of_service="2025-01-01"),
            ],
            total_billed=310.0,
        )
        issues = _check_cms_benchmarks(bill)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, IssueType.cms_overcharge)

    def test_reasonable_charge_ok(self):
        """Charge within normal range should not be flagged."""
        bill = _make_bill(
            line_items=[
                BillLineItem(cpt_code="99213", description="Office visit", charge_amount=200.0, date_of_service="2025-01-01"),
            ],
            total_billed=200.0,
        )
        issues = _check_cms_benchmarks(bill)
        self.assertEqual(len(issues), 0)


class TestUnbundling(unittest.TestCase):
    def test_unbundling_detected(self):
        """ECG complete + ECG interpretation on same day should be flagged."""
        bill = _make_bill(
            line_items=[
                BillLineItem(cpt_code="93000", description="ECG complete", charge_amount=310.0, date_of_service="2025-01-01"),
                BillLineItem(cpt_code="93010", description="ECG interpretation", charge_amount=145.0, date_of_service="2025-01-01"),
            ],
            total_billed=455.0,
        )
        issues = _check_unbundling(bill)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, IssueType.unbundling)
        self.assertEqual(issues[0].severity, IssueSeverity.critical)
        self.assertEqual(issues[0].cpt_code, "93010")

    def test_unbundled_codes_different_dates_ok(self):
        """Same codes on different dates should not be flagged for unbundling."""
        bill = _make_bill(
            line_items=[
                BillLineItem(cpt_code="93000", description="ECG complete", charge_amount=310.0, date_of_service="2025-01-01"),
                BillLineItem(cpt_code="93010", description="ECG interpretation", charge_amount=145.0, date_of_service="2025-01-02"),
            ],
            total_billed=455.0,
        )
        issues = _check_unbundling(bill)
        self.assertEqual(len(issues), 0)


class TestPlausibility(unittest.TestCase):
    def test_implausible_procedure_flagged(self):
        """Cardiac stress test for appendicitis should be flagged."""
        bill = _make_bill(
            primary_diagnosis_icd10="K35.80",
            line_items=[
                BillLineItem(cpt_code="93015", description="Cardiac stress test", charge_amount=1450.0, date_of_service="2025-01-01"),
            ],
            total_billed=1450.0,
        )
        issues = _check_plausibility(bill)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, IssueType.implausible_procedure)
        self.assertEqual(issues[0].cpt_code, "93015")

    def test_plausible_procedure_ok(self):
        """Appendectomy for appendicitis should not be flagged."""
        bill = _make_bill(
            primary_diagnosis_icd10="K35.80",
            line_items=[
                BillLineItem(cpt_code="44970", description="Laparoscopic appendectomy", charge_amount=18500.0, date_of_service="2025-01-01"),
            ],
            total_billed=18500.0,
        )
        issues = _check_plausibility(bill)
        self.assertEqual(len(issues), 0)

    def test_secondary_diagnosis_makes_plausible(self):
        """A procedure plausible for a secondary diagnosis should not be flagged."""
        bill = _make_bill(
            primary_diagnosis_icd10="M17.11",  # knee OA — cardiac stress implausible
            secondary_diagnoses_icd10=["I50.23"],  # heart failure — cardiac stress plausible
            line_items=[
                BillLineItem(cpt_code="93015", description="Cardiac stress test", charge_amount=1450.0, date_of_service="2025-01-01"),
            ],
            total_billed=1450.0,
        )
        issues = _check_plausibility(bill)
        self.assertEqual(len(issues), 0)


class TestIntegration(unittest.TestCase):
    """Integration tests: run full verification on each synthetic patient."""

    def setUp(self):
        self.patients = {p["id"]: p for p in get_synthetic_bills()}

    def test_patient_1_maria_garcia(self):
        """Maria Garcia (appendectomy) should have at least 3 issues."""
        bill = self.patients["patient-1"]["bill"]
        issues = verify_bill(bill)
        self.assertGreaterEqual(len(issues), 3)
        # Check specific issue types are found
        issue_types = {i.issue_type for i in issues}
        self.assertIn(IssueType.math_error, issue_types)
        self.assertIn(IssueType.duplicate_charge, issue_types)
        self.assertIn(IssueType.unbundling, issue_types)

    def test_patient_2_robert_thompson(self):
        """Robert Thompson (CHF) should have at least 3 issues."""
        bill = self.patients["patient-2"]["bill"]
        issues = verify_bill(bill)
        self.assertGreaterEqual(len(issues), 3)
        issue_types = {i.issue_type for i in issues}
        self.assertIn(IssueType.unbundling, issue_types)
        self.assertIn(IssueType.duplicate_charge, issue_types)

    def test_patient_3_dorothy_chen(self):
        """Dorothy Chen (knee replacement) should have at least 3 issues."""
        bill = self.patients["patient-3"]["bill"]
        issues = verify_bill(bill)
        self.assertGreaterEqual(len(issues), 3)
        issue_types = {i.issue_type for i in issues}
        self.assertIn(IssueType.math_error, issue_types)
        self.assertIn(IssueType.duplicate_charge, issue_types)

    def test_all_patients_score_below_80(self):
        """All synthetic patients should have safety score < 80 (they have errors)."""
        from pipeline.scorer import calculate_safety_score
        for pid, data in self.patients.items():
            issues = verify_bill(data["bill"])
            score, grade = calculate_safety_score(issues)
            self.assertLess(score, 80, f"Patient {pid} score should be < 80, got {score}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
