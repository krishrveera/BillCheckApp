"""
THE CORE — 8 Deterministic Verification Engines

NO LLM CALLS. Pure deterministic logic. This is the differentiator.
Every flag maps to a specific rule, a specific CPT code, and a specific dollar amount.
The verification CANNOT hallucinate because it is not an AI.
"""

from datetime import datetime
from collections import defaultdict
from models import PatientBill, VerificationIssue, IssueSeverity, IssueType
from reference_data import (
    CMS_FEE_SCHEDULE,
    CMS_FEE_SCHEDULE_FALLBACK,
    NCCI_LOOKUP,
    ICD10_PLAUSIBLE_CPTS,
    CMS_OVERCHARGE_MULTIPLIER,
    CMS_SEVERE_OVERCHARGE_MULTIPLIER,
    DRUG_DOSAGE_LIMITS,
    MAX_PROCEDURES_PER_DAY,
    PROCEDURE_DURATION_MINUTES,
    MUTUALLY_EXCLUSIVE_PROCEDURES,
)
from pipeline.cms_api import build_fee_schedule

import logging

logger = logging.getLogger(__name__)


def _build_live_fee_schedule(bill: PatientBill) -> dict[str, dict]:
    """
    Build a fee schedule for every CPT code on this bill.

    1. Try the CMS data.cms.gov API (cached on disk for 7 days).
    2. Fall back to the hardcoded CMS_FEE_SCHEDULE_FALLBACK for any
       code not returned by the API.
    """
    codes = list({item.cpt_code for item in bill.line_items if item.cpt_code and item.cpt_code.strip()})
    try:
        schedule = build_fee_schedule(
            codes, fallback=CMS_FEE_SCHEDULE_FALLBACK, use_cache=True
        )
        api_count = sum(1 for v in schedule.values() if v.get("source") == "cms_api")
        fb_count = sum(1 for v in schedule.values() if v.get("source") == "fallback")
        logger.info(
            "Fee schedule: %d codes from CMS API, %d from fallback",
            api_count, fb_count,
        )
    except Exception:
        logger.warning("CMS API unavailable — using fallback fee schedule")
        schedule = {
            c: {**CMS_FEE_SCHEDULE_FALLBACK[c], "source": "fallback"}
            for c in codes
            if c in CMS_FEE_SCHEDULE_FALLBACK
        }
    return schedule


def verify_bill(bill: PatientBill) -> list[VerificationIssue]:
    """Run all 8 deterministic verification engines against a bill."""
    fee_schedule = _build_live_fee_schedule(bill)
    issues = []
    issues.extend(_check_duplicates(bill))
    issues.extend(_check_dates(bill))
    issues.extend(_check_math(bill))
    issues.extend(_check_cms_benchmarks(bill, fee_schedule))
    issues.extend(_check_unbundling(bill))
    issues.extend(_check_plausibility(bill))
    issues.extend(_check_dosage_anomalies(bill))
    issues.extend(_check_phantom_billing(bill))
    return issues


def _check_duplicates(bill: PatientBill) -> list[VerificationIssue]:
    """Engine 1: Detect duplicate charges — same CPT code on same date."""
    issues = []
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)

    for idx, item in enumerate(bill.line_items):
        # Skip items with no CPT/HCPCS code (e.g., hospital internal codes only)
        if not item.cpt_code or item.cpt_code.strip() == "":
            continue
        key = (item.cpt_code, item.date_of_service)
        groups[key].append(idx)

    for (cpt, date), indices in groups.items():
        if len(indices) > 1:
            item = bill.line_items[indices[0]]
            overcharge = item.charge_amount * (len(indices) - 1)
            issues.append(VerificationIssue(
                issue_type=IssueType.duplicate_charge,
                severity=IssueSeverity.critical,
                cpt_code=cpt,
                description=f"Duplicate charge: {item.description}",
                details=f"{cpt} ({item.description}) charged {len(indices)} times on {date}. "
                        f"Each charge: ${item.charge_amount:,.2f}",
                potential_overcharge=overcharge,
                line_item_index=indices[1],
            ))

    return issues


def _check_dates(bill: PatientBill) -> list[VerificationIssue]:
    """Engine 2: Flag charges outside admission-discharge window."""
    issues = []
    try:
        admission = datetime.strptime(bill.admission_date, "%Y-%m-%d").date()
        discharge = datetime.strptime(bill.discharge_date, "%Y-%m-%d").date()
    except ValueError:
        return issues

    for idx, item in enumerate(bill.line_items):
        try:
            service_date = datetime.strptime(item.date_of_service, "%Y-%m-%d").date()
        except ValueError:
            continue

        if service_date < admission:
            days_before = (admission - service_date).days
            issues.append(VerificationIssue(
                issue_type=IssueType.date_outside_stay,
                severity=IssueSeverity.critical,
                cpt_code=item.cpt_code,
                description=f"Charge before admission: {item.description}",
                details=f"{item.cpt_code} ({item.description}) billed on {item.date_of_service}, "
                        f"which is {days_before} day(s) BEFORE admission ({bill.admission_date})",
                potential_overcharge=item.charge_amount * item.quantity,
                line_item_index=idx,
            ))
        elif service_date > discharge:
            days_after = (service_date - discharge).days
            issues.append(VerificationIssue(
                issue_type=IssueType.date_outside_stay,
                severity=IssueSeverity.critical,
                cpt_code=item.cpt_code,
                description=f"Charge after discharge: {item.description}",
                details=f"{item.cpt_code} ({item.description}) billed on {item.date_of_service}, "
                        f"which is {days_after} day(s) AFTER discharge ({bill.discharge_date})",
                potential_overcharge=item.charge_amount * item.quantity,
                line_item_index=idx,
            ))

    return issues


def _check_math(bill: PatientBill) -> list[VerificationIssue]:
    """Engine 3: Verify total matches sum of line items."""
    issues = []
    # charge_amount is the unit price; multiply by quantity for each line total
    computed_sum = sum(item.charge_amount * item.quantity for item in bill.line_items)
    discrepancy = bill.total_billed - computed_sum

    abs_disc = abs(discrepancy)
    disc_label = (
        f"Overcharged by ${abs_disc:,.2f}" if discrepancy > 0
        else f"Undercharged by ${abs_disc:,.2f} (line items exceed stated total)"
    )

    if abs_disc > 100:
        issues.append(VerificationIssue(
            issue_type=IssueType.math_error,
            severity=IssueSeverity.critical,
            cpt_code="N/A",
            description="Math error: total does not match line items",
            details=f"Billed total: ${bill.total_billed:,.2f}. "
                    f"Sum of line items: ${computed_sum:,.2f}. "
                    f"{disc_label}",
            potential_overcharge=abs_disc,
        ))
    elif abs_disc > 0.01:
        issues.append(VerificationIssue(
            issue_type=IssueType.math_error,
            severity=IssueSeverity.warning,
            cpt_code="N/A",
            description="Minor math discrepancy in total",
            details=f"Billed total: ${bill.total_billed:,.2f}. "
                    f"Sum of line items: ${computed_sum:,.2f}. "
                    f"{disc_label}",
            potential_overcharge=abs_disc,
        ))

    return issues


def _check_cms_benchmarks(
    bill: PatientBill,
    fee_schedule: dict[str, dict] | None = None,
) -> list[VerificationIssue]:
    """Engine 4: Compare charges against CMS Medicare fee schedule (live API + fallback)."""
    issues = []
    schedule = fee_schedule or CMS_FEE_SCHEDULE

    for idx, item in enumerate(bill.line_items):
        # Skip items with no CPT/HCPCS code
        if not item.cpt_code or item.cpt_code.strip() == "":
            continue
        if item.cpt_code not in schedule:
            # Let the user know this code couldn't be checked
            code = item.cpt_code
            if code.startswith("S") or code.startswith("T") or code.startswith("C"):
                reason = (
                    f"{code} is a private-payer code (not in the Medicare fee schedule). "
                    f"No Medicare benchmark is available for comparison."
                )
            else:
                reason = (
                    f"{code} was not found in the CMS Medicare fee schedule or fallback data. "
                    f"No benchmark available for comparison."
                )
            issues.append(VerificationIssue(
                issue_type=IssueType.cms_overcharge,
                severity=IssueSeverity.info,
                cpt_code=code,
                description=f"No Medicare rate available: {item.description}",
                details=reason,
                potential_overcharge=0,
                line_item_index=idx,
            ))
            continue

        entry = schedule[item.cpt_code]
        medicare_rate = entry["medicare_rate"]
        source_tag = "CMS API" if entry.get("source") == "cms_api" else "fallback"
        unit_charge = item.charge_amount  # charge per unit
        ratio = unit_charge / medicare_rate if medicare_rate > 0 else 0

        if ratio >= CMS_SEVERE_OVERCHARGE_MULTIPLIER:
            issues.append(VerificationIssue(
                issue_type=IssueType.cms_overcharge,
                severity=IssueSeverity.critical,
                cpt_code=item.cpt_code,
                description=f"Severe overcharge: {item.description}",
                details=f"{item.cpt_code} charged at ${unit_charge:,.2f} vs Medicare rate "
                        f"${medicare_rate:,.2f} ({ratio:.1f}x markup) [source: {source_tag}]",
                potential_overcharge=unit_charge - medicare_rate,
                line_item_index=idx,
            ))
        elif ratio >= CMS_OVERCHARGE_MULTIPLIER:
            issues.append(VerificationIssue(
                issue_type=IssueType.cms_overcharge,
                severity=IssueSeverity.warning,
                cpt_code=item.cpt_code,
                description=f"Significant overcharge: {item.description}",
                details=f"{item.cpt_code} charged at ${unit_charge:,.2f} vs Medicare rate "
                        f"${medicare_rate:,.2f} ({ratio:.1f}x markup) [source: {source_tag}]",
                potential_overcharge=unit_charge - medicare_rate,
                line_item_index=idx,
            ))

    return issues


def _check_unbundling(bill: PatientBill) -> list[VerificationIssue]:
    """Engine 5: Detect NCCI unbundling violations — codes that should be bundled together."""
    issues = []
    flagged: set[tuple[str, str, str]] = set()

    # Build per-date code sets with their indices (skip items without CPT codes)
    date_codes: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for idx, item in enumerate(bill.line_items):
        if not item.cpt_code or item.cpt_code.strip() == "":
            continue
        date_codes[item.date_of_service][item.cpt_code].append(idx)

    for date, codes in date_codes.items():
        for col1_code in codes:
            if col1_code not in NCCI_LOOKUP:
                continue
            for col2_code, reason in NCCI_LOOKUP[col1_code]:
                if col2_code in codes:
                    flag_key = (date, col1_code, col2_code)
                    if flag_key in flagged:
                        continue
                    flagged.add(flag_key)

                    col2_idx = codes[col2_code][0]
                    col2_item = bill.line_items[col2_idx]
                    issues.append(VerificationIssue(
                        issue_type=IssueType.unbundling,
                        severity=IssueSeverity.critical,
                        cpt_code=col2_code,
                        description=f"Unbundling: {col2_item.description}",
                        details=f"{reason} — Both billed on {date}. "
                                f"{col2_code} (${col2_item.charge_amount * col2_item.quantity:,.2f}) should not be billed separately.",
                        potential_overcharge=col2_item.charge_amount * col2_item.quantity,
                        line_item_index=col2_idx,
                    ))

    return issues


def _check_plausibility(bill: PatientBill) -> list[VerificationIssue]:
    """Engine 6: Check if procedures are plausible given diagnoses."""
    issues = []

    # Collect all ICD-10 codes
    all_icd = [bill.primary_diagnosis_icd10] + bill.secondary_diagnoses_icd10

    # Gather plausible and implausible sets across ALL diagnoses
    plausible_codes: set[str] = set()
    implausible_codes: set[str] = set()

    for icd in all_icd:
        # Try prefix matching: full code, then progressively shorter
        matched = False
        for prefix_len in [len(icd), 5, 4, 3]:
            prefix = icd[:prefix_len]
            if prefix in ICD10_PLAUSIBLE_CPTS:
                mapping = ICD10_PLAUSIBLE_CPTS[prefix]
                plausible_codes.update(mapping.get("plausible", set()))
                implausible_codes.update(mapping.get("implausible", set()))
                matched = True
                break

    # A procedure plausible for ANY diagnosis is OK
    truly_implausible = implausible_codes - plausible_codes

    for idx, item in enumerate(bill.line_items):
        if not item.cpt_code or item.cpt_code.strip() == "":
            continue
        if item.cpt_code in truly_implausible:
            # Find which diagnosis makes it implausible
            diagnosis_desc = ""
            for icd in all_icd:
                for prefix_len in [len(icd), 5, 4, 3]:
                    prefix = icd[:prefix_len]
                    if prefix in ICD10_PLAUSIBLE_CPTS:
                        if item.cpt_code in ICD10_PLAUSIBLE_CPTS[prefix].get("implausible", set()):
                            diagnosis_desc = f"{icd} ({ICD10_PLAUSIBLE_CPTS[prefix]['description']})"
                        break

            issues.append(VerificationIssue(
                issue_type=IssueType.implausible_procedure,
                severity=IssueSeverity.warning,
                cpt_code=item.cpt_code,
                description=f"Implausible procedure: {item.description}",
                details=f"{item.cpt_code} ({item.description}) is not clinically plausible "
                        f"for diagnosis {diagnosis_desc}",
                potential_overcharge=item.charge_amount * item.quantity,
                line_item_index=idx,
            ))

    return issues


def _check_dosage_anomalies(bill: PatientBill) -> list[VerificationIssue]:
    """Engine 7: Flag abnormally high medication dosages.

    For each calendar day, sum the total mg billed per drug (J-code) and
    compare against the clinically accepted maximum daily dose from
    DRUG_DOSAGE_LIMITS.  Also flag any single line item whose quantity alone
    exceeds the daily limit.
    """
    issues = []

    # Accumulate total units per drug per date
    daily_usage: dict[str, dict[str, list[tuple[int, int]]]] = defaultdict(
        lambda: defaultdict(list)
    )  # date -> jcode -> [(line_idx, qty), ...]

    for idx, item in enumerate(bill.line_items):
        code = (item.cpt_code or "").strip().upper()
        if code in DRUG_DOSAGE_LIMITS:
            daily_usage[item.date_of_service][code].append((idx, item.quantity))

    for date, drugs in daily_usage.items():
        for jcode, entries in drugs.items():
            ref = DRUG_DOSAGE_LIMITS[jcode]
            total_units = sum(qty for _, qty in entries)
            total_mg = total_units * ref["unit_mg"]
            max_mg = ref["max_daily_mg"]

            if total_mg > max_mg:
                ratio = total_mg / max_mg
                first_idx = entries[0][0]
                first_item = bill.line_items[first_idx]

                if ratio >= 5.0:
                    severity = IssueSeverity.critical
                    label = "Dangerously high"
                elif ratio >= 2.0:
                    severity = IssueSeverity.critical
                    label = "Excessive"
                else:
                    severity = IssueSeverity.warning
                    label = "Elevated"

                issues.append(VerificationIssue(
                    issue_type=IssueType.dosage_anomaly,
                    severity=severity,
                    cpt_code=jcode,
                    description=f"{label} dosage: {ref['drug']}",
                    details=(
                        f"{ref['drug']} ({jcode}) billed {total_units} unit(s) on {date}, "
                        f"totaling {total_mg:,.1f} mg. "
                        f"Maximum recommended daily dose is {max_mg:,.1f} mg "
                        f"({ratio:.1f}x the safe limit)."
                    ),
                    potential_overcharge=first_item.charge_amount * max(total_units - int(max_mg / ref["unit_mg"]), 0),
                    line_item_index=first_idx,
                ))

    return issues


def _check_phantom_billing(bill: PatientBill) -> list[VerificationIssue]:
    """Engine 8: Detect phantom billing red flags.

    Three checks:
    1. Excessive service density — too many distinct procedures in one day
    2. Mutually exclusive procedures — conflicting services on the same day
    3. Time-overlap detection — major surgeries that can't physically overlap
    """
    issues = []

    # Build per-date code sets
    date_codes: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for idx, item in enumerate(bill.line_items):
        if not item.cpt_code or item.cpt_code.strip() == "":
            continue
        date_codes[item.date_of_service][item.cpt_code].append(idx)

    for date, codes in date_codes.items():
        # --- Check 1: Excessive service density ---
        distinct_count = len(codes)
        if distinct_count > MAX_PROCEDURES_PER_DAY:
            issues.append(VerificationIssue(
                issue_type=IssueType.phantom_billing,
                severity=IssueSeverity.critical,
                cpt_code="N/A",
                description=f"Suspicious service density on {date}",
                details=f"{distinct_count} distinct procedure codes billed on {date}. "
                        f"Maximum expected for a single patient is {MAX_PROCEDURES_PER_DAY}. "
                        f"This may indicate phantom charges for services not actually rendered.",
                potential_overcharge=0,
            ))

        # --- Check 2: Mutually exclusive procedures ---
        code_set = set(codes.keys())
        for code_a, code_b, reason in MUTUALLY_EXCLUSIVE_PROCEDURES:
            if code_a in code_set and code_b in code_set:
                idx_b = codes[code_b][0]
                item_b = bill.line_items[idx_b]
                issues.append(VerificationIssue(
                    issue_type=IssueType.phantom_billing,
                    severity=IssueSeverity.critical,
                    cpt_code=f"{code_a}/{code_b}",
                    description=f"Mutually exclusive procedures on {date}",
                    details=f"{reason}. One of these charges may be phantom — "
                            f"a service billed but never performed.",
                    potential_overcharge=item_b.charge_amount * item_b.quantity,
                    line_item_index=idx_b,
                ))

        # --- Check 3: Time-overlap detection ---
        major_procs = [
            (cpt, codes[cpt][0])
            for cpt in codes
            if cpt in PROCEDURE_DURATION_MINUTES
        ]
        if len(major_procs) >= 2:
            total_minutes = sum(
                PROCEDURE_DURATION_MINUTES[cpt] for cpt, _ in major_procs
            )
            # A surgical day realistically caps at ~10 hours (600 min)
            if total_minutes > 600:
                proc_names = ", ".join(
                    f"{cpt} ({PROCEDURE_DURATION_MINUTES[cpt]} min)"
                    for cpt, _ in major_procs
                )
                last_idx = major_procs[-1][1]
                last_item = bill.line_items[last_idx]
                issues.append(VerificationIssue(
                    issue_type=IssueType.phantom_billing,
                    severity=IssueSeverity.warning,
                    cpt_code="N/A",
                    description=f"Impossible surgical schedule on {date}",
                    details=f"Major procedures totaling {total_minutes} minutes on {date}: "
                            f"{proc_names}. This exceeds a feasible surgical day (~600 min) "
                            f"and may indicate a phantom charge.",
                    potential_overcharge=last_item.charge_amount * last_item.quantity,
                    line_item_index=last_idx,
                ))

    return issues
