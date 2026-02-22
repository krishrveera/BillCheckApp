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
- IMPORTANT: Only use codes from the "CPT/HCPCS Code" column, NOT the hospital internal "Code" column (e.g., 0260, 0450, 0301 are hospital revenue codes, not CPT/HCPCS codes)
- If a line item has no CPT/HCPCS code (only a hospital internal code), set cpt_code to "" (empty string)
- Use standard CPT/HCPCS codes (5 characters for CPT, J-codes for pharmacy)
- Do NOT infer or guess CPT codes — only use codes explicitly listed in the CPT/HCPCS column
- Dates must be in YYYY-MM-DD format
- charge_amount is the PER-UNIT price (NOT the line total). If a line shows a total of $180 for qty 4, charge_amount should be 45.00 and quantity should be 4
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

    # Strip markdown code fences if present (e.g. ```json ... ```)
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw_text = "\n".join(lines)

    data = json.loads(raw_text)
    return ExtractedBillClaims(**data)


IMAGE_EXTRACTION_PROMPT = """You are a medical billing coding specialist. Extract every line item from this medical bill image into structured JSON.

Also extract the patient metadata. If any field is not visible, use "Unknown" for strings and "2025-01-01" for dates.

Return ONLY valid JSON (no markdown backticks, no explanation) with this exact schema:
{
    "patient_name": "string",
    "mrn": "string",
    "admission_date": "YYYY-MM-DD",
    "discharge_date": "YYYY-MM-DD",
    "primary_diagnosis_icd10": "string (ICD-10 code if visible, otherwise 'Unknown')",
    "secondary_diagnoses_icd10": ["string"],
    "facility_name": "string",
    "total_billed": number,
    "line_items": [
        {
            "cpt_code": "string",
            "description": "string",
            "charge_amount": number,
            "date_of_service": "YYYY-MM-DD",
            "quantity": integer
        }
    ]
}

Rules:
- Extract EVERY line item, even if it looks like a duplicate
- IMPORTANT: Only use codes from the "CPT/HCPCS Code" column, NOT the hospital internal "Code" column (e.g., 0260, 0450, 0301 are hospital revenue codes, not CPT/HCPCS codes)
- If a line item has no CPT/HCPCS code (only a hospital internal code), set cpt_code to "" (empty string)
- Use standard CPT/HCPCS codes (5 characters for CPT, J-codes for pharmacy)
- Do NOT infer or guess CPT codes — only use codes explicitly listed in the CPT/HCPCS column
- Dates must be in YYYY-MM-DD format
- charge_amount is the PER-UNIT price (NOT the line total). If a line shows a total of $180 for qty 4, charge_amount should be 45.00 and quantity should be 4
- quantity defaults to 1 if not specified"""


async def extract_bill_from_image(image_data: bytes, media_type: str) -> PatientBill:
    """Use Claude's vision to extract structured bill data from an image or PDF."""
    import base64
    client = AsyncAnthropic()

    b64_data = base64.standard_b64encode(image_data).decode("utf-8")

    if media_type == "application/pdf":
        content_block = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": b64_data,
            },
        }
    else:
        content_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": b64_data,
            },
        }

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [
                    content_block,
                    {
                        "type": "text",
                        "text": IMAGE_EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown code fences if present (e.g. ```json ... ```)
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # Remove opening fence (```json or ```) and closing fence (```)
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw_text = "\n".join(lines)

    data = json.loads(raw_text)

    from models import BillLineItem
    line_items = [
        BillLineItem(
            cpt_code=li["cpt_code"],
            description=li["description"],
            charge_amount=li["charge_amount"],
            date_of_service=li["date_of_service"],
            quantity=li.get("quantity", 1),
        )
        for li in data.get("line_items", [])
    ]

    return PatientBill(
        patient_name=data.get("patient_name", "Unknown"),
        mrn=data.get("mrn", "UPLOAD"),
        admission_date=data.get("admission_date", "2025-01-01"),
        discharge_date=data.get("discharge_date", "2025-01-01"),
        primary_diagnosis_icd10=data.get("primary_diagnosis_icd10", "Unknown"),
        secondary_diagnoses_icd10=data.get("secondary_diagnoses_icd10", []),
        facility_name=data.get("facility_name", "Unknown"),
        total_billed=data.get("total_billed", sum(li.charge_amount for li in line_items)),
        line_items=line_items,
    )


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
