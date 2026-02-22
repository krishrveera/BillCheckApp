from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class BillLineItem(BaseModel):
    cpt_code: str = ""
    description: str
    charge_amount: float
    date_of_service: str
    quantity: int = 1
    unit_cost: Optional[float] = None


class PatientBill(BaseModel):
    patient_name: str
    mrn: str
    admission_date: str
    discharge_date: str
    primary_diagnosis_icd10: str
    secondary_diagnoses_icd10: list[str] = Field(default_factory=list)
    line_items: list[BillLineItem]
    total_billed: float
    facility_name: str


class ExtractedLineItem(BaseModel):
    cpt_code: str
    description: str
    charge_amount: float
    date_of_service: str
    quantity: int = 1
    source_text: str = ""


class ExtractedBillClaims(BaseModel):
    patient_name: str
    line_items: list[ExtractedLineItem]
    total_billed: float


class IssueSeverity(str, Enum):
    critical = "critical"
    warning = "warning"
    info = "info"


class IssueType(str, Enum):
    duplicate_charge = "duplicate_charge"
    date_outside_stay = "date_outside_stay"
    math_error = "math_error"
    cms_overcharge = "cms_overcharge"
    unbundling = "unbundling"
    implausible_procedure = "implausible_procedure"
    quantity_error = "quantity_error"
    dosage_anomaly = "dosage_anomaly"
    phantom_billing = "phantom_billing"


class VerificationIssue(BaseModel):
    issue_type: IssueType
    severity: IssueSeverity
    cpt_code: str
    description: str
    details: str
    potential_overcharge: float = 0.0
    line_item_index: Optional[int] = None


class VerificationReport(BaseModel):
    patient_name: str
    facility_name: str
    total_billed: float
    total_flagged: float
    issues: list[VerificationIssue]
    safety_score: int
    grade: str
    summary: str
    dispute_letter: str
    phone_script: str
