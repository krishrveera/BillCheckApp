from models import PatientBill, BillLineItem


def get_synthetic_bills() -> list[dict]:
    """Return 3 synthetic patient bills, each with 5 intentional billing errors."""
    return [
        _patient_1_maria_garcia(),
        _patient_2_robert_thompson(),
        _patient_3_dorothy_chen(),
    ]


def _patient_1_maria_garcia() -> dict:
    """Appendectomy patient with 5 billing errors."""
    line_items = [
        BillLineItem(cpt_code="99284", description="ED visit, moderately high severity", charge_amount=1850.00, date_of_service="2025-11-10", quantity=1),
        BillLineItem(cpt_code="74177", description="CT abdomen/pelvis with contrast", charge_amount=3200.00, date_of_service="2025-11-10", quantity=1),
        # ERROR 2 - UNBUNDLING: CT w/o contrast billed alongside CT w/ contrast
        BillLineItem(cpt_code="74176", description="CT abdomen/pelvis without contrast", charge_amount=2400.00, date_of_service="2025-11-10", quantity=1),
        BillLineItem(cpt_code="85025", description="CBC with differential", charge_amount=120.00, date_of_service="2025-11-10", quantity=1),
        BillLineItem(cpt_code="80053", description="Comprehensive metabolic panel", charge_amount=185.00, date_of_service="2025-11-10", quantity=1),
        BillLineItem(cpt_code="81001", description="Urinalysis with microscopy", charge_amount=65.00, date_of_service="2025-11-10", quantity=1),
        BillLineItem(cpt_code="44970", description="Laparoscopic appendectomy", charge_amount=18500.00, date_of_service="2025-11-10", quantity=1),
        BillLineItem(cpt_code="00810", description="Anesthesia, lower abdominal surgery", charge_amount=4200.00, date_of_service="2025-11-10", quantity=1),
        BillLineItem(cpt_code="88305", description="Surgical pathology, gross and micro", charge_amount=650.00, date_of_service="2025-11-10", quantity=1),
        BillLineItem(cpt_code="96360", description="IV hydration, initial 31-60 min", charge_amount=380.00, date_of_service="2025-11-10", quantity=1),
        # ERROR 3 - DUPLICATE: IV hydration charged twice on same day
        BillLineItem(cpt_code="96360", description="IV hydration, initial 31-60 min", charge_amount=380.00, date_of_service="2025-11-10", quantity=1),
        BillLineItem(cpt_code="J0290", description="Ampicillin injection, 500mg", charge_amount=45.00, date_of_service="2025-11-10", quantity=2),
        BillLineItem(cpt_code="J2270", description="Morphine sulfate injection, 10mg", charge_amount=35.00, date_of_service="2025-11-10", quantity=1),
        BillLineItem(cpt_code="99231", description="Subsequent hospital care, low", charge_amount=420.00, date_of_service="2025-11-11", quantity=1),
        BillLineItem(cpt_code="85025", description="CBC with differential", charge_amount=120.00, date_of_service="2025-11-11", quantity=1),
        BillLineItem(cpt_code="71046", description="Chest X-ray, 2 views", charge_amount=350.00, date_of_service="2025-11-11", quantity=1),
        # ERROR 4 - IMPLAUSIBLE: Cardiac stress test for appendicitis patient
        BillLineItem(cpt_code="93015", description="Cardiac stress test, complete", charge_amount=1450.00, date_of_service="2025-11-11", quantity=1),
        BillLineItem(cpt_code="99238", description="Discharge day management", charge_amount=520.00, date_of_service="2025-11-12", quantity=1),
        # ERROR 5 - DATE: CMP billed one day AFTER discharge
        BillLineItem(cpt_code="80053", description="Comprehensive metabolic panel", charge_amount=185.00, date_of_service="2025-11-13", quantity=1),
    ]

    # ERROR 1 - MATH: total doesn't match sum of line items
    actual_sum = sum(item.charge_amount * item.quantity for item in line_items)
    inflated_total = actual_sum + 840.00

    bill = PatientBill(
        patient_name="Maria Garcia",
        mrn="MG-2025-44891",
        admission_date="2025-11-10",
        discharge_date="2025-11-12",
        primary_diagnosis_icd10="K35.80",
        secondary_diagnoses_icd10=[],
        line_items=line_items,
        total_billed=inflated_total,
        facility_name="St. Marcus Regional Medical Center",
    )

    known_errors = [
        "MATH ERROR: Total billed is $840.00 more than the sum of line items",
        "UNBUNDLING: CT without contrast (74176, $2,400) billed alongside CT with contrast (74177) on 2025-11-10",
        "DUPLICATE: IV hydration (96360, $380) charged twice on 2025-11-10",
        "IMPLAUSIBLE: Cardiac stress test (93015, $1,450) is not plausible for appendicitis (K35.80)",
        "DATE ERROR: CMP (80053, $185) billed on 2025-11-13, one day after discharge (2025-11-12)",
    ]

    return {"id": "patient-1", "bill": bill, "known_errors": known_errors}


def _patient_2_robert_thompson() -> dict:
    """CHF exacerbation patient with 5 billing errors."""
    line_items = [
        # Day 1 - ED and admission (2025-10-15)
        BillLineItem(cpt_code="99285", description="ED visit, high severity", charge_amount=2800.00, date_of_service="2025-10-15", quantity=1),
        BillLineItem(cpt_code="93000", description="ECG, complete", charge_amount=310.00, date_of_service="2025-10-15", quantity=1),
        # ERROR 1 - UNBUNDLING: ECG interpretation billed separately alongside complete ECG
        BillLineItem(cpt_code="93010", description="ECG, interpretation only", charge_amount=145.00, date_of_service="2025-10-15", quantity=1),
        BillLineItem(cpt_code="85025", description="CBC with differential", charge_amount=125.00, date_of_service="2025-10-15", quantity=1),
        BillLineItem(cpt_code="80053", description="Comprehensive metabolic panel", charge_amount=195.00, date_of_service="2025-10-15", quantity=1),
        # ERROR 2 - UNBUNDLING: Creatinine billed separately alongside CMP
        BillLineItem(cpt_code="82565", description="Creatinine, blood", charge_amount=85.00, date_of_service="2025-10-15", quantity=1),
        BillLineItem(cpt_code="85379", description="D-dimer", charge_amount=165.00, date_of_service="2025-10-15", quantity=1),
        BillLineItem(cpt_code="85610", description="Prothrombin time (PT)", charge_amount=78.00, date_of_service="2025-10-15", quantity=1),
        BillLineItem(cpt_code="71046", description="Chest X-ray, 2 views", charge_amount=365.00, date_of_service="2025-10-15", quantity=1),
        BillLineItem(cpt_code="93306", description="Echocardiography, complete", charge_amount=2100.00, date_of_service="2025-10-15", quantity=1),
        # ERROR 5 - DUPLICATE: Echocardiography charged twice on same day
        BillLineItem(cpt_code="93306", description="Echocardiography, complete", charge_amount=2100.00, date_of_service="2025-10-15", quantity=1),
        BillLineItem(cpt_code="96365", description="IV therapeutic infusion, initial", charge_amount=520.00, date_of_service="2025-10-15", quantity=1),
        BillLineItem(cpt_code="99223", description="Initial hospital care, high", charge_amount=1450.00, date_of_service="2025-10-15", quantity=1),
        # Day 2 (2025-10-16)
        BillLineItem(cpt_code="99232", description="Subsequent hospital care", charge_amount=580.00, date_of_service="2025-10-16", quantity=1),
        BillLineItem(cpt_code="94640", description="Nebulizer treatment", charge_amount=175.00, date_of_service="2025-10-16", quantity=2),
        BillLineItem(cpt_code="80053", description="Comprehensive metabolic panel", charge_amount=195.00, date_of_service="2025-10-16", quantity=1),
        BillLineItem(cpt_code="96360", description="IV hydration", charge_amount=385.00, date_of_service="2025-10-16", quantity=1),
        # ERROR 6 - DOSAGE ANOMALY: 50 units of morphine = 500mg, max safe daily is 100mg
        BillLineItem(cpt_code="J2270", description="Morphine sulfate injection, 10mg", charge_amount=35.00, date_of_service="2025-10-16", quantity=50),
        # Day 3 (2025-10-17)
        BillLineItem(cpt_code="99232", description="Subsequent hospital care", charge_amount=580.00, date_of_service="2025-10-17", quantity=1),
        BillLineItem(cpt_code="94640", description="Nebulizer treatment", charge_amount=175.00, date_of_service="2025-10-17", quantity=2),
        BillLineItem(cpt_code="85025", description="CBC with differential", charge_amount=125.00, date_of_service="2025-10-17", quantity=1),
        # ERROR 3 - IMPLAUSIBLE: Laparoscopic appendectomy for CHF patient
        BillLineItem(cpt_code="44970", description="Laparoscopic appendectomy", charge_amount=18500.00, date_of_service="2025-10-17", quantity=1),
        # Day 4 (2025-10-18)
        BillLineItem(cpt_code="99232", description="Subsequent hospital care", charge_amount=580.00, date_of_service="2025-10-18", quantity=1),
        BillLineItem(cpt_code="80053", description="Comprehensive metabolic panel", charge_amount=195.00, date_of_service="2025-10-18", quantity=1),
        BillLineItem(cpt_code="94640", description="Nebulizer treatment", charge_amount=175.00, date_of_service="2025-10-18", quantity=1),
        # Day 5 (2025-10-19)
        BillLineItem(cpt_code="99232", description="Subsequent hospital care", charge_amount=580.00, date_of_service="2025-10-19", quantity=1),
        BillLineItem(cpt_code="71046", description="Chest X-ray, 2 views", charge_amount=365.00, date_of_service="2025-10-19", quantity=1),
        # Discharge (2025-10-20)
        BillLineItem(cpt_code="99239", description="Discharge day management, >30 min", charge_amount=680.00, date_of_service="2025-10-20", quantity=1),
        # ERROR 4 - DATE: CMP billed one day after discharge
        BillLineItem(cpt_code="80053", description="Comprehensive metabolic panel", charge_amount=195.00, date_of_service="2025-10-21", quantity=1),
    ]

    total = sum(item.charge_amount * item.quantity for item in line_items)

    bill = PatientBill(
        patient_name="Robert Thompson",
        mrn="RT-2025-77234",
        admission_date="2025-10-15",
        discharge_date="2025-10-20",
        primary_diagnosis_icd10="I50.23",
        secondary_diagnoses_icd10=["I48.91", "E11.9"],
        line_items=line_items,
        total_billed=total,
        facility_name="Mercy General Hospital",
    )

    known_errors = [
        "UNBUNDLING: ECG interpretation (93010, $145) billed separately alongside complete ECG (93000) on 2025-10-15",
        "UNBUNDLING: Creatinine (82565, $85) billed separately alongside CMP (80053) on 2025-10-15",
        "IMPLAUSIBLE: Laparoscopic appendectomy (44970, $18,500) is not plausible for heart failure (I50.23)",
        "DATE ERROR: CMP (80053, $195) billed on 2025-10-21, one day after discharge (2025-10-20)",
        "DUPLICATE: Echocardiography (93306, $2,100) charged twice on 2025-10-15",
        "DOSAGE ANOMALY: Morphine (J2270) billed 50 units (500 mg) on 2025-10-16 — max safe daily dose is 100 mg (5.0x the limit)",
    ]

    return {"id": "patient-2", "bill": bill, "known_errors": known_errors}


def _patient_3_dorothy_chen() -> dict:
    """Total knee replacement patient with 5 billing errors."""
    line_items = [
        # Day 1 - Surgery (2025-09-22)
        BillLineItem(cpt_code="99222", description="Initial hospital care, moderate", charge_amount=980.00, date_of_service="2025-09-22", quantity=1),
        BillLineItem(cpt_code="93000", description="ECG, complete (pre-op)", charge_amount=295.00, date_of_service="2025-09-22", quantity=1),
        BillLineItem(cpt_code="85025", description="CBC with differential", charge_amount=118.00, date_of_service="2025-09-22", quantity=1),
        BillLineItem(cpt_code="80053", description="Comprehensive metabolic panel", charge_amount=190.00, date_of_service="2025-09-22", quantity=1),
        # ERROR 2 - UNBUNDLING: Potassium billed separately alongside CMP
        BillLineItem(cpt_code="84132", description="Potassium, serum", charge_amount=72.00, date_of_service="2025-09-22", quantity=1),
        BillLineItem(cpt_code="85610", description="Prothrombin time (PT)", charge_amount=75.00, date_of_service="2025-09-22", quantity=1),
        BillLineItem(cpt_code="85730", description="PTT", charge_amount=95.00, date_of_service="2025-09-22", quantity=1),
        BillLineItem(cpt_code="71046", description="Chest X-ray, 2 views (pre-op)", charge_amount=340.00, date_of_service="2025-09-22", quantity=1),
        BillLineItem(cpt_code="27447", description="Total knee arthroplasty", charge_amount=32000.00, date_of_service="2025-09-22", quantity=1),
        BillLineItem(cpt_code="01402", description="Anesthesia, knee arthroplasty", charge_amount=6800.00, date_of_service="2025-09-22", quantity=1),
        BillLineItem(cpt_code="96360", description="IV hydration, initial", charge_amount=375.00, date_of_service="2025-09-22", quantity=1),
        BillLineItem(cpt_code="J2270", description="Morphine sulfate injection, 10mg", charge_amount=42.00, date_of_service="2025-09-22", quantity=2),
        BillLineItem(cpt_code="J1885", description="Ketorolac injection, 15mg", charge_amount=28.00, date_of_service="2025-09-22", quantity=1),
        # ERROR 3 - IMPLAUSIBLE: Surgical pathology not standard for knee replacement
        BillLineItem(cpt_code="88305", description="Surgical pathology, gross and micro", charge_amount=650.00, date_of_service="2025-09-22", quantity=1),
        # Day 2 (2025-09-23)
        BillLineItem(cpt_code="99231", description="Subsequent hospital care", charge_amount=420.00, date_of_service="2025-09-23", quantity=1),
        BillLineItem(cpt_code="97161", description="PT evaluation, low complexity", charge_amount=480.00, date_of_service="2025-09-23", quantity=1),
        BillLineItem(cpt_code="97110", description="Therapeutic exercises, 15 min", charge_amount=185.00, date_of_service="2025-09-23", quantity=2),
        BillLineItem(cpt_code="J2270", description="Morphine sulfate injection, 10mg", charge_amount=42.00, date_of_service="2025-09-23", quantity=1),
        # ERROR 4 - DUPLICATE: Morphine charged twice on same day
        BillLineItem(cpt_code="J2270", description="Morphine sulfate injection, 10mg", charge_amount=42.00, date_of_service="2025-09-23", quantity=1),
        # Day 3 (2025-09-24)
        BillLineItem(cpt_code="99231", description="Subsequent hospital care", charge_amount=420.00, date_of_service="2025-09-24", quantity=1),
        BillLineItem(cpt_code="97110", description="Therapeutic exercises, 15 min", charge_amount=185.00, date_of_service="2025-09-24", quantity=2),
        BillLineItem(cpt_code="80053", description="Comprehensive metabolic panel", charge_amount=190.00, date_of_service="2025-09-24", quantity=1),
        # Discharge (2025-09-25)
        BillLineItem(cpt_code="99238", description="Discharge day management", charge_amount=520.00, date_of_service="2025-09-25", quantity=1),
        # ERROR 5 - DATE + IMPLAUSIBLE: Cardiac stress test billed after discharge AND implausible for knee OA
        BillLineItem(cpt_code="93015", description="Cardiac stress test, complete", charge_amount=1450.00, date_of_service="2025-09-26", quantity=1),
    ]

    # ERROR 1 - MATH: total doesn't match
    actual_sum = sum(item.charge_amount * item.quantity for item in line_items)
    inflated_total = actual_sum + 1250.00

    bill = PatientBill(
        patient_name="Dorothy Chen",
        mrn="DC-2025-33106",
        admission_date="2025-09-22",
        discharge_date="2025-09-25",
        primary_diagnosis_icd10="M17.11",
        secondary_diagnoses_icd10=["E11.65", "I10"],
        line_items=line_items,
        total_billed=inflated_total,
        facility_name="Pacific Coast University Hospital",
    )

    known_errors = [
        "MATH ERROR: Total billed is $1,250.00 more than the sum of line items",
        "UNBUNDLING: Potassium (84132, $72) billed separately alongside CMP (80053) on 2025-09-22",
        "IMPLAUSIBLE: Surgical pathology (88305, $650) is not standard for knee osteoarthritis (M17.11)",
        "DUPLICATE: Morphine injection (J2270, $42) charged twice on 2025-09-23",
        "DATE + IMPLAUSIBLE: Cardiac stress test (93015, $1,450) billed on 2025-09-26 after discharge (2025-09-25) AND implausible for knee osteoarthritis",
    ]

    return {"id": "patient-3", "bill": bill, "known_errors": known_errors}
