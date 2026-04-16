"""validators.py v3"""
import re

GSTIN_STATE = {
    "01":"Jammu & Kashmir","02":"Himachal Pradesh","03":"Punjab","04":"Chandigarh",
    "05":"Uttarakhand","06":"Haryana","07":"Delhi","08":"Rajasthan","09":"Uttar Pradesh",
    "10":"Bihar","11":"Sikkim","12":"Arunachal Pradesh","13":"Nagaland","14":"Manipur",
    "15":"Mizoram","16":"Tripura","17":"Meghalaya","18":"Assam","19":"West Bengal",
    "20":"Jharkhand","21":"Odisha","22":"Chhattisgarh","23":"Madhya Pradesh",
    "24":"Gujarat","25":"Daman & Diu","26":"Dadra & Nagar Haveli","27":"Maharashtra",
    "28":"Andhra Pradesh","29":"Karnataka","30":"Goa","31":"Lakshadweep",
    "32":"Kerala","33":"Tamil Nadu","34":"Puducherry","35":"Andaman & Nicobar",
    "36":"Telangana","37":"Andhra Pradesh (New)","38":"Ladakh","97":"Other Territory",
}

INDIAN_STATES = [
    "", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu & Kashmir", "Ladakh", "Chandigarh", "Puducherry",
    "Daman & Diu", "Dadra & Nagar Haveli", "Andaman & Nicobar",
    "Lakshadweep", "Other Territory",
]

CONSTITUTIONS = [
    "", "Individual", "Joint", "Proprietorship Concern", "Partnership Firm",
    "Private Limited Company", "Public Limited Company", "LLP", "Trust", "HUF",
    "AOP/BOI", "Government", "Others",
]

PERSON_LABEL = {
    "Individual": "Applicant", "Joint": "Joint Applicant",
    "Proprietorship Concern": "Proprietor", "Partnership Firm": "Partner",
    "Private Limited Company": "Director", "Public Limited Company": "Director",
    "LLP": "Designated Partner", "Trust": "Trustee", "HUF": "Karta",
    "AOP/BOI": "Member", "Government": "Authorised Signatory",
    "Others": "Authorised Person", "": "Director / Partner",
}
PERSON_LABEL_PLURAL = {
    "Individual": "Applicants", "Joint": "Joint Applicants",
    "Proprietorship Concern": "Proprietors", "Partnership Firm": "Partners",
    "Private Limited Company": "Directors", "Public Limited Company": "Directors",
    "LLP": "Designated Partners", "Trust": "Trustees", "HUF": "Kartas",
    "AOP/BOI": "Members", "Government": "Authorised Signatories",
    "Others": "Authorised Persons", "": "Directors / Partners",
}

def get_person_label(constitution: str) -> str:
    return PERSON_LABEL.get(constitution, "Director / Partner")

def get_person_label_plural(constitution: str) -> str:
    return PERSON_LABEL_PLURAL.get(constitution, "Directors / Partners")

NIC_DESCRIPTIONS = {
    "01":"Crop and animal production, hunting","02":"Forestry and logging",
    "03":"Fishing and aquaculture","05":"Mining of coal and lignite",
    "06":"Extraction of crude petroleum and natural gas",
    "10":"Manufacture of food products","11":"Manufacture of beverages",
    "12":"Manufacture of tobacco products","13":"Manufacture of textiles",
    "14":"Manufacture of wearing apparel","15":"Manufacture of leather products",
    "16":"Manufacture of wood and cork products","17":"Manufacture of paper products",
    "18":"Printing and reproduction of recorded media",
    "19":"Manufacture of coke and refined petroleum products",
    "20":"Manufacture of chemicals and chemical products",
    "21":"Manufacture of pharmaceuticals, medicinal chemical",
    "22":"Manufacture of rubber and plastics products",
    "23":"Manufacture of other non-metallic mineral products",
    "24":"Manufacture of basic metals","25":"Manufacture of fabricated metal products",
    "26":"Manufacture of computer, electronic and optical products",
    "27":"Manufacture of electrical equipment",
    "28":"Manufacture of machinery and equipment n.e.c.",
    "29":"Manufacture of motor vehicles, trailers",
    "30":"Manufacture of other transport equipment",
    "31":"Manufacture of furniture","32":"Other manufacturing",
    "33":"Repair and installation of machinery and equipment",
    "35":"Electricity, gas, steam and air conditioning supply",
    "36":"Water collection, treatment and supply","37":"Sewerage",
    "38":"Waste collection, treatment and disposal",
    "41":"Construction of buildings","42":"Civil engineering",
    "43":"Specialised construction activities",
    "45":"Wholesale and retail trade/repair of motor vehicles",
    "46":"Wholesale trade (except motor vehicles)","47":"Retail trade",
    "49":"Land transport and transport via pipelines","50":"Water transport",
    "51":"Air transport","52":"Warehousing and support for transportation",
    "53":"Postal and courier activities","55":"Accommodation",
    "56":"Food and beverage service activities","58":"Publishing activities",
    "61":"Telecommunications","62":"Computer programming, consultancy and IT",
    "63":"Information service activities","64":"Financial service activities",
    "65":"Insurance, reinsurance and pension funding",
    "66":"Activities auxiliary to financial services",
    "68":"Real estate activities","69":"Legal and accounting activities",
    "70":"Management consultancy activities",
    "71":"Architectural and engineering activities",
    "72":"Scientific research and development",
    "73":"Advertising and market research","74":"Other professional activities",
    "75":"Veterinary activities","77":"Rental and leasing activities",
    "78":"Employment activities","79":"Travel agency, tour operator",
    "80":"Security and investigation activities",
    "85":"Education","86":"Human health activities",
    "95":"Repair of computers and personal household goods",
    "96":"Other personal service activities",
}

def nic_to_activity(nic_code: str) -> str:
    if not nic_code:
        return ""
    code = nic_code.strip()
    if code in NIC_DESCRIPTIONS:
        return NIC_DESCRIPTIONS[code]
    if len(code) >= 2 and code[:2] in NIC_DESCRIPTIONS:
        return NIC_DESCRIPTIONS[code[:2]]
    return ""

def validate_pan(pan: str):
    pan = pan.upper().strip()
    if not pan: return None, ""
    if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan):
        return False, "PAN: 5 letters + 4 digits + 1 letter (e.g. ABCDE1234F)"
    return True, "✅ Valid PAN"

def validate_gstin(gstin: str):
    gstin = gstin.upper().strip()
    if not gstin: return None, "", {}
    if not re.match(r'^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$', gstin):
        return False, "Invalid GSTIN (15 chars, e.g. 07ABCDE1234F1Z5)", {}
    pan = gstin[2:12]
    extracted = {
        "pan": pan,
        "state": GSTIN_STATE.get(gstin[:2], ""),
        "constitution": constitution_from_pan(pan),
    }
    return True, f"✅ Valid — State: {extracted['state']}", extracted

def validate_udyam(udyam: str):
    udyam = udyam.upper().strip()
    if not udyam: return None, ""
    if not re.match(r'^UDYAM-[A-Z]{2}-\d{2}-\d{7}$', udyam):
        return False, "Format: UDYAM-XX-00-0000000"
    return True, "✅ Valid Udyam No."

def validate_mobile(mobile: str):
    m = re.sub(r'[\s\-\+]', '', mobile)
    if not m: return None, ""
    if m.startswith("91") and len(m) == 12: m = m[2:]
    if not re.match(r'^[6-9]\d{9}$', m):
        return False, "10-digit mobile, starts with 6-9"
    return True, "✅ Valid"

def validate_email(email: str):
    if not email: return None, ""
    if not re.match(r'^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$', email):
        return False, "Enter valid email"
    return True, "✅ Valid"

def validate_aadhar(aadhar: str):
    a = re.sub(r'\D', '', aadhar)
    if not a: return None, ""
    if not re.match(r'^\d{12}$', a): return False, "Aadhar must be 12 digits"
    if a[0] in "01": return False, "Cannot start with 0 or 1"
    return True, "✅ Valid"

def pan_from_gstin(gstin: str) -> str:
    gstin = gstin.upper().strip()
    if len(gstin) >= 12 and re.match(r'^\d{2}[A-Z]{5}\d{4}[A-Z]', gstin):
        return gstin[2:12]
    return ""

def state_from_gstin(gstin: str) -> str:
    gstin = gstin.upper().strip()
    return GSTIN_STATE.get(gstin[:2], "") if len(gstin) >= 2 else ""

def constitution_from_pan(pan: str) -> str:
    pan = pan.upper().strip()
    if len(pan) < 4: return ""
    return {
        "P":"Proprietorship Concern","F":"Partnership Firm",
        "C":"Private Limited Company","H":"HUF","A":"AOP/BOI",
        "T":"Trust","B":"Public Limited Company","L":"LLP",
        "J":"Artificial Juridical Person","G":"Government",
    }.get(pan[3], "")
