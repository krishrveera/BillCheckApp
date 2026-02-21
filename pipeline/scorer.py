from models import PatientBill, VerificationIssue, VerificationReport, IssueSeverity, IssueType
from collections import Counter


def calculate_safety_score(issues: list[VerificationIssue]) -> tuple[int, str]:
    """Calculate a safety score (0-100) and letter grade based on issues found."""
    score = 100

    for issue in issues:
        if issue.severity == IssueSeverity.critical:
            score -= 15
        elif issue.severity == IssueSeverity.warning:
            score -= 7
        elif issue.severity == IssueSeverity.info:
            score -= 2

    score = max(0, score)

    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"

    return score, grade


def _build_summary(issues: list[VerificationIssue]) -> str:
    """Build a human-readable summary of findings."""
    if not issues:
        return "No billing issues found. This bill appears to be correctly coded."

    critical = [i for i in issues if i.severity == IssueSeverity.critical]
    warnings = [i for i in issues if i.severity == IssueSeverity.warning]
    info = [i for i in issues if i.severity == IssueSeverity.info]

    type_counts = Counter(i.issue_type.value for i in issues)
    type_list = ", ".join(
        t.replace("_", " ") for t in type_counts
    )

    total_overcharge = sum(i.potential_overcharge for i in issues)

    parts = [f"Found {len(issues)} issue(s):"]
    if critical:
        parts.append(f"{len(critical)} critical")
    if warnings:
        parts.append(f"{len(warnings)} warning(s)")
    if info:
        parts.append(f"{len(info)} informational")

    summary = parts[0] + " " + ", ".join(parts[1:]) + f" ({type_list})."
    summary += f" Potential overcharges: ${total_overcharge:,.2f}."

    return summary


def _generate_dispute_letter(bill: PatientBill, issues: list[VerificationIssue]) -> str:
    """Generate a formal dispute letter."""
    critical = [i for i in issues if i.severity == IssueSeverity.critical]
    warnings = [i for i in issues if i.severity == IssueSeverity.warning]
    total_overcharge = sum(i.potential_overcharge for i in issues)

    letter = f"""FORMAL DISPUTE OF MEDICAL BILLING CHARGES

Date: [INSERT DATE]

To: Billing Department
    {bill.facility_name}

Re: Patient {bill.patient_name}
    MRN: {bill.mrn}
    Dates of Service: {bill.admission_date} through {bill.discharge_date}
    Total Billed: ${bill.total_billed:,.2f}

Dear Billing Department,

I am writing to formally dispute charges on the above-referenced account. Upon careful review of the itemized bill, I have identified {len(issues)} billing issue(s) totaling approximately ${total_overcharge:,.2f} in potential overcharges.

CRITICAL ISSUES REQUIRING IMMEDIATE CORRECTION:
"""

    for i, issue in enumerate(critical, 1):
        letter += f"""
{i}. {issue.description}
   CPT Code: {issue.cpt_code}
   Details: {issue.details}
   Potential Overcharge: ${issue.potential_overcharge:,.2f}
"""

    if warnings:
        letter += "\nADDITIONAL CONCERNS:\n"
        for i, issue in enumerate(warnings, 1):
            letter += f"""
{i}. {issue.description}
   CPT Code: {issue.cpt_code}
   Details: {issue.details}
   Potential Overcharge: ${issue.potential_overcharge:,.2f}
"""

    letter += f"""
I request that you:
1. Conduct a thorough review of these charges
2. Provide an itemized correction for each identified issue
3. Issue an adjusted bill reflecting accurate charges
4. Confirm these corrections in writing within 30 days

Under the No Surprises Act (Public Law 116-260) and applicable state billing regulations, patients have the right to dispute billing errors and receive corrected statements. I also request a copy of the facility's charge master for the CPT codes in question.

Please respond within 30 business days. If I do not receive a satisfactory response, I will escalate this matter to the state Attorney General's office and the Centers for Medicare & Medicaid Services (CMS).

Sincerely,
{bill.patient_name}
[Patient Address]
[Patient Phone]

cc: State Insurance Commissioner
    CMS Regional Office
"""

    return letter


def _generate_phone_script(bill: PatientBill, issues: list[VerificationIssue]) -> str:
    """Generate a step-by-step phone script for disputing the bill."""
    total_overcharge = sum(i.potential_overcharge for i in issues)

    script = f"""PHONE DISPUTE SCRIPT — {bill.patient_name}
{'=' * 50}

BEFORE YOU CALL:
- Have your bill in front of you
- Have a pen and paper ready to document the call
- Note the date and time of your call
- Ask for the name of everyone you speak with

STEP 1: OPENING
"Hello, my name is {bill.patient_name}. My MRN is {bill.mrn}. I'm calling to dispute charges on my bill dated {bill.admission_date} through {bill.discharge_date}. The total billed is ${bill.total_billed:,.2f}, and I've identified ${total_overcharge:,.2f} in potential billing errors."

STEP 2: REQUEST A SUPERVISOR
"I'd like to speak with a billing supervisor or patient advocate, as I have specific coding concerns that require someone familiar with CPT codes and NCCI bundling edits."

STEP 3: PRESENT EACH ISSUE
"""

    for i, issue in enumerate(issues, 1):
        severity_label = "CRITICAL" if issue.severity == IssueSeverity.critical else "CONCERN"
        script += f"""
ISSUE {i} ({severity_label}):
"I'm looking at CPT code {issue.cpt_code} — {issue.description}.
{issue.details}
This represents a potential overcharge of ${issue.potential_overcharge:,.2f}."

"""

    script += f"""STEP 4: REQUEST ACTION
"Based on these {len(issues)} issues, I'm requesting:
1. An immediate review of each charge I've identified
2. A corrected itemized statement
3. A hold on any collection activity until the review is complete
4. Written confirmation of any adjustments

Can you provide a case number or reference number for this dispute?"

STEP 5: DOCUMENT THE CALL
Write down:
- Date and time of call: _______________
- Name of representative: _______________
- Name of supervisor (if transferred): _______________
- Case/reference number: _______________
- Promised follow-up date: _______________
- Summary of what they agreed to: _______________

STEP 6: FOLLOW UP
"Thank you. I will also be sending a formal written dispute letter to your billing department. If I don't hear back within 30 days, I will escalate to the state Attorney General and CMS."

IMPORTANT: If they are uncooperative:
- Ask for the hospital's Patient Advocate
- File a complaint with your state's Department of Insurance
- Contact CMS at 1-800-MEDICARE
- Consider contacting your state Attorney General's office
"""

    return script


def generate_report(bill: PatientBill, issues: list[VerificationIssue]) -> VerificationReport:
    """Generate the complete verification report."""
    score, grade = calculate_safety_score(issues)
    total_flagged = sum(i.potential_overcharge for i in issues)
    summary = _build_summary(issues)
    dispute_letter = _generate_dispute_letter(bill, issues)
    phone_script = _generate_phone_script(bill, issues)

    return VerificationReport(
        patient_name=bill.patient_name,
        facility_name=bill.facility_name,
        total_billed=bill.total_billed,
        total_flagged=total_flagged,
        issues=issues,
        safety_score=score,
        grade=grade,
        summary=summary,
        dispute_letter=dispute_letter,
        phone_script=phone_script,
    )
