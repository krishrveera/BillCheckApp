import json
import os
from anthropic import AsyncAnthropic
from models import PatientBill, ExtractedBillClaims, ExtractedLineItem


EXTRACTION_SYSTEM_PROMPT = """You are a medical billing coding specialist. Your job is to extract every line item from a medical bill into structured JSON.

Return ONLY valid JSON (no markdown backticks, no explanation) with this exact schema:
{
    "patient_name": "string",
    "total_billed": number,
    "line_items": [
        {
            "cpt_code": "string",
            "description": "string",
            "charge_amount": number,
            "date_of_service": "YYYY-MM-DD",
            "quantity": integer,
            "source_text": "string (the original text this was extracted from)"
        }
    ]
}

Rules:
- Extract EVERY line item, even if it looks like a duplicate
- Use standard CPT/HCPCS codes (5 characters for CPT, J-codes for pharmacy)
- Dates must be in YYYY-MM-DD format
- charge_amount is the total charge for that line (unit_cost * quantity if applicable)
- quantity defaults to 1 if not specified
- source_text should contain the original line from the bill"""


async def extract_bill_claims(bill_text: str) -> ExtractedBillClaims:
    """Use Claude to extract structured claims from bill text. This is the ONLY LLM call in the pipeline."""
    client = AsyncAnthropic()

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Extract all line items from this medical bill:\n\n{bill_text}"}
        ],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown backticks if present
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # Remove first and last lines (``` markers)
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines)

    data = json.loads(raw_text)
    return ExtractedBillClaims(**data)


def bill_to_text(bill: PatientBill) -> str:
    """Convert a PatientBill model to formatted text for extraction testing."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  {bill.facility_name}")
    lines.append(f"  PATIENT BILLING STATEMENT")
    lines.append("=" * 70)
    lines.append(f"  Patient: {bill.patient_name}")
    lines.append(f"  MRN: {bill.mrn}")
    lines.append(f"  Admission Date: {bill.admission_date}")
    lines.append(f"  Discharge Date: {bill.discharge_date}")
    lines.append(f"  Primary Diagnosis: {bill.primary_diagnosis_icd10}")
    if bill.secondary_diagnoses_icd10:
        lines.append(f"  Secondary Diagnoses: {', '.join(bill.secondary_diagnoses_icd10)}")
    lines.append("-" * 70)
    lines.append(f"  {'Date':<12} {'CPT':<8} {'Description':<30} {'Qty':>4} {'Amount':>12}")
    lines.append("-" * 70)

    for item in bill.line_items:
        amt = f"${item.charge_amount * item.quantity:,.2f}"
        lines.append(f"  {item.date_of_service:<12} {item.cpt_code:<8} {item.description:<30} {item.quantity:>4} {amt:>12}")

    lines.append("-" * 70)
    lines.append(f"  {'TOTAL BILLED':>56} ${bill.total_billed:>12,.2f}")
    lines.append("=" * 70)

    return "\n".join(lines)
