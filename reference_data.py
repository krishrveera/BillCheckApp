# ── Static fallback fee schedule ────────────────────────────────────────
# Used ONLY when the CMS API (pipeline/cms_api.py) is unreachable.
# Rates approximate CMS Medicare national averages.
CMS_FEE_SCHEDULE_FALLBACK = {
    # E&M - Office visits
    "99211": {"description": "Office visit, minimal", "medicare_rate": 23.0, "category": "E&M"},
    "99212": {"description": "Office visit, straightforward", "medicare_rate": 56.0, "category": "E&M"},
    "99213": {"description": "Office visit, low complexity", "medicare_rate": 92.0, "category": "E&M"},
    "99214": {"description": "Office visit, moderate complexity", "medicare_rate": 131.0, "category": "E&M"},
    "99215": {"description": "Office visit, high complexity", "medicare_rate": 176.0, "category": "E&M"},
    # E&M - Initial hospital care
    "99221": {"description": "Initial hospital care, low", "medicare_rate": 143.0, "category": "E&M"},
    "99222": {"description": "Initial hospital care, moderate", "medicare_rate": 196.0, "category": "E&M"},
    "99223": {"description": "Initial hospital care, high", "medicare_rate": 272.0, "category": "E&M"},
    # E&M - Subsequent hospital care
    "99231": {"description": "Subsequent hospital care, low", "medicare_rate": 80.0, "category": "E&M"},
    "99232": {"description": "Subsequent hospital care, moderate", "medicare_rate": 112.0, "category": "E&M"},
    "99233": {"description": "Subsequent hospital care, high", "medicare_rate": 160.0, "category": "E&M"},
    # E&M - Discharge
    "99238": {"description": "Discharge day management, 30 min", "medicare_rate": 103.0, "category": "E&M"},
    "99239": {"description": "Discharge day management, >30 min", "medicare_rate": 145.0, "category": "E&M"},
    # E&M - ED visits
    "99281": {"description": "ED visit, minimal", "medicare_rate": 22.0, "category": "E&M"},
    "99282": {"description": "ED visit, low", "medicare_rate": 50.0, "category": "E&M"},
    "99283": {"description": "ED visit, moderate", "medicare_rate": 95.0, "category": "E&M"},
    "99284": {"description": "ED visit, moderately high", "medicare_rate": 168.0, "category": "E&M"},
    "99285": {"description": "ED visit, high", "medicare_rate": 264.0, "category": "E&M"},
    # E&M - Critical care
    "99291": {"description": "Critical care, first 30-74 min", "medicare_rate": 285.0, "category": "E&M"},
    "99292": {"description": "Critical care, each additional 30 min", "medicare_rate": 127.0, "category": "E&M"},
    # Surgery
    "44950": {"description": "Appendectomy, open", "medicare_rate": 670.0, "category": "Surgery"},
    "44970": {"description": "Appendectomy, laparoscopic", "medicare_rate": 780.0, "category": "Surgery"},
    "47562": {"description": "Cholecystectomy, laparoscopic", "medicare_rate": 720.0, "category": "Surgery"},
    "47563": {"description": "Cholecystectomy, lap w/ cholangiography", "medicare_rate": 830.0, "category": "Surgery"},
    "27447": {"description": "Total knee arthroplasty", "medicare_rate": 1450.0, "category": "Surgery"},
    "27130": {"description": "Total hip arthroplasty", "medicare_rate": 1380.0, "category": "Surgery"},
    "33533": {"description": "CABG, single arterial graft", "medicare_rate": 2100.0, "category": "Surgery"},
    # Cardiac
    "93000": {"description": "ECG, complete (tracing + interpretation)", "medicare_rate": 17.0, "category": "Cardiac"},
    "93005": {"description": "ECG, tracing only", "medicare_rate": 8.0, "category": "Cardiac"},
    "93010": {"description": "ECG, interpretation only", "medicare_rate": 9.0, "category": "Cardiac"},
    "93015": {"description": "Cardiac stress test, complete", "medicare_rate": 115.0, "category": "Cardiac"},
    "93306": {"description": "Echocardiography, complete", "medicare_rate": 175.0, "category": "Cardiac"},
    "93458": {"description": "Left heart catheterization", "medicare_rate": 560.0, "category": "Cardiac"},
    # Lab
    "80048": {"description": "Basic metabolic panel (BMP)", "medicare_rate": 11.0, "category": "Lab"},
    "80050": {"description": "General health panel", "medicare_rate": 32.0, "category": "Lab"},
    "80053": {"description": "Comprehensive metabolic panel (CMP)", "medicare_rate": 14.0, "category": "Lab"},
    "80061": {"description": "Lipid panel", "medicare_rate": 18.0, "category": "Lab"},
    "85025": {"description": "CBC with differential", "medicare_rate": 11.0, "category": "Lab"},
    "85027": {"description": "CBC, automated", "medicare_rate": 8.0, "category": "Lab"},
    "82947": {"description": "Glucose, quantitative", "medicare_rate": 5.0, "category": "Lab"},
    "82565": {"description": "Creatinine, blood", "medicare_rate": 7.0, "category": "Lab"},
    "84443": {"description": "TSH", "medicare_rate": 22.0, "category": "Lab"},
    "83036": {"description": "Hemoglobin A1c", "medicare_rate": 13.0, "category": "Lab"},
    "82310": {"description": "Calcium, total", "medicare_rate": 7.0, "category": "Lab"},
    "84132": {"description": "Potassium, serum", "medicare_rate": 6.0, "category": "Lab"},
    "84295": {"description": "Sodium, serum", "medicare_rate": 6.0, "category": "Lab"},
    "85610": {"description": "Prothrombin time (PT)", "medicare_rate": 6.0, "category": "Lab"},
    "85730": {"description": "PTT (partial thromboplastin time)", "medicare_rate": 9.0, "category": "Lab"},
    "85379": {"description": "D-dimer", "medicare_rate": 14.0, "category": "Lab"},
    "81001": {"description": "Urinalysis, with microscopy", "medicare_rate": 4.0, "category": "Lab"},
    "81003": {"description": "Urinalysis, automated", "medicare_rate": 3.0, "category": "Lab"},
    # Radiology
    "71046": {"description": "Chest X-ray, 2 views", "medicare_rate": 28.0, "category": "Radiology"},
    "71048": {"description": "Chest X-ray, 3+ views", "medicare_rate": 33.0, "category": "Radiology"},
    "74177": {"description": "CT abdomen/pelvis with contrast", "medicare_rate": 245.0, "category": "Radiology"},
    "74176": {"description": "CT abdomen/pelvis without contrast", "medicare_rate": 200.0, "category": "Radiology"},
    "70553": {"description": "MRI brain with/without contrast", "medicare_rate": 350.0, "category": "Radiology"},
    "72148": {"description": "MRI lumbar spine without contrast", "medicare_rate": 280.0, "category": "Radiology"},
    "76700": {"description": "Ultrasound, abdominal, complete", "medicare_rate": 105.0, "category": "Radiology"},
    "76856": {"description": "Ultrasound, pelvic", "medicare_rate": 105.0, "category": "Radiology"},
    # Anesthesia
    "00740": {"description": "Anesthesia, upper GI endoscopy", "medicare_rate": 280.0, "category": "Anesthesia"},
    "00810": {"description": "Anesthesia, lower abdominal surgery", "medicare_rate": 340.0, "category": "Anesthesia"},
    "01402": {"description": "Anesthesia, knee arthroplasty", "medicare_rate": 520.0, "category": "Anesthesia"},
    # IV/Infusion
    "96360": {"description": "IV hydration, initial 31-60 min", "medicare_rate": 38.0, "category": "IV/Infusion"},
    "96361": {"description": "IV hydration, each additional hour", "medicare_rate": 22.0, "category": "IV/Infusion"},
    "96365": {"description": "IV therapeutic infusion, initial", "medicare_rate": 65.0, "category": "IV/Infusion"},
    "96374": {"description": "IV push, single substance", "medicare_rate": 25.0, "category": "IV/Infusion"},
    # Pharmacy (HCPCS J-codes)
    "J0290": {"description": "Ampicillin injection, 500mg", "medicare_rate": 3.0, "category": "Pharmacy"},
    "J2270": {"description": "Morphine sulfate injection, 10mg", "medicare_rate": 4.0, "category": "Pharmacy"},
    "J1885": {"description": "Ketorolac injection, 15mg", "medicare_rate": 2.0, "category": "Pharmacy"},
    "J2550": {"description": "Promethazine injection, 50mg", "medicare_rate": 3.0, "category": "Pharmacy"},
    "J3010": {"description": "Fentanyl citrate injection, 0.1mg", "medicare_rate": 2.0, "category": "Pharmacy"},
    # Pathology
    "88305": {"description": "Surgical pathology, gross/micro", "medicare_rate": 75.0, "category": "Pathology"},
    "88307": {"description": "Surgical pathology, complex", "medicare_rate": 155.0, "category": "Pathology"},
    # Physical Therapy
    "97110": {"description": "Therapeutic exercises, 15 min", "medicare_rate": 33.0, "category": "PT"},
    "97140": {"description": "Manual therapy, 15 min", "medicare_rate": 31.0, "category": "PT"},
    "97161": {"description": "PT evaluation, low complexity", "medicare_rate": 92.0, "category": "PT"},
    "97162": {"description": "PT evaluation, moderate complexity", "medicare_rate": 112.0, "category": "PT"},
    # Respiratory
    "94640": {"description": "Nebulizer treatment", "medicare_rate": 16.0, "category": "Respiratory"},
    "94060": {"description": "Bronchodilator response spirometry", "medicare_rate": 55.0, "category": "Respiratory"},
}


# NCCI Bundling Edits: (column1_code, column2_code, reason)
NCCI_EDITS = [
    ("93000", "93005", "ECG tracing (93005) is included in complete ECG (93000)"),
    ("93000", "93010", "ECG interpretation (93010) is included in complete ECG (93000)"),
    ("80053", "80048", "BMP (80048) is included in CMP (80053)"),
    ("80053", "82565", "Creatinine (82565) is included in CMP (80053)"),
    ("80053", "82947", "Glucose (82947) is included in CMP (80053)"),
    ("80053", "84132", "Potassium (84132) is included in CMP (80053)"),
    ("80053", "84295", "Sodium (84295) is included in CMP (80053)"),
    ("80053", "82310", "Calcium (82310) is included in CMP (80053)"),
    ("85025", "85027", "Automated CBC (85027) is included in CBC w/diff (85025)"),
    ("80050", "80053", "CMP (80053) is included in General Health Panel (80050)"),
    ("80050", "85025", "CBC w/diff (85025) is included in General Health Panel (80050)"),
    ("80050", "84443", "TSH (84443) is included in General Health Panel (80050)"),
    ("74177", "74176", "CT w/o contrast (74176) is included in CT w/ contrast (74177)"),
    ("96365", "96374", "IV push (96374) is included in IV therapeutic infusion (96365) for same drug"),
    ("81001", "81003", "Automated UA (81003) is included in UA w/ microscopy (81001)"),
    ("44970", "99221", "Initial hospital care (99221) is bundled with appendectomy (44970) on same day"),
    ("44970", "99222", "Initial hospital care (99222) is bundled with appendectomy (44970) on same day"),
    ("47562", "99221", "Initial hospital care (99221) is bundled with cholecystectomy (47562) on same day"),
    ("47562", "99222", "Initial hospital care (99222) is bundled with cholecystectomy (47562) on same day"),
    ("27447", "99221", "Initial hospital care (99221) is bundled with knee arthroplasty (27447) on same day"),
    ("27447", "99222", "Initial hospital care (99222) is bundled with knee arthroplasty (27447) on same day"),
]

# Build lookup dict for fast access
NCCI_LOOKUP: dict[str, list[tuple[str, str]]] = {}
for col1, col2, reason in NCCI_EDITS:
    if col1 not in NCCI_LOOKUP:
        NCCI_LOOKUP[col1] = []
    NCCI_LOOKUP[col1].append((col2, reason))


# ICD-10 to CPT Plausibility Mapping
ICD10_PLAUSIBLE_CPTS: dict[str, dict] = {
    "K35": {
        "description": "Acute appendicitis",
        "plausible": {
            "44950", "44970",  # appendectomy
            "00810",  # anesthesia
            "74177", "74176", "76700",  # imaging
            "80053", "80048", "85025", "85027", "82565", "82947", "81001", "81003",  # labs
            "88305", "88307",  # pathology
            "96360", "96361", "96365", "96374",  # IV
            "J0290", "J2270", "J1885", "J2550", "J3010",  # meds
            "99281", "99282", "99283", "99284", "99285",  # ED
            "99221", "99222", "99223", "99231", "99232", "99233",  # hospital care
            "99238", "99239",  # discharge
            "71046", "71048",  # chest xray
        },
        "implausible": {
            "93015",  # cardiac stress test
            "70553",  # MRI brain
            "27447", "27130",  # joint replacement
            "93458",  # cardiac cath
            "97110", "97140", "97161", "97162",  # PT
            "94060",  # spirometry
        },
    },
    "I50": {
        "description": "Heart failure",
        "plausible": {
            "93000", "93005", "93010", "93306", "93458", "93015",  # cardiac
            "80053", "80048", "85025", "85027", "82565", "82947", "83036",  # labs
            "80061", "84443", "85610", "85730", "85379",  # more labs
            "82310", "84132", "84295", "81001", "81003",  # more labs
            "71046", "71048", "76700",  # imaging
            "96360", "96361", "96365", "96374",  # IV
            "94640",  # nebulizer
            "J0290", "J2270", "J1885", "J2550", "J3010",  # meds
            "99281", "99282", "99283", "99284", "99285",  # ED
            "99221", "99222", "99223", "99231", "99232", "99233",  # hospital care
            "99238", "99239", "99291", "99292",  # discharge/critical
        },
        "implausible": {
            "44950", "44970",  # appendectomy
            "27447", "27130",  # joint replacement
            "47562", "47563",  # cholecystectomy
            "97110", "97140", "97161", "97162",  # PT
        },
    },
    "I48": {
        "description": "Atrial fibrillation",
        "plausible": {
            "93000", "93005", "93010", "93306", "93458", "93015",  # cardiac
            "80053", "80048", "85025", "82565", "85610", "85730",  # labs
            "84132", "84295", "82310", "84443",  # labs
            "71046",  # chest xray
            "96360", "96365", "96374",  # IV
            "J0290", "J2270", "J1885",  # meds
            "99281", "99282", "99283", "99284", "99285",  # ED
            "99221", "99222", "99223", "99231", "99232", "99233",  # hospital care
            "99238", "99239",  # discharge
        },
        "implausible": {
            "44950", "44970",  # appendectomy
            "27447", "27130",  # joint replacement
            "47562", "47563",  # cholecystectomy
            "97110", "97140", "97161", "97162",  # PT
        },
    },
    "E11": {
        "description": "Type 2 diabetes mellitus",
        "plausible": {
            "80053", "80048", "85025", "82947", "83036", "80061",  # labs
            "82565", "84443", "82310", "84132", "84295",  # labs
            "81001", "81003",  # UA
            "99211", "99212", "99213", "99214", "99215",  # office visits
            "99221", "99222", "99223", "99231", "99232", "99233",  # hospital care
            "99238", "99239",  # discharge
            "96360", "96365", "96374",  # IV
            "J0290", "J2270", "J1885",  # meds
            "71046",  # chest xray
            "93000",  # ECG
            "76700",  # ultrasound
        },
        "implausible": {
            "44950", "44970",  # appendectomy
            "93458",  # cardiac cath
            "27447", "27130",  # joint replacement
            "47562", "47563",  # cholecystectomy
            "33533",  # CABG
        },
    },
    "M17": {
        "description": "Knee osteoarthritis",
        "plausible": {
            "27447",  # knee replacement
            "01402",  # anesthesia
            "97110", "97140", "97161", "97162",  # PT
            "80053", "80048", "85025", "85610", "85730",  # labs
            "82565", "84132", "84295", "82310",  # labs
            "71046",  # chest xray
            "93000",  # ECG (pre-op)
            "96360", "96361", "96365", "96374",  # IV
            "J0290", "J2270", "J1885", "J2550", "J3010",  # meds
            "99221", "99222", "99223", "99231", "99232", "99233",  # hospital care
            "99238", "99239",  # discharge
            "72148",  # MRI
        },
        "implausible": {
            "44950", "44970",  # appendectomy
            "93458",  # cardiac cath
            "93015",  # cardiac stress test
            "47562", "47563",  # cholecystectomy
            "74177", "74176",  # CT abdomen
            "88305", "88307",  # surgical pathology (not standard for knee)
        },
    },
    "K80": {
        "description": "Gallstones / cholelithiasis",
        "plausible": {
            "47562", "47563",  # cholecystectomy
            "00740",  # anesthesia
            "74177", "74176", "76700",  # imaging
            "80053", "80048", "85025", "82565", "82947",  # labs
            "82310", "84132", "84295",  # labs
            "88305",  # pathology
            "96360", "96365", "96374",  # IV
            "J0290", "J2270", "J1885", "J2550",  # meds
            "99281", "99282", "99283", "99284", "99285",  # ED
            "99221", "99222", "99223", "99231", "99232", "99233",  # hospital care
            "99238", "99239",  # discharge
            "71046",  # chest xray
        },
        "implausible": {
            "27447", "27130",  # joint replacement
            "93458",  # cardiac cath
            "93015",  # cardiac stress test
            "97110", "97140", "97161", "97162",  # PT
            "93306",  # echo
        },
    },
    "I10": {
        "description": "Essential hypertension",
        "plausible": {
            "93000", "93005", "93010", "93306",  # cardiac
            "80053", "80048", "85025", "82565", "82947", "80061",  # labs
            "84132", "84295", "82310", "84443", "83036",  # labs
            "81001", "81003",  # UA
            "71046",  # chest xray
            "99211", "99212", "99213", "99214", "99215",  # office visits
            "99221", "99222", "99223", "99231", "99232", "99233",  # hospital care
            "99238", "99239",  # discharge
            "96360", "96365", "96374",  # IV
            "J0290", "J2270", "J1885",  # meds
        },
        "implausible": set(),
    },
}


# Back-compat alias — comparator.py now uses build_live_fee_schedule()
CMS_FEE_SCHEDULE = CMS_FEE_SCHEDULE_FALLBACK

CMS_OVERCHARGE_MULTIPLIER = 15.0
CMS_SEVERE_OVERCHARGE_MULTIPLIER = 25.0
