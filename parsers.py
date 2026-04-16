"""
parsers.py — Tested against actual Udyam & GST Registration Certificate PDFs
Every pattern verified on real government-issued documents.
"""
import re

# ── Value normalisers ─────────────────────────────────────────────────────────
CONSTITUTION_MAP = {
    "partnership firm":"Partnership Firm","partnership":"Partnership Firm",
    "private limited company":"Private Limited Company","private limited":"Private Limited Company",
    "pvt ltd":"Private Limited Company","pvt. ltd":"Private Limited Company",
    "public limited company":"Public Limited Company","public limited":"Public Limited Company",
    "proprietorship concern":"Proprietorship Concern","proprietorship":"Proprietorship Concern",
    "sole proprietorship":"Proprietorship Concern","proprietor":"Proprietorship Concern",
    "individual":"Individual","huf":"HUF","hindu undivided family":"HUF",
    "llp":"LLP","limited liability partnership":"LLP",
    "trust":"Trust","aop":"AOP/BOI","boi":"AOP/BOI","aop/boi":"AOP/BOI",
    "joint":"Joint","government":"Government","others":"Others",
}
STATE_MAP = {
    "andhra pradesh":"Andhra Pradesh","arunachal pradesh":"Arunachal Pradesh",
    "assam":"Assam","bihar":"Bihar","chhattisgarh":"Chhattisgarh","goa":"Goa",
    "gujarat":"Gujarat","haryana":"Haryana","himachal pradesh":"Himachal Pradesh",
    "hp":"Himachal Pradesh","jharkhand":"Jharkhand","karnataka":"Karnataka",
    "kerala":"Kerala","madhya pradesh":"Madhya Pradesh","mp":"Madhya Pradesh",
    "maharashtra":"Maharashtra","manipur":"Manipur","meghalaya":"Meghalaya",
    "mizoram":"Mizoram","nagaland":"Nagaland","odisha":"Odisha","orissa":"Odisha",
    "punjab":"Punjab","rajasthan":"Rajasthan","sikkim":"Sikkim",
    "tamil nadu":"Tamil Nadu","tn":"Tamil Nadu","telangana":"Telangana",
    "tripura":"Tripura","uttar pradesh":"Uttar Pradesh","up":"Uttar Pradesh",
    "uttarakhand":"Uttarakhand","uttaranchal":"Uttarakhand",
    "west bengal":"West Bengal","wb":"West Bengal",
    "delhi":"Delhi","new delhi":"Delhi","nct of delhi":"Delhi","nct delhi":"Delhi",
    "jammu & kashmir":"Jammu & Kashmir","jammu and kashmir":"Jammu & Kashmir","j&k":"Jammu & Kashmir",
    "ladakh":"Ladakh","chandigarh":"Chandigarh",
    "puducherry":"Puducherry","pondicherry":"Puducherry",
    "daman & diu":"Daman & Diu","dadra & nagar haveli":"Dadra & Nagar Haveli",
    "andaman & nicobar":"Andaman & Nicobar","lakshadweep":"Lakshadweep",
}

def norm_constitution(raw):
    if not raw: return ""
    clean = re.sub(r'^(?:Type\s*of\s*(?:Organisation|Enterprise|Business)\s*[:\-]?\s*|Organisation\s*Type\s*[:\-]?\s*|Constitution\s*of\s*Business\s*[:\-]?\s*)', '', raw, flags=re.I)
    clean = clean.strip().rstrip('.,;:')
    key = clean.lower().strip()
    if key in CONSTITUTION_MAP: return CONSTITUTION_MAP[key]
    for k,v in CONSTITUTION_MAP.items():
        if k in key or key.startswith(k): return v
    return ""

def norm_state(raw):
    if not raw: return ""
    clean = raw.strip().rstrip('.,;:\n\r')
    key = clean.lower().strip()
    if key in STATE_MAP: return STATE_MAP[key]
    for k,v in STATE_MAP.items():
        if key.startswith(k): return v
    try:
        from validators import INDIAN_STATES
        title = clean.title()
        if title in INDIAN_STATES: return title
    except: pass
    return ""

def norm_date(raw):
    if not raw: return ""
    raw = raw.strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw): return raw
    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    m = re.match(r'^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})$', raw)
    if m: d,mo,y = m.groups(); return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
    m = re.match(r'^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2})$', raw)
    if m: d,mo,y = m.groups(); yr = f"20{y}" if int(y)<50 else f"19{y}"; return f"{yr}-{mo.zfill(2)}-{d.zfill(2)}"
    return raw

def norm_mobile(raw):
    m = re.sub(r'[\s\-\(\)\+]', '', raw)
    if m.startswith("91") and len(m)==12: m = m[2:]
    return m if re.match(r'^[6-9]\d{9}$', m) else ""

def norm_msme(raw):
    return {"micro":"Micro","small":"Small","medium":"Medium"}.get(raw.strip().lower(), "")

def extract_text_from_upload(uploaded_file) -> str:
    text = ""
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t: text += t + "\n"
        except Exception as e: text = f"[PDF read error: {e}]"
    else:
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(uploaded_file)
            text = pytesseract.image_to_string(img, lang="eng")
        except Exception as e: text = f"[Image OCR error: {e}]"
    return text.strip()

# ── Udyam address builder ─────────────────────────────────────────────────────
def _build_udyam_address(text):
    parts = []
    # Door / plot number (stop before "Gf" which is ground floor tag, not part of address)
    door = re.search(r'((?:Sco|SCO|Plot|H\.?\s*No\.?|Shop\s*No\.?|House\s*No\.?|Flat\s*No\.?)\s*[\-\d]+)', text, re.I)
    if door: parts.append(door.group(1).strip().rstrip(','))
    # Premises / building name (Sector, Colony etc.)
    sector = re.search(r'(Sector\s*-?\s*\d+)', text, re.I)
    if sector: parts.append(sector.group(1).strip())
    # City
    city = re.search(r'City\s+([A-Za-z]+)', text)
    if city: parts.append(city.group(1).strip())
    # State
    state = re.search(r'State\s+([A-Z]{3,})', text)
    if state: parts.append(state.group(1).title())
    # PIN - appears on its own line after "Pin"
    pin = re.search(r'(?:,\s*Pin\s*\n|Pin\s*\n)(\d{6})', text)
    if not pin: pin = re.search(r'\n(\d{6})\n', text, re.MULTILINE)
    if pin: parts.append(pin.group(1))

    address = ', '.join(p for p in parts if p)
    return address

# ── Main Udyam parser — tested on real certificate ────────────────────────────
def parse_udyam(text: str) -> dict:
    data = {}

    # 1. Udyam Registration Number
    m = re.search(r'UDYAM REGISTRATION NUMBER\s+(UDYAM-[A-Z]{2}-\d{2}-\d{7})', text)
    if m: data["udyam_no"] = m.group(1).strip()

    # 2. Enterprise Name
    m = re.search(r'NAME OF ENTERPRISE\s+(.+)', text)
    if m: data["enterprise_name"] = m.group(1).strip()

    # 3. MSME Category — from the classification table, first entry
    # Format: "1  2023-24  Micro  09/05/2023"
    m = re.search(r'(?:^|\n)\d+\s+\d{4}-\d{2}\s+(Micro|Small|Medium)\s+', text, re.MULTILINE | re.IGNORECASE)
    if m: data["msme_category"] = m.group(1).strip()

    # 4. Major Activity (SERVICES / MANUFACTURING / TRADING)
    m = re.search(r'MAJOR ACTIVITY\s+(\S+)', text)
    if m: data["major_activity"] = m.group(1).strip()

    # 5. State — "State HARYANA District"
    m = re.search(r'State\s+([A-Z]{3,})\s+District', text)
    if m: data["state"] = norm_state(m.group(1).strip())

    # 6. Mobile
    m = re.search(r'Mobile\s+(\d{10})', text)
    if m: data["mobile"] = norm_mobile(m.group(1))

    # 7. Email
    m = re.search(r'Email:\s*([\w\.\+\-]+@[\w\.\-]+\.\w+)', text)
    if m: data["email"] = m.group(1).strip()

    # 8. Date of Incorporation — label splits across 2 lines, date on 3rd
    # "DATE OF INCORPORATION /\nREGISTRATION OF ENTERPRISE\n01/07/2017"
    m = re.search(r'DATE OF INCORPORATION[^\n]*\n(?:[^\n]*\n)?(\d{2}/\d{2}/\d{4})', text)
    if m: data["date_of_establishment"] = norm_date(m.group(1))

    # 9. NIC Code — first column "1  47 - Retail trade..."
    m = re.search(r'(?:^|\n)1\s+(\d{2})\s+-\s+', text, re.MULTILINE)
    if m: data["nic_code"] = m.group(1).strip()

    # 10. Activity from NIC description
    m = re.search(r'(?:^|\n)1\s+\d{2}\s+-\s+([^\n,]+)', text, re.MULTILINE)
    if m: data["activity_existing"] = m.group(1).strip()

    # 11. Address — build from components
    address = _build_udyam_address(text)
    if address: data["regd_office_address"] = address

    # 12. PIN code
    pin = re.search(r'(?:,\s*Pin\s*\n|Pin\s*\n)(\d{6})', text)
    if not pin: pin = re.search(r'\n(\d{6})\n', text)
    # (already incorporated in address above)

    # 13. Date of Udyam Registration (as registration date)
    m = re.search(r'DATE OF UDYAM REGISTRATION\s+(\d{2}/\d{2}/\d{4})', text)
    if m and not data.get("date_of_establishment"):
        data["date_of_establishment"] = norm_date(m.group(1))

    # Normalise dropdown fields
    if data.get("state") and not data["state"].startswith("norm"):
        pass  # already normalised above via norm_state()
    if data.get("msme_category"):
        data["msme_category"] = norm_msme(data["msme_category"])
    if data.get("date_of_establishment"):
        data["date_of_establishment"] = norm_date(data["date_of_establishment"])

    # Remove empty
    return {k: v for k, v in data.items() if v and str(v).strip()}

# ── Main GST parser — tested on real certificate ──────────────────────────────
def parse_gst(text: str) -> dict:
    data = {}

    # 1. GSTIN — "Registration Number :06AALFN8058Q1ZD"
    m = re.search(r'Registration Number\s*:?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])', text)
    if m: data["gst_no"] = m.group(1).strip()
    # Also catch plain GSTIN in Annexure A/B
    if not data.get("gst_no"):
        m = re.search(r'GSTIN\s+([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])', text)
        if m: data["gst_no"] = m.group(1).strip()

    # 2. Enterprise Name — "1. Legal Name   NARULA & SONS"
    m = re.search(r'1\.\s+Legal Name\s+(.+)', text)
    if m: data["enterprise_name"] = m.group(1).strip()

    # 3. Constitution — "3. Constitution of Business   Partnership"
    m = re.search(r'3\.\s+Constitution of Business\s+(.+)', text)
    if m: data["constitution"] = norm_constitution(m.group(1).strip())

    # 4. Address — "4. Address of Principal Place of   <addr>\nBusiness  <continued>"
    # The word "Business" appears at the start of the continuation line
    m = re.search(r'4\.\s+Address of Principal Place of\s+(.+(?:\n.+)?)\n5\.', text, re.DOTALL)
    if m:
        raw_addr = m.group(1)
        # Remove the "Business" continuation label that pdfplumber includes
        clean = re.sub(r'\nBusiness\s+', ', ', raw_addr)
        clean = re.sub(r',\s*,', ',', clean)          # remove double commas
        clean = re.sub(r'\s+', ' ', clean).strip().rstrip(',')
        data["regd_office_address"] = clean

    # 5. GST Date of Liability — "5. Date of Liability   01/07/2017"
    m = re.search(r'5\.\s+Date of Liability\s+(\d{2}/\d{2}/\d{4})', text)
    if m: data["gst_date"] = norm_date(m.group(1))

    # 6. Date of issue — "9. Date of issue of Certificate   09/04/2019"
    m = re.search(r'9\.\s+Date of issue of Certificate\s+(\d{2}/\d{2}/\d{4})', text)
    if m and not data.get("gst_date"):
        data["gst_date"] = norm_date(m.group(1))

    # 7. Partners from Annexure B — "1 Name   NIVESH NARULA"
    partners = re.findall(r'(?:^|\n)\d+\s+Name\s+([A-Z][A-Z\s]+)\nDesignation/Status\s+(\w+)', text, re.MULTILINE)
    if partners:
        data["_partners"] = [{"name": p[0].strip(), "designation": p[1].strip()} for p in partners]

    # 8. Auto-extract PAN and State from GSTIN
    gstin = data.get("gst_no", "")
    if gstin and len(gstin) >= 12:
        data["pan"] = gstin[2:12]
        from validators import GSTIN_STATE, constitution_from_pan
        state_code = gstin[:2]
        if state_code in GSTIN_STATE:
            data["state"] = GSTIN_STATE[state_code]
        # Constitution from PAN 4th char (if not already from cert)
        if not data.get("constitution"):
            data["constitution"] = constitution_from_pan(data["pan"])

    # Normalise
    if data.get("gst_date"):
        data["gst_date"] = norm_date(data["gst_date"])

    return {k: v for k, v in data.items() if v and str(v).strip()}

# ── PAN card parser ───────────────────────────────────────────────────────────
def parse_pan_card(text: str) -> dict:
    data = {}
    m = re.search(r'\b([A-Z]{5}\d{4}[A-Z])\b', text)
    if m: data["pan"] = m.group(1)
    m = re.search(r'(?:Name|नाम)[:\s]*\n?\s*([A-Z][A-Z\s\.]{3,60})', text, re.IGNORECASE)
    if m: data["enterprise_name"] = m.group(1).strip()
    m = re.search(r'(?:Date\s*of\s*Birth|DOB|जन्म)[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', text, re.IGNORECASE)
    if m: data["dob"] = norm_date(m.group(1))
    m = re.search(r"(?:Father'?s?\s*Name|पिता)[:\s]*\n?\s*([A-Z][A-Z\s\.]{3,60})", text, re.IGNORECASE)
    if m: data["father_name"] = m.group(1).strip()
    return data
