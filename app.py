"""
MSME Loan Application Portal v4
- Auto-parse on upload (no button click needed)
- PAN + Aadhaar upload per director with inline parsing
- No nested expanders (machine table fix)
- Unique widget keys throughout
- Constitution/State auto-fill from GSTIN
- NIC → Activity auto-fill
- All fields consistent with person label
"""
import streamlit as st
import json, os, re, io, base64
from datetime import datetime, date
from PIL import Image

st.set_page_config(
    page_title="MSME Loan Portal — Bharat Bank of india",
    page_icon="🏦", layout="wide",
    initial_sidebar_state="collapsed",
)

# Scroll to top on navigation
st.markdown("""
<script>
try { window.parent.document.querySelector('section.main').scrollTop = 0; } catch(e){}
</script>
""", unsafe_allow_html=True)

def load_css():
    p = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(p):
        with open(p) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()

from validators import (
    validate_pan, validate_gstin, validate_udyam, validate_mobile,
    validate_email, validate_aadhar, pan_from_gstin, state_from_gstin,
    constitution_from_pan, INDIAN_STATES, CONSTITUTIONS,
    get_person_label, get_person_label_plural, nic_to_activity,
)
from parsers import extract_text_from_upload, parse_udyam, parse_gst, parse_pan_card

COLLATERAL_NATURE = [
    "", "Immovable Property (Residential)", "Immovable Property (Commercial)",
    "Immovable Property (Industrial/Land)", "Fixed Deposit (FD)", "NSC/KVP",
    "Life Insurance Policy (LIC)", "Shares / Mutual Funds",
    "Gold / Jewellery", "Machinery & Equipment", "Vehicle", "Others",
]

STEPS = [
    ("🚀","Start"), ("🏢","Enterprise"), ("👥","People"),
    ("💳","Banking"), ("💰","Loan"), ("🔒","Security"),
    ("📊","Financials"), ("📸","Photos"), ("✅","Submit"),
]

STEP_REQUIRED = {
    1: ["enterprise_name","pan","udyam_no","gst_no","mobile","constitution","state","regd_office_address","city_loan"],
    8: ["declaration_agreed","cibil_consent"],
}

# ── State init ────────────────────────────────────────────────────────────────
def make_director():
    return {"name":"","dob":None,"father_spouse":"","qualification":"",
            "category":"","mobile":"","pan":"","address":"",
            "aadhar_din":"","telephone":"","experience":"","designation":""}

def make_facility(t):
    return {"type":t,"limit":"","outstanding":"","banking_with":"","securities":"","roi":"","repayment":""}

def make_proposed(t):
    return {"type":t,"amount":"","purpose":"","primary_security":"","collateral_offered":"No"}

def make_guarantor(name="",mobile="",address="",pan="",relationship=""):
    return {"name":name,"father_spouse":"","address":address,"telephone":"",
            "mobile":mobile,"net_worth":"","aadhar":"","pan":pan,"relationship":relationship}

def make_machine():
    return {"machine":"","purpose":"","imported":"Indigenous","supplier":"",
            "total_cost":"","contribution":"","loan_req":"","second_hand":False,"residual_life":""}

def init():
    D = {
        "step":0,
        "enterprise_name":"","regd_office_address":"","factory_address":"",
        "factory_same_as_regd":False,
        "date_of_establishment":None,"state":"","premises_type":"Owned",
        "premises_details":"","telephone":"","mobile":"","email":"",
        "pan":"","constitution":"","website":"","num_employees":"",
        "udyam_no":"","gst_no":"","gst_date":None,
        "gem_registered":"No","gem_no":"","iec_code":"",
        "city_loan":"","branch_loan":"",
        "msme_category":"","nic_code":"",
        "activity_existing":"","activity_proposed":"",
        "zed_rated":"No","zed_grade":"",
        "directors":[make_director()],
        "associate_concerns":[],
        "bank_relationship":"No","bank_relationship_details":"",
        "existing_facilities":[make_facility(t) for t in ["Current Account","Cash Credit","Term Loan","LC/BG","Others"]],
        "cif_no":"",
        "proposed_facilities":[make_proposed(t) for t in ["Cash Credit","Term Loan","LC/BG","Others"]],
        "machinery_details":[],
        "collateral_guarantors":[],
        "collateral_others":[],
        "performance_data":{k:"" for k in [
            "past2_sales","past2_profit","past2_capital",
            "past1_sales","past1_profit","past1_capital",
            "current_sales","current_profit","current_capital",
            "next_sales","next_profit","next_capital",
        ]},
        "turnover_last_year":"","investment_plant":"",
        "top_suppliers":[{"name":"","contact":"","since":"","pct":"","terms":""} for _ in range(5)],
        "top_customers":[{"name":"","contact":"","since":"","pct":"","terms":""} for _ in range(5)],
        "statutory":{k:"" for k in ["shops_act","msme_reg","drug_license","sales_tax","income_tax","other_dues"]},
        "photos":{},
        "autofilled_fields":set(),
        "declaration_agreed":False,"cibil_consent":False,"cibil_equifax_consent":False,
        "application_id":f"UBI-MSME-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "udyam_parsed":False,"gst_parsed":False,
        # track file hashes to avoid re-parsing
        "_last_udyam_hash":"","_last_gst_hash":"",
    }
    for k,v in D.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()
ss = st.session_state

# ── Nav helpers ────────────────────────────────────────────────────────────────
def go(n): ss.step=n; st.rerun()
def next_s(): go(min(ss.step+1,len(STEPS)-1))
def prev_s(): go(max(ss.step-1,0))

def step_complete(i):
    for f in STEP_REQUIRED.get(i,[]):
        v = ss.get(f,"")
        if not v or str(v).strip() in ["","None","False"]: return False
    return True

# ── Auto-fill helpers ─────────────────────────────────────────────────────────
def mark_af(*fields):
    if not isinstance(ss.autofilled_fields,set): ss.autofilled_fields=set()
    for f in fields: ss.autofilled_fields.add(f)

def is_af(field):
    return field in (ss.autofilled_fields if isinstance(ss.autofilled_fields,set) else set())

def af_label(label,field):
    return f"⚡ {label}" if is_af(field) else label

def apply_gst_autofill(gstin):
    filled=[]
    ok,_,ext = validate_gstin(gstin)
    if not ok: return filled
    if ext.get("pan") and not ss.pan:
        ss.pan=ext["pan"]; mark_af("pan"); filled.append("PAN")
    if ext.get("state") and not ss.state:
        ss.state=ext["state"]
        ss["sel_state"]=ext["state"]   # write widget key
        mark_af("state"); filled.append("State")
    if ext.get("constitution") and not ss.constitution:
        ss.constitution=ext["constitution"]
        ss["sel_const"]=ext["constitution"]  # write widget key
        mark_af("constitution"); filled.append("Constitution")
    return filled

def apply_parsed_to_ss(data:dict):
    # Mapping: parsed key → (session_state field, widget_key_if_dropdown)
    field_map = {
        "enterprise_name":       ("enterprise_name",       None),
        "udyam_no":              ("udyam_no",              None),
        "gst_no":                ("gst_no",                None),
        "gst_date":              ("gst_date",              None),
        "pan":                   ("pan",                   None),
        "mobile":                ("mobile",                None),
        "email":                 ("email",                 None),
        "telephone":             ("telephone",             None),
        "num_employees":         ("num_employees",         None),
        "nic_code":              ("nic_code",              None),
        "activity_existing":     ("activity_existing",     None),
        "major_activity":        ("activity_existing",     None),  # fallback
        "regd_office_address":   ("regd_office_address",   None),
        "factory_address":       ("regd_office_address",   None),
        "date_of_establishment": ("date_of_establishment", None),
        # Dropdowns — must write to BOTH ss.field AND ss['widget_key']
        "state":                 ("state",        "sel_state"),
        "constitution":          ("constitution", "sel_const"),
        "msme_category":         ("msme_category","sel_msme"),
    }
    n=0
    for src,(dest,widget_key) in field_map.items():
        val=str(data.get(src,"")).strip()
        if val and not ss.get(dest,""):
            ss[dest]=val
            mark_af(dest)
            if widget_key:
                ss[widget_key]=val
            n+=1

    # NIC → activity description (if activity_existing still empty after mapping)
    if data.get("nic_code") and not ss.activity_existing:
        act=nic_to_activity(data["nic_code"])
        if act: ss.activity_existing=act; mark_af("activity_existing"); n+=1

    # Auto-populate partners/directors from GST Annexure B
    partners = data.get("_partners", [])
    if partners:
        existing_names = {d.get("name","").upper() for d in ss.directors if d.get("name")}
        for p in partners:
            pname = p.get("name","").strip()
            if pname and pname.upper() not in existing_names:
                new_dir = make_director()
                new_dir["name"] = pname.title()
                new_dir["designation"] = p.get("designation","").title()
                # If first director slot is empty, fill it; else append
                if ss.directors and not ss.directors[0].get("name"):
                    ss.directors[0] = new_dir
                else:
                    ss.directors.append(new_dir)
                existing_names.add(pname.upper())
                n += 1

    # GSTIN → PAN+State+Constitution (with widget key writes)
    if ss.gst_no:
        extras=apply_gst_autofill(ss.gst_no)
        n+=len(extras)
    return n

def parse_director_pan(text:str, d:dict):
    """Extract PAN, name from PAN card text and fill director dict."""
    from parsers import parse_pan_card
    data = parse_pan_card(text)
    filled = []
    if data.get("pan") and not d.get("pan"):
        d["pan"] = data["pan"]; filled.append("PAN")
    if data.get("enterprise_name") and not d.get("name"):
        d["name"] = data["enterprise_name"]; filled.append("Name")
    if data.get("dob") and not d.get("dob"):
        d["dob"] = data["dob"]; filled.append("DOB")
    if data.get("father_name") and not d.get("father_spouse"):
        d["father_spouse"] = data["father_name"]; filled.append("Father's Name")
    return filled

def parse_director_aadhar(text:str, d:dict):
    """Extract name, DOB from Aadhaar text and fill director dict."""
    filled = []
    name_m = re.search(r'(?:^|\n)([A-Z][A-Za-z\s]{2,40})(?:\n|$)', text)
    if name_m and not d.get("name"):
        d["name"] = name_m.group(1).strip(); filled.append("Name")
    dob_m = re.search(r'(?:DOB|Date\s*of\s*Birth|जन्म)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', text, re.I)
    if dob_m and not d.get("dob"):
        d["dob"] = dob_m.group(1); filled.append("DOB")
    aadhar_m = re.search(r'\b(\d{4}\s\d{4}\s\d{4})\b', text)
    if aadhar_m and not d.get("aadhar_din"):
        d["aadhar_din"] = aadhar_m.group(1).replace(" ",""); filled.append("Aadhaar No.")
    addr_m = re.search(r'(?:Address|पता)[:\s]*([^\n]{10,}(?:\n[^\n]{5,}){0,3})', text, re.I)
    if addr_m and not d.get("address"):
        d["address"] = addr_m.group(1).strip(); filled.append("Address")
    return filled

# ── Widget helpers ────────────────────────────────────────────────────────────
def val_badge(ok,msg):
    if ok is True:  st.markdown(f'<div class="val-ok">✅ {msg}</div>', unsafe_allow_html=True)
    elif ok is False: st.markdown(f'<div class="val-err">⚠️ {msg}</div>', unsafe_allow_html=True)

def af_pill(msg):
    st.markdown(f'<div class="autofill-pill">⚡ {msg}</div>', unsafe_allow_html=True)

def img_to_b64(pil_img):
    buf=io.BytesIO(); pil_img.save(buf,format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def loan_total():
    t=0
    for f in ss.proposed_facilities:
        try: t+=float(f["amount"])
        except: pass
    return t

def save_draft():
    skip={"photos","autofilled_fields"}
    data={k:ss[k] for k in ss if not k.startswith("_") and k not in skip and not callable(ss.get(k))}
    p=os.path.join(os.path.dirname(__file__),f"draft_{ss.application_id}.json")
    with open(p,"w") as f: json.dump(data,f,default=str,indent=2)
    return p

def auto_populate_guarantors():
    label=get_person_label(ss.constitution)
    existing={g["name"] for g in ss.collateral_guarantors}
    for d in ss.directors:
        if d.get("name") and d["name"] not in existing:
            ss.collateral_guarantors.append(make_guarantor(
                name=d.get("name",""),mobile=d.get("mobile",""),
                address=d.get("address",""),pan=d.get("pan",""),relationship=label,
            ))
            existing.add(d["name"])

def file_hash(f):
    if f is None: return ""
    return f"{f.name}_{f.size}"

# ── Top Navigation ────────────────────────────────────────────────────────────
nav_html='<div class="top-nav-outer"><div class="top-nav-inner">'
for i,(icon,name) in enumerate(STEPS):
    curr=i==ss.step
    done=i<ss.step and step_complete(i)
    inc=i<ss.step and not step_complete(i)
    cls="active" if curr else ("done" if done else ("incomplete" if inc else ""))
    num="✓" if done else str(i+1)
    nav_html+=f'<span class="tnav-pill {cls}"><span class="tnav-num">{num}</span>{icon} {name}</span>'
    if i<len(STEPS)-1: nav_html+='<span class="tnav-sep">›</span>'
nav_html+='</div></div>'
st.markdown(nav_html,unsafe_allow_html=True)
st.markdown('<div class="nav-scroll-hint">← Swipe for more steps →</div>',unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div style="color:#fff;font-weight:700;padding:5px 0;">🏦 UBI MSME Portal</div>',unsafe_allow_html=True)
    pct=int(ss.step/(len(STEPS)-1)*100)
    st.progress(pct/100)
    st.markdown(f'<div style="color:#aac;font-size:0.68rem;margin:3px 0;">Step {ss.step+1} of {len(STEPS)} · {pct}%</div>',unsafe_allow_html=True)
    st.markdown("---")
    for i,(icon,name) in enumerate(STEPS):
        d_s="✅" if (i<ss.step and step_complete(i)) else ("⚠" if (i<ss.step and not step_complete(i)) else ("▶" if i==ss.step else "○"))
        if st.button(f"{d_s} {icon} {name}",key=f"sb_{i}",use_container_width=True): go(i)
    st.markdown("---")
    if st.button("💾 Save Draft",key="sidebar_save",use_container_width=True):
        save_draft(); st.success("Saved!")
    st.markdown(f'<div style="font-size:0.6rem;color:#607d9f;">{ss.application_id}</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# STEP 0 — START & AUTO-PARSE DOCUMENT UPLOAD
# ════════════════════════════════════════════════════════════════════════════
if ss.step==0:
    st.markdown(f"""
    <div class="hero-wrap">
      <div style="display:flex;align-items:flex-start;gap:16px;flex-wrap:wrap;">
        <div style="flex:1;min-width:230px;">
          <div class="hero-bank">🏦 Bharat Bank of India</div>
          <div class="hero-tag">MSME Credit Portal · Digital Application Form</div>
          <div class="hero-title">MSME Loan Application</div>
          <div class="hero-sub">Upload your registration certificates — fields fill automatically. Or skip and fill manually throughout.</div>
          <div class="hero-chips">
            <span class="hero-chip gold">⚡ Instant Auto-Fill</span>
            <span class="hero-chip">🔒 Data Stays on Device</span>
            <span class="hero-chip">📱 Mobile Friendly</span>
            <span class="hero-chip">🖨 Printable PDF</span>
          </div>
        </div>
        <div style="background:rgba(255,255,255,0.09);border-radius:11px;padding:12px 16px;border:1px solid rgba(255,255,255,0.14);min-width:180px;">
          <div style="font-size:0.62rem;color:rgba(255,255,255,0.48);text-transform:uppercase;letter-spacing:1px;margin-bottom:7px;">Application</div>
          <div style="color:#fff;font-size:0.75rem;margin-bottom:4px;">📋 <b style="font-family:monospace;font-size:0.65rem;">{ss.application_id[:20]}</b></div>
          <div style="color:#fff;font-size:0.75rem;margin-bottom:4px;">📅 {datetime.now().strftime('%d %b %Y')}</div>
          <div style="color:#f5c842;font-size:0.75rem;font-weight:600;">Step 1 of {len(STEPS)}</div>
        </div>
      </div>
      <div class="appid-badge">Approx. 15–20 min to complete · All fields can be filled manually</div>
    </div>
    """,unsafe_allow_html=True)

    st.markdown("""
    <div class="scard">
      <div class="scard-head">📁 Upload Certificates — Fields Fill Automatically
        <span class="sbadge">Drop file → instant parse · No button click needed</span>
      </div>
    </div>
    """,unsafe_allow_html=True)

    c1,c2 = st.columns(2)

    # ── Udyam ──────────────────────────────────────────────────────────────
    with c1:
        pc="parsed" if ss.udyam_parsed else ""
        st.markdown(f"""
        <div class="doc-card {pc}">
          <div class="doc-icon-lg">📜</div>
          <div class="doc-name">Udyam Registration Certificate</div>
          <div class="doc-hint">Fills: Enterprise name · Udyam No. · Category · NIC Code → Activity · Address · Mobile · Est. Date · Constitution</div>
          <div class="doc-tags">
            <span class="doc-tag">Udyam No.</span><span class="doc-tag">Category</span>
            <span class="doc-tag">NIC → Activity</span><span class="doc-tag">Address</span>
            <span class="doc-tag">Mobile</span><span class="doc-tag">Est. Date</span>
            <span class="doc-tag">Constitution</span>
          </div>
          {"<div class='parsed-stamp'>✅ Parsed — Fields Filled</div>" if ss.udyam_parsed else ""}
        </div>
        """,unsafe_allow_html=True)
        uf=st.file_uploader("Udyam Certificate",type=["pdf","png","jpg","jpeg"],key="uf_udyam",label_visibility="collapsed")
        if uf is not None:
            fh=file_hash(uf)
            if fh!=ss._last_udyam_hash:
                ss._last_udyam_hash=fh
                with st.spinner("📖 Reading Udyam certificate..."):
                    text=extract_text_from_upload(uf)
                    if text and not text.startswith("["):
                        data=parse_udyam(text)
                        n=apply_parsed_to_ss(data)
                        ss.udyam_parsed=True
                        if n: st.success(f"✅ {n} fields auto-filled from Udyam certificate!")
                        else: st.info("Parsed but could not extract structured data. Please fill manually.")
                    else:
                        st.warning("Could not read file. Try a clearer scan or fill manually.")

    # ── GST ────────────────────────────────────────────────────────────────
    with c2:
        pc="parsed" if ss.gst_parsed else ""
        st.markdown(f"""
        <div class="doc-card {pc}">
          <div class="doc-icon-lg">🧾</div>
          <div class="doc-name">GST Registration Certificate</div>
          <div class="doc-hint">Fills: GSTIN · GST Date · Address · and auto-extracts <b>PAN · State · Constitution from GSTIN</b></div>
          <div class="doc-tags">
            <span class="doc-tag">GSTIN</span><span class="doc-tag">PAN ← auto</span>
            <span class="doc-tag">State ← auto</span><span class="doc-tag">Constitution ← auto</span>
            <span class="doc-tag">GST Date</span><span class="doc-tag">Address</span>
          </div>
          {"<div class='parsed-stamp'>✅ Parsed — Fields Filled</div>" if ss.gst_parsed else ""}
        </div>
        """,unsafe_allow_html=True)
        gf=st.file_uploader("GST Certificate",type=["pdf","png","jpg","jpeg"],key="uf_gst",label_visibility="collapsed")
        if gf is not None:
            fh=file_hash(gf)
            if fh!=ss._last_gst_hash:
                ss._last_gst_hash=fh
                with st.spinner("📖 Reading GST certificate..."):
                    text=extract_text_from_upload(gf)
                    if text and not text.startswith("["):
                        from parsers import parse_gst
                        data=parse_gst(text)
                        n=apply_parsed_to_ss(data)
                        ss.gst_parsed=True
                        if n: st.success(f"✅ {n} fields auto-filled! PAN, State & Constitution extracted from GSTIN.")
                        else: st.info("Parsed but could not extract structured data. Fill manually.")
                    else:
                        st.warning("Could not read file.")

    st.markdown("""
    <div class="info-banner">
      💡 <b>PAN card</b>, Balance Sheet, ITR and other supporting documents are collected at the final step.
      &nbsp;&nbsp;|&nbsp;&nbsp;
      Director / Partner PAN & Aadhaar can be uploaded individually in Step 3.
    </div>
    """,unsafe_allow_html=True)

    _,nav_col=st.columns([3,1])
    with nav_col:
        if st.button("Start Application ➡",type="primary",use_container_width=True): next_s()

# ════════════════════════════════════════════════════════════════════════════
# STEP 1 — ENTERPRISE DETAILS
# ════════════════════════════════════════════════════════════════════════════
elif ss.step==1:

    def af_input(label,key,**kw):
        full=af_label(label,key); val=ss.get(key,"")
        r=st.text_input(full,value=val,**kw)
        if r!=val: ss[key]=r; ss.autofilled_fields.discard(key)
        return r

    st.markdown('<div class="scard"><div class="scard-head">🏢 Enterprise Information <span class="sbadge">Sections 1–10</span></div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        af_input("Name of Enterprise *","enterprise_name",placeholder="As per Udyam/ROC records")
        af_input("Mobile Number *","mobile",placeholder="10-digit mobile")
        ok,msg=validate_mobile(ss.mobile); val_badge(ok,msg)
        if is_af("mobile"): af_pill("From Udyam certificate")
        af_input("Email Address","email",placeholder="info@company.com")
        ok,msg=validate_email(ss.email); val_badge(ok,msg)
        af_input("Office Telephone","telephone",placeholder="STD Code + Number")
        if is_af("telephone"): af_pill("From Udyam certificate")
        ss.website=st.text_input("Website (optional)",ss.website,placeholder="www.yourcompany.com")
    with c2:
        # Constitution dropdown
        # We write to ss["sel_const"] on autofill, so Streamlit widget picks it up
        const_lbl=af_label("Constitution *","constitution")
        # Ensure widget key is in sync with our field (first render or manual edit)
        if "sel_const" not in ss or ss.get("sel_const","") != ss.constitution:
            ss["sel_const"] = ss.constitution if ss.constitution in CONSTITUTIONS else ""
        nc=st.selectbox(const_lbl, CONSTITUTIONS, key="sel_const")
        if nc!=ss.constitution:
            ss.constitution=nc; ss.autofilled_fields.discard("constitution")
        if is_af("constitution"): af_pill(f"Extracted from GSTIN/Udyam: {ss.constitution}")

        # State dropdown
        if "sel_state" not in ss or ss.get("sel_state","") != ss.state:
            ss["sel_state"] = ss.state if ss.state in INDIAN_STATES else ""
        state_lbl=af_label("State *","state")
        ns=st.selectbox(state_lbl, INDIAN_STATES, key="sel_state")
        if ns!=ss.state:
            ss.state=ns; ss.autofilled_fields.discard("state")
        if is_af("state"): af_pill(f"Extracted from GSTIN/Udyam: {ss.state}")

        # Date of establishment
        dob_v=ss.date_of_establishment
        if isinstance(dob_v,str):
            try: dob_v=date.fromisoformat(dob_v)
            except: dob_v=None
        dob_lbl=af_label("Date of Establishment *","date_of_establishment")
        nd=st.date_input(dob_lbl,value=dob_v,min_value=date(1900,1,1),max_value=date.today(),key="dob_inp")
        if nd!=ss.date_of_establishment: ss.date_of_establishment=nd
        if is_af("date_of_establishment"): af_pill("From Udyam certificate")

        ss.num_employees=st.text_input("Number of Employees",ss.num_employees,placeholder="e.g. 45")
    st.markdown('</div>',unsafe_allow_html=True)

    # Registration numbers
    st.markdown('<div class="scard"><div class="scard-head">🪪 Registration & Tax Numbers</div>',unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    with c1:
        pan_lbl=af_label("PAN Number *","pan")
        np=st.text_input(pan_lbl,(ss.pan or "").upper(),placeholder="ABCDE1234F",max_chars=10,key="pan_inp")
        np=np.upper()
        if np!=ss.pan: ss.pan=np; ss.autofilled_fields.discard("pan")
        ok,msg=validate_pan(ss.pan); val_badge(ok,msg)
        if is_af("pan"): af_pill("Extracted from GSTIN")
    with c2:
        udyam_lbl=af_label("Udyam Registration No. *","udyam_no")
        nu=st.text_input(udyam_lbl,ss.udyam_no,placeholder="UDYAM-DL-01-0012345",key="udyam_inp")
        if nu!=ss.udyam_no: ss.udyam_no=nu; ss.autofilled_fields.discard("udyam_no")
        ok,msg=validate_udyam(ss.udyam_no); val_badge(ok,msg)
        if is_af("udyam_no"): af_pill("From Udyam certificate")
    with c3:
        gst_lbl=af_label("GSTIN *","gst_no")
        ng=st.text_input(gst_lbl,(ss.gst_no or "").upper(),placeholder="07ABCDE1234F1Z5",max_chars=15,key="gst_inp")
        ng=ng.upper()
        if ng!=ss.gst_no:
            ss.gst_no=ng; ss.autofilled_fields.discard("gst_no")
            if len(ng)==15:
                extras=apply_gst_autofill(ng)
                if extras: st.rerun()
        ok,msg,_=validate_gstin(ss.gst_no); val_badge(ok,msg)
        if is_af("gst_no"): af_pill("From GST certificate")

    c1,c2,c3=st.columns(3)
    with c1:
        gd_v=ss.gst_date
        if isinstance(gd_v,str):
            try: gd_v=date.fromisoformat(gd_v)
            except: gd_v=None
        gd_lbl=af_label("GST Registration Date","gst_date")
        ss.gst_date=st.date_input(gd_lbl,value=gd_v,min_value=date(2017,7,1),max_value=date.today(),key="gst_date_inp")
        if is_af("gst_date"): af_pill("From GST certificate")
    with c2:
        msme_lbl=af_label("MSME Category","msme_category")
        mo=["","Micro","Small","Medium"]
        if "sel_msme" not in ss or ss.get("sel_msme","") != ss.msme_category:
            ss["sel_msme"] = ss.msme_category if ss.msme_category in mo else ""
        nm=st.selectbox(msme_lbl,mo,key="sel_msme")
        if nm!=ss.msme_category: ss.msme_category=nm
        if is_af("msme_category"): af_pill("From Udyam certificate")
    with c3:
        nic_lbl=af_label("NIC Code","nic_code")
        nn=st.text_input(nic_lbl,ss.nic_code,placeholder="e.g. 26100",key="nic_inp")
        if nn!=ss.nic_code:
            ss.nic_code=nn
            if nn:
                act=nic_to_activity(nn)
                if act and not ss.activity_existing:
                    ss.activity_existing=act; mark_af("activity_existing")
        if is_af("nic_code"): af_pill("From Udyam certificate")

    c1,c2,c3=st.columns(3)
    with c1:
        ss.gem_registered=st.selectbox("GeM Registered?",["No","Yes"],key="gem_sel")
        if ss.gem_registered=="Yes": ss.gem_no=st.text_input("GeM No.",ss.gem_no,key="gem_no_inp")
    with c2: ss.iec_code=st.text_input("IEC Code (if applicable)",ss.iec_code,placeholder="Import-Export Code",key="iec_inp")
    with c3:
        ss.zed_rated=st.selectbox("ZED Rated?",["No","Yes"],key="zed_sel")
        if ss.zed_rated=="Yes":
            ss.zed_grade=st.selectbox("ZED Grade",["","Bronze","Silver","Gold","Diamond","Platinum"],key="zed_grade_sel")

    c1,c2=st.columns(2)
    with c1: ss.city_loan=st.text_input("City/District for Loan *",ss.city_loan,key="city_inp")
    with c2: ss.branch_loan=st.text_input("Preferred Branch (optional)",ss.branch_loan,key="branch_inp")
    st.markdown('</div>',unsafe_allow_html=True)

    # Address
    st.markdown('<div class="scard"><div class="scard-head">📍 Address Details</div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        regd_lbl=af_label("Registered Office Address * (as per Udyam/ROC)","regd_office_address")
        nr=st.text_area(regd_lbl,ss.regd_office_address,height=80,placeholder="Full address with PIN code",key="regd_addr")
        if nr!=ss.regd_office_address: ss.regd_office_address=nr; ss.autofilled_fields.discard("regd_office_address")
        if is_af("regd_office_address"): af_pill("From Udyam/GST certificate")
    with c2:
        same=st.checkbox("Factory/Shop address same as Registered Office",value=ss.factory_same_as_regd,key="same_addr_cb")
        ss.factory_same_as_regd=same
        if same:
            ss.factory_address=ss.regd_office_address
            st.text_area("Factory / Shop Address",ss.factory_address,height=80,disabled=True,key="fac_addr_dis")
            af_pill("Copied from Registered Office")
        else:
            nf=st.text_area("Factory / Shop Address",ss.factory_address,height=80,placeholder="If different from registered office",key="fac_addr_inp")
            if nf!=ss.factory_address: ss.factory_address=nf

    c1,c2=st.columns(2)
    with c1: ss.premises_type=st.selectbox("Premises Type *",["Owned","Rented","Leased"],key="prem_sel")
    with c2:
        if ss.premises_type in ["Rented","Leased"]:
            ss.premises_details=st.text_input("Lessor Name & Rent/Lease Details *",ss.premises_details,key="prem_det")
    st.markdown('</div>',unsafe_allow_html=True)

    # Activity
    st.markdown('<div class="scard"><div class="scard-head">⚙️ Business Activity</div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        act_lbl=af_label("Present Activity * (as per NIC/Udyam)","activity_existing")
        na=st.text_area(act_lbl,ss.activity_existing,height=65,placeholder="e.g. Manufacture of electronic components (NIC 26100)",key="act_inp")
        if na!=ss.activity_existing: ss.activity_existing=na; ss.autofilled_fields.discard("activity_existing")
        if is_af("activity_existing"): af_pill(f"Mapped from NIC code {ss.nic_code}")
    with c2:
        ss.activity_proposed=st.text_area("Proposed Activity (if new/different)",ss.activity_proposed,height=65,placeholder="Leave blank if same",key="act_prop")
    st.markdown('</div>',unsafe_allow_html=True)

    c1,c2=st.columns(2)
    with c1:
        if st.button("⬅ Back",use_container_width=True,key="ent_back"): prev_s()
    with c2:
        if st.button(f"Next: {get_person_label_plural(ss.constitution)} ➡",type="primary",use_container_width=True,key="ent_next"): next_s()

# ════════════════════════════════════════════════════════════════════════════
# STEP 2 — DIRECTORS / PARTNERS / PROPRIETORS
# ════════════════════════════════════════════════════════════════════════════
elif ss.step==2:
    plabel=get_person_label(ss.constitution)
    plabelp=get_person_label_plural(ss.constitution)

    st.markdown(f"""
    <div class="info-banner">
      <b>Section 11 — {plabelp}</b> — Add details of all {plabelp}.
      Upload PAN or Aadhaar for each person to auto-fill their details.
      Photographs are collected in Step 8.
    </div>
    """,unsafe_allow_html=True)

    if st.button(f"➕ Add {plabel}",key="add_dir_btn"):
        ss.directors.append(make_director()); st.rerun()

    for i,d in enumerate(ss.directors):
        lbl=f"👤 {plabel} {i+1}: {d['name'] or '(Name not entered)'}"
        with st.expander(lbl,expanded=(i==0)):

            # ── Compact PAN + Aadhaar upload row ─────────────────────────
            st.markdown(f"""
            <div style="background:#f0f6ff;border-radius:10px;padding:8px 12px;margin-bottom:10px;border:1px solid #c7d9f5;">
              <div style="font-size:0.72rem;font-weight:700;color:#1a3c6e;margin-bottom:6px;">
                ⚡ Quick Fill — Upload {plabel}'s documents to auto-fill fields below
              </div>
            </div>
            """,unsafe_allow_html=True)

            pu_col, au_col = st.columns(2)
            with pu_col:
                pan_file=st.file_uploader(
                    f"🪪 Upload PAN Card",
                    type=["pdf","png","jpg","jpeg"],
                    key=f"dir_pan_upload_{i}",
                    help="Auto-fills PAN number, name, date of birth, father's name"
                )
                if pan_file is not None:
                    pan_fh=file_hash(pan_file)
                    last_key=f"_dir_pan_hash_{i}"
                    if ss.get(last_key,"")!=pan_fh:
                        ss[last_key]=pan_fh
                        with st.spinner("Reading PAN card..."):
                            text=extract_text_from_upload(pan_file)
                            if text and not text.startswith("["):
                                filled=parse_director_pan(text,d)
                                if filled: st.success(f"✅ Filled: {', '.join(filled)}")
                                else: st.info("PAN read but couldn't extract — fill manually")
                            else: st.warning("Could not read PAN card")

            with au_col:
                aadhar_file=st.file_uploader(
                    f"🔵 Upload Aadhaar Card",
                    type=["pdf","png","jpg","jpeg"],
                    key=f"dir_aadhar_upload_{i}",
                    help="Auto-fills Aadhaar number, name, date of birth, address"
                )
                if aadhar_file is not None:
                    aadhar_fh=file_hash(aadhar_file)
                    last_key=f"_dir_aadhar_hash_{i}"
                    if ss.get(last_key,"")!=aadhar_fh:
                        ss[last_key]=aadhar_fh
                        with st.spinner("Reading Aadhaar card..."):
                            text=extract_text_from_upload(aadhar_file)
                            if text and not text.startswith("["):
                                filled=parse_director_aadhar(text,d)
                                if filled: st.success(f"✅ Filled: {', '.join(filled)}")
                                else: st.info("Aadhaar read but couldn't extract — fill manually")
                            else: st.warning("Could not read Aadhaar card")

            st.markdown("<hr style='margin:8px 0'>",unsafe_allow_html=True)

            # ── Manual fields ─────────────────────────────────────────────
            c1,c2,c3=st.columns(3)
            with c1:
                d["name"]=st.text_input(f"Full Name * ({plabel})",d["name"],key=f"dn_{i}",placeholder="As per PAN card")
                d["father_spouse"]=st.text_input("Father's / Spouse's Name",d["father_spouse"],key=f"dfs_{i}")
                d["qualification"]=st.text_input("Qualification",d["qualification"],key=f"dq_{i}",placeholder="e.g. B.Tech, MBA")
                d["designation"]=st.text_input(f"Designation",d.get("designation",""),key=f"ddes_{i}",placeholder=f"e.g. Managing {plabel}")
            with c2:
                dob_v=d["dob"]
                if isinstance(dob_v,str):
                    try: dob_v=date.fromisoformat(dob_v)
                    except: dob_v=None
                d["dob"]=st.date_input("Date of Birth *",value=dob_v,key=f"ddob_{i}",min_value=date(1930,1,1),max_value=date.today())
                d["mobile"]=st.text_input("Mobile No.",d["mobile"],key=f"dmob_{i}")
                ok,msg=validate_mobile(d["mobile"]); val_badge(ok,msg)
                d["category"]=st.selectbox("Category",["","General","SC","ST","OBC","Minority","Women","Other"],key=f"dcat_{i}")
                d["experience"]=st.text_input("Experience (Years)",d["experience"],key=f"dexp_{i}",placeholder="Years in this line of business")
            with c3:
                d["pan"]=st.text_input("PAN No.",(d.get("pan") or "").upper(),key=f"dpan_{i}",max_chars=10)
                d["pan"]=d["pan"].upper()
                ok,msg=validate_pan(d["pan"]); val_badge(ok,msg)
                d["aadhar_din"]=st.text_input("Aadhaar No. / DIN No.",d.get("aadhar_din",""),key=f"ddin_{i}")
                adi=re.sub(r'\D','',d.get("aadhar_din",""))
                if len(adi)==12: ok,msg=validate_aadhar(adi); val_badge(ok,msg)
                d["telephone"]=st.text_input("Telephone (Residence)",d.get("telephone",""),key=f"dtel_{i}")
            d["address"]=st.text_area("Residential Address",d.get("address",""),key=f"daddr_{i}",height=58,placeholder="Full address with PIN code")

            if len(ss.directors)>1:
                if st.button(f"🗑 Remove {plabel} {i+1}",key=f"ddel_{i}"):
                    ss.directors.pop(i); st.rerun()

    with st.expander("🤝 Associate Concerns (Section 14)",expanded=False):
        if not ss.associate_concerns:
            ss.associate_concerns=[{"name":"","address":"","banking_with":"","nature":"","extent":""}]
        for j,ac in enumerate(ss.associate_concerns):
            cols=st.columns(5)
            ac["name"]        =cols[0].text_input("Name",ac["name"],key=f"acn_{j}")
            ac["address"]     =cols[1].text_input("Address",ac["address"],key=f"aca_{j}")
            ac["banking_with"]=cols[2].text_input("Banking With",ac["banking_with"],key=f"acb_{j}")
            ac["nature"]      =cols[3].text_input("Nature of Assoc.",ac["nature"],key=f"acna_{j}")
            ac["extent"]      =cols[4].text_input("Extent of Interest",ac["extent"],key=f"ace_{j}")
        if st.button("➕ Add Associate Concern",key="add_assoc"):
            ss.associate_concerns.append({"name":"","address":"","banking_with":"","nature":"","extent":""}); st.rerun()

    with st.expander("🏛 Relationship with Bank Officials (Section 15)",expanded=False):
        ss.bank_relationship=st.radio("Relationship with Bank Officials/Directors?",["No","Yes"],horizontal=True,key="br_r")
        if ss.bank_relationship=="Yes":
            ss.bank_relationship_details=st.text_area("Provide Details",ss.bank_relationship_details,height=55,key="br_det")

    c1,c2=st.columns(2)
    with c1:
        if st.button("⬅ Back",use_container_width=True,key="ppl_back"): prev_s()
    with c2:
        if st.button("Next: Existing Banking ➡",type="primary",use_container_width=True,key="ppl_next"): next_s()

# ════════════════════════════════════════════════════════════════════════════
# STEP 3 — EXISTING BANKING
# ════════════════════════════════════════════════════════════════════════════
elif ss.step==3:
    st.markdown('<div class="scard"><div class="scard-head">💳 Existing Banking / Credit Facilities <span class="sbadge">Section 16 · ₹ in Lakhs</span></div>',unsafe_allow_html=True)
    st.markdown('<div class="info-banner">Fill only facilities that currently exist. Leave amount blank if not applicable.</div>',unsafe_allow_html=True)

    tabs=st.tabs([f["type"] for f in ss.existing_facilities])
    for idx,(tab,fac) in enumerate(zip(tabs,ss.existing_facilities)):
        with tab:
            c1,c2,c3=st.columns(3)
            k=f"ef{idx}"
            with c1:
                fac["limit"]      =st.text_input("Limit (₹ Lacs)",fac["limit"],key=f"{k}l",placeholder="0.00")
                fac["outstanding"]=st.text_input("Outstanding",fac["outstanding"],key=f"{k}o",placeholder="0.00")
            with c2:
                fac["banking_with"]=st.text_input("Presently Banking With",fac["banking_with"],key=f"{k}b",placeholder="Bank & Branch name")
                fac["securities"]  =st.text_input("Securities",fac["securities"],key=f"{k}s",placeholder="e.g. Stock, Machinery, FD")
            with c3:
                fac["roi"]      =st.text_input("Rate of Interest (%)",fac["roi"],key=f"{k}r",placeholder="e.g. 10.5%")
                fac["repayment"]=st.text_input("Repayment Terms",fac["repayment"],key=f"{k}rep",placeholder="e.g. 60 EMIs / Revolving")

    st.markdown('</div>',unsafe_allow_html=True)
    ss.cif_no=st.text_input("CIF No. (if existing Bharat Bank customer)",ss.cif_no,placeholder="Customer ID / CIF Number",key="cif_inp")
    st.markdown('<div class="warn-banner">📌 By proceeding you certify that no loans exist from any Bank/FI other than those listed above.</div>',unsafe_allow_html=True)

    c1,c2=st.columns(2)
    with c1:
        if st.button("⬅ Back",use_container_width=True,key="bk_back"): prev_s()
    with c2:
        if st.button("Next: Loan Requirements ➡",type="primary",use_container_width=True,key="bk_next"): next_s()

# ════════════════════════════════════════════════════════════════════════════
# STEP 4 — LOAN REQUIREMENTS
# ════════════════════════════════════════════════════════════════════════════
elif ss.step==4:
    st.markdown('<div class="scard"><div class="scard-head">💰 Credit Facilities Proposed <span class="sbadge">Section 17 · ₹ in Lakhs</span></div>',unsafe_allow_html=True)

    tabs=st.tabs([f["type"] for f in ss.proposed_facilities])
    for idx,(tab,fac) in enumerate(zip(tabs,ss.proposed_facilities)):
        with tab:
            c1,c2,c3,c4=st.columns(4)
            k=f"pf{idx}"
            with c1: fac["amount"]           =st.text_input("Amount * (₹ Lacs)",fac["amount"],key=f"{k}a",placeholder="0.00")
            with c2: fac["purpose"]          =st.text_input("Purpose *",fac["purpose"],key=f"{k}p",placeholder="e.g. Working Capital")
            with c3: fac["primary_security"] =st.text_input("Primary Security (with approx. value)",fac["primary_security"],key=f"{k}s")
            with c4: fac["collateral_offered"]=st.selectbox("Collateral Offered?",["No","Yes"],key=f"{k}c")

    total=loan_total()
    st.markdown(f"""<div class="loan-bar"><div><div class="loan-bar-lbl">Total Loan Proposed</div>
    <div style="font-size:0.68rem;opacity:0.58">Sum of all facilities above</div></div>
    <div class="loan-bar-val">₹ {total:,.2f} Lacs</div></div>""",unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

    # ── Machinery — flat table, NO nested expanders ───────────────────────
    term_amt=next((f["amount"] for f in ss.proposed_facilities if f["type"]=="Term Loan" and f["amount"]),"")
    with st.expander(f"⚙️ Machinery Details — Section 18{'  · Required for Term Loan' if term_amt else ''}",expanded=bool(term_amt)):
        if not ss.machinery_details:
            ss.machinery_details=[make_machine()]

        for mi,m in enumerate(ss.machinery_details):
            st.markdown(f'<div class="machine-row"><div class="machine-row-head">⚙️ Machine {mi+1}: {m.get("machine") or "(unnamed)"}',unsafe_allow_html=True)
            if len(ss.machinery_details)>1:
                if st.button(f"🗑 Remove",key=f"mach_del_{mi}"):
                    ss.machinery_details.pop(mi); st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)

            c1,c2,c3,c4=st.columns(4)
            with c1:
                m["machine"]    =st.text_input("Machine/Equipment",m["machine"],key=f"mt_{mi}")
                m["purpose"]    =st.text_input("Purpose",m["purpose"],key=f"mp_{mi}")
            with c2:
                m["imported"]   =st.selectbox("Indigenous/Imported",["Indigenous","Imported"],key=f"mi_{mi}")
                m["supplier"]   =st.text_input("Supplier Name",m["supplier"],key=f"ms_{mi}")
            with c3:
                m["total_cost"] =st.text_input("Total Cost (₹ Lacs)",m["total_cost"],key=f"mc_{mi}")
                m["contribution"]=st.text_input("Promoter Contribution",m["contribution"],key=f"mcon_{mi}")
            with c4:
                m["loan_req"]   =st.text_input("Loan Required",m["loan_req"],key=f"ml_{mi}")
                m["second_hand"]=st.checkbox("Second Hand / Old",m["second_hand"],key=f"msh_{mi}")
                if m["second_hand"]:
                    m["residual_life"]=st.text_input("Residual Life (Years) *",m.get("residual_life",""),key=f"mrl_{mi}")
            st.markdown('</div>',unsafe_allow_html=True)

        if st.button("➕ Add Machine",key="add_machine_btn"):
            ss.machinery_details.append(make_machine()); st.rerun()

    c1,c2=st.columns(2)
    with c1:
        if st.button("⬅ Back",use_container_width=True,key="ln_back"): prev_s()
    with c2:
        if st.button("Next: Security & Collateral ➡",type="primary",use_container_width=True,key="ln_next"): next_s()

# ════════════════════════════════════════════════════════════════════════════
# STEP 5 — SECURITY & COLLATERAL
# ════════════════════════════════════════════════════════════════════════════
elif ss.step==5:
    plabelp=get_person_label_plural(ss.constitution)
    st.markdown('<div class="warn-banner">📌 As per guidelines, collateral is not required for loans up to ₹10 Lakhs to MSE Units.</div>',unsafe_allow_html=True)

    ac,_=st.columns([2,3])
    with ac:
        if st.button(f"⚡ Auto-fill Guarantors from {plabelp} List",use_container_width=True,key="autofill_guar"):
            auto_populate_guarantors(); st.rerun()

    st.markdown('<div class="scard"><div class="scard-head">🤝 Third Party Guarantors <span class="sbadge">Section 19(a)</span></div>',unsafe_allow_html=True)
    if not ss.collateral_guarantors: ss.collateral_guarantors=[make_guarantor()]

    for gi,g in enumerate(ss.collateral_guarantors):
        with st.expander(f"Guarantor {gi+1}: {g.get('name') or '(Name not set)'}",expanded=(gi==0)):
            c1,c2,c3,c4=st.columns(4)
            with c1:
                g["name"]        =st.text_input("Name of Guarantor *",g["name"],key=f"gn{gi}")
                g["father_spouse"]=st.text_input("Father's / Spouse Name",g["father_spouse"],key=f"gfs{gi}")
                g["relationship"]=st.text_input("Relationship with Applicant",g.get("relationship",""),key=f"grel{gi}")
            with c2:
                g["address"]=st.text_area("Residential Address",g["address"],key=f"gaddr{gi}",height=65)
            with c3:
                g["mobile"]=st.text_input("Mobile No.",g["mobile"],key=f"gmob{gi}")
                ok,msg=validate_mobile(g["mobile"]); val_badge(ok,msg)
                g["telephone"]=st.text_input("Telephone (Residence)",g.get("telephone",""),key=f"gtel{gi}")
            with c4:
                g["net_worth"]=st.text_input("Net Worth (₹ Lacs)",g["net_worth"],key=f"gnw{gi}")
                g["aadhar"]=st.text_input("Aadhaar No.",g.get("aadhar",""),key=f"gad{gi}")
                g["pan"]=st.text_input("PAN No.",(g.get("pan") or "").upper(),key=f"gpan{gi}").upper()
                ok,msg=validate_pan(g["pan"]); val_badge(ok,msg)
            if len(ss.collateral_guarantors)>1:
                if st.button(f"🗑 Remove Guarantor {gi+1}",key=f"gdel{gi}"):
                    ss.collateral_guarantors.pop(gi); st.rerun()

    if st.button("➕ Add Guarantor",key="add_guar"): ss.collateral_guarantors.append(make_guarantor()); st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

    st.markdown('<div class="scard"><div class="scard-head">🏠 Other Collateral Security <span class="sbadge">Section 19(b)</span></div>',unsafe_allow_html=True)
    if not ss.collateral_others: ss.collateral_others=[{"owner":"","nature":"","details":"","value":"","location":""}]
    for oi,o in enumerate(ss.collateral_others):
        c1,c2,c3,c4,c5=st.columns(5)
        with c1: o["owner"]  =st.text_input("Owner Name",o["owner"],key=f"coo{oi}")
        with c2:
            ni=COLLATERAL_NATURE.index(o.get("nature","")) if o.get("nature","") in COLLATERAL_NATURE else 0
            o["nature"]=st.selectbox("Nature of Security",COLLATERAL_NATURE,index=ni,key=f"con{oi}")
        with c3: o["details"]=st.text_input("Details / Description",o["details"],key=f"cod{oi}",placeholder="Address/FD No./Policy No.")
        with c4: o["location"]=st.text_input("Location / Bank",o.get("location",""),key=f"col{oi}")
        with c5: o["value"]=st.text_input("Value (₹ Lacs)",o["value"],key=f"cov{oi}")
    if st.button("➕ Add Collateral",key="add_coll"): ss.collateral_others.append({"owner":"","nature":"","details":"","value":"","location":""}); st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

    c1,c2=st.columns(2)
    with c1:
        if st.button("⬅ Back",use_container_width=True,key="sec_back"): prev_s()
    with c2:
        if st.button("Next: Financials ➡",type="primary",use_container_width=True,key="sec_next"): next_s()

# ════════════════════════════════════════════════════════════════════════════
# STEP 6 — FINANCIALS
# ════════════════════════════════════════════════════════════════════════════
elif ss.step==6:
    pd_ref=ss.performance_data

    st.markdown('<div class="scard"><div class="scard-head">💹 Turnover & Investment</div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        ss.turnover_last_year=st.text_input("Last Year Annual Turnover (₹ Lakhs) *",ss.get("turnover_last_year",""),placeholder="e.g. 485.50",key="tol_inp",help="Used for MSME category verification")
    with c2:
        ss.investment_plant=st.text_input("Investment in Plant & Machinery / Equipment (₹ Lakhs)",ss.get("investment_plant",""),placeholder="e.g. 125.00",key="inv_inp",help="Used for Micro/Small/Medium classification")
    st.markdown('</div>',unsafe_allow_html=True)

    st.markdown('<div class="scard"><div class="scard-head">📊 Past Performance & Future Estimates <span class="sbadge">Section 20 · ₹ in Lakhs</span></div>',unsafe_allow_html=True)
    cols=st.columns(5)
    cols[0].markdown("**Metric**")
    for i,h in enumerate(["Past Year-II (Actual)","Past Year-I (Actual)","Current Year (Est.)","Next Year (Proj.)"]):
        cols[i+1].markdown(f"**{h}**")
    for metric,suffix in [("Net Sales","sales"),("Net Profit","profit"),("Capital / Net Worth","capital")]:
        c=st.columns(5); c[0].markdown(f"**{metric}**")
        for pi,prefix in enumerate(["past2","past1","current","next"]):
            k=f"{prefix}_{suffix}"
            pd_ref[k]=c[pi+1].text_input("",pd_ref.get(k,""),key=f"pd_{k}",label_visibility="collapsed",placeholder="0.00")
    st.markdown('</div>',unsafe_allow_html=True)

    st.markdown('<div class="scard"><div class="scard-head">🏪 Top 5 Suppliers & Customers <span class="sbadge">Section 21</span></div>',unsafe_allow_html=True)
    t_sup,t_cus=st.tabs(["🏭 Top 5 Suppliers","🧑‍💼 Top 5 Customers"])
    hdr=["Name","Contact","Since","% Business","Credit Terms"]
    with t_sup:
        hc=st.columns(5)
        for hi,h in enumerate(hdr): hc[hi].markdown(f"**{h}**")
        for si,s in enumerate(ss.top_suppliers):
            c=st.columns(5)
            s["name"]   =c[0].text_input("",s["name"],   key=f"sn{si}",placeholder=f"Supplier {si+1}",label_visibility="collapsed")
            s["contact"]=c[1].text_input("",s["contact"],key=f"sc{si}",label_visibility="collapsed")
            s["since"]  =c[2].text_input("",s["since"],  key=f"ss{si}",placeholder="Year",label_visibility="collapsed")
            s["pct"]    =c[3].text_input("",s["pct"],    key=f"sp{si}",placeholder="%",label_visibility="collapsed")
            s["terms"]  =c[4].text_input("",s["terms"],  key=f"st{si}",placeholder="30 days",label_visibility="collapsed")
    with t_cus:
        hc=st.columns(5)
        for hi,h in enumerate(hdr): hc[hi].markdown(f"**{h}**")
        for ci,cu in enumerate(ss.top_customers):
            c=st.columns(5)
            cu["name"]   =c[0].text_input("",cu["name"],   key=f"cn{ci}",placeholder=f"Customer {ci+1}",label_visibility="collapsed")
            cu["contact"]=c[1].text_input("",cu["contact"],key=f"cc{ci}",label_visibility="collapsed")
            cu["since"]  =c[2].text_input("",cu["since"],  key=f"cs{ci}",placeholder="Year",label_visibility="collapsed")
            cu["pct"]    =c[3].text_input("",cu["pct"],    key=f"cp{ci}",placeholder="%",label_visibility="collapsed")
            cu["terms"]  =c[4].text_input("",cu["terms"],  key=f"ct{ci}",placeholder="60 days",label_visibility="collapsed")
    st.markdown('</div>',unsafe_allow_html=True)

    with st.expander("⚖️ Statutory Compliance — Section 22",expanded=False):
        stat=ss.statutory; opts=["","Yes","No","N.A."]
        c1,c2=st.columns(2)
        with c1:
            for k,lbl in [("shops_act","1. Shops & Establishment Act"),("msme_reg","2. MSME Registration"),("drug_license","3. Drug License")]:
                stat[k]=st.selectbox(lbl,opts,index=opts.index(stat.get(k,"")) if stat.get(k,"") in opts else 0,key=f"stat_{k}")
        with c2:
            for k,lbl in [("sales_tax","4. Sales Tax Return Filed"),("income_tax","5. Income Tax Return Filed"),("other_dues","6. Other Statutory Dues Outstanding")]:
                stat[k]=st.selectbox(lbl,opts,index=opts.index(stat.get(k,"")) if stat.get(k,"") in opts else 0,key=f"stat_{k}")

    c1,c2=st.columns(2)
    with c1:
        if st.button("⬅ Back",use_container_width=True,key="fin_back"): prev_s()
    with c2:
        if st.button("Next: Photos ➡",type="primary",use_container_width=True,key="fin_next"): next_s()

# ════════════════════════════════════════════════════════════════════════════
# STEP 7 — PHOTOS
# ════════════════════════════════════════════════════════════════════════════
elif ss.step==7:
    plabelp=get_person_label_plural(ss.constitution)
    st.markdown(f"""
    <div class="info-banner">
      <b>Passport Photographs of {plabelp}</b> — Upload one recent passport-size photo per person.
      Photos will be printed on the application form and attested by the branch.
    </div>
    """,unsafe_allow_html=True)

    for i,d in enumerate(ss.directors):
        name=d.get("name") or f"{get_person_label(ss.constitution)} {i+1}"
        desig=d.get("designation") or get_person_label(ss.constitution)
        ci2,cu,cinfo=st.columns([1,2,3])
        with ci2:
            if str(i) in ss.photos:
                img_bytes=base64.b64decode(ss.photos[str(i)])
                st.image(img_bytes,width=90,caption=name[:16])
            else:
                st.markdown(f"""<div style="width:90px;height:110px;background:#f0f4fa;border:2px dashed #a8c0e0;
                border-radius:8px;display:flex;align-items:center;justify-content:center;
                flex-direction:column;font-size:0.63rem;color:#6b7280;text-align:center;padding:5px;">
                📷<br>{name[:14]}</div>""",unsafe_allow_html=True)
        with cu:
            pf=st.file_uploader(f"Photo — {name}",type=["jpg","jpeg","png"],key=f"photo_up_{i}")
            if pf:
                img=Image.open(pf); img.thumbnail((300,380))
                ss.photos[str(i)]=img_to_b64(img); st.rerun()
            if str(i) in ss.photos:
                if st.button("🗑 Remove photo",key=f"rph_{i}"):
                    del ss.photos[str(i)]; st.rerun()
        with cinfo:
            st.markdown(f"""<div style="background:#f8faff;border-radius:9px;padding:9px 12px;font-size:0.75rem;color:#374151;">
            <b>{name}</b><br><span style="color:#6b7280;">{desig}</span><br>
            PAN: {d.get('pan') or '—'} &nbsp;|&nbsp; {d.get('category') or '—'}</div>""",unsafe_allow_html=True)
        st.markdown("<hr style='margin:8px 0'>",unsafe_allow_html=True)

    st.markdown('<div class="scard"><div class="scard-head">🪪 ID & Address Proof — Section 23</div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        st.selectbox("ID Proof Type",["","Aadhaar Card","Passport","Voter ID","PAN Card","Driving Licence","Job Card"],key="id_proof_type")
        st.text_input("ID Proof Number",key="id_proof_no",placeholder="Document number")
    with c2:
        st.selectbox("Address Proof Type",["","Electricity Bill","Telephone Bill","Bank Statement","Passport","Voter ID","Ration Card","Property Tax Receipt"],key="addr_proof_type")
        st.text_input("Address Proof Reference",key="addr_proof_ref",placeholder="Date or reference number")
    st.markdown('</div>',unsafe_allow_html=True)

    c1,c2=st.columns(2)
    with c1:
        if st.button("⬅ Back",use_container_width=True,key="ph_back"): prev_s()
    with c2:
        if st.button("Next: Review & Submit ➡",type="primary",use_container_width=True,key="ph_next"): next_s()

# ════════════════════════════════════════════════════════════════════════════
# STEP 8 — REVIEW, DOCS, CONSENT & PDF
# ════════════════════════════════════════════════════════════════════════════
elif ss.step==8:
    from pdf_generator import generate_pdf
    plabelp=get_person_label_plural(ss.constitution)
    total=loan_total()

    st.markdown(f"""
    <div class="mrow">
      <div class="mbox"><div class="mbox-lbl">Enterprise</div><div class="mbox-val" style="font-size:0.78rem;">{ss.enterprise_name or '—'}</div></div>
      <div class="mbox"><div class="mbox-lbl">Loan Proposed</div><div class="mbox-val green">₹ {total:,.2f} L</div></div>
      <div class="mbox"><div class="mbox-lbl">Category</div><div class="mbox-val">{ss.msme_category or '—'}</div></div>
      <div class="mbox"><div class="mbox-lbl">{plabelp}</div><div class="mbox-val">{len(ss.directors)}</div></div>
      <div class="mbox"><div class="mbox-lbl">Photos</div><div class="mbox-val {'green' if len(ss.photos)==len(ss.directors) else 'amber'}">{len(ss.photos)}/{len(ss.directors)}</div></div>
      <div class="mbox"><div class="mbox-lbl">GSTIN</div><div class="mbox-val" style="font-size:0.68rem;font-family:monospace;">{ss.gst_no or '—'}</div></div>
    </div>
    """,unsafe_allow_html=True)

    with st.expander("📂 Supporting Documents Upload & Checklist",expanded=False):
        st.markdown('<div class="info-banner">Upload all documents as per the checklist. These accompany your printed form to the branch.</div>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:
            st.file_uploader("🪪 PAN Card (Enterprise)",type=["pdf","jpg","png"],key="doc_pan")
            st.file_uploader("📊 Balance Sheet — Last 3 Years",type=["pdf","xlsx","xls"],key="doc_bs")
            st.file_uploader("📋 ITR / GST Returns (3 years)",type=["pdf","zip"],key="doc_itr")
            st.file_uploader("📜 MOA/AOA or Partnership Deed",type=["pdf"],key="doc_moa")
        with c2:
            st.file_uploader("💰 Assets & Liabilities Statement",type=["pdf","xlsx"],key="doc_al")
            st.file_uploader("🏠 Property Documents / Title Deeds",type=["pdf","jpg","png"],key="doc_prop",accept_multiple_files=True)
            st.file_uploader("📄 Rent Agreement (if rented)",type=["pdf"],key="doc_rent")
            st.file_uploader("📁 Any Other Documents",type=["pdf","jpg","png","docx"],key="doc_other",accept_multiple_files=True)

    st.markdown("""
    <div class="decl-box">
      <b>I/We hereby certify that:</b>
      <ul>
        <li>All information furnished is <b>true, correct and complete</b>.</li>
        <li>I/We have no borrowing arrangements except as indicated in this application.</li>
        <li>There are no overdue/statutory dues against me/us/promoters except as stated above.</li>
        <li>No legal action has been or is being taken against me/us/promoters by any Bank/FI.</li>
        <li>I/We shall furnish all other information required for processing this application.</li>
        <li>The Bank or RBI may, at any time, inspect/verify our assets and books of accounts.</li>
        <li>My/our loan shall be governed by the rules of the Bank in force from time to time.</li>
      </ul>
    </div>
    """,unsafe_allow_html=True)

    ss.declaration_agreed=st.checkbox(
        f"✅ I/We agree to the above declaration. All information is true and correct.",
        value=ss.declaration_agreed,key="decl_cb"
    )

    st.markdown("---")
    st.markdown("### 📊 Credit Bureau Consent")
    st.markdown('<div class="info-banner">The Bank requires consent to access credit information from Credit Information Companies (CICs) for evaluating this loan application.</div>',unsafe_allow_html=True)
    ss.cibil_consent=st.checkbox(
        "✅ I/We consent to Bharat Bank of India accessing our Credit Information Report from **CIBIL (TransUnion)** for this MSME loan application.",
        value=ss.cibil_consent,key="cibil_cb"
    )
    ss.cibil_equifax_consent=st.checkbox(
        "✅ I/We further consent to accessing credit information from **Equifax, CRIF High Mark, and/or Experian** as required for credit appraisal.",
        value=ss.cibil_equifax_consent,key="cibil_eq_cb"
    )
    st.caption("Consent is valid for the duration of this application and any subsequent review/renewal. Governed by the Credit Information Companies (Regulation) Act, 2005.")

    st.markdown("---")
    c1,c2,c3=st.columns(3)
    with c1:
        if st.button("⬅ Back",use_container_width=True,key="sub_back"): prev_s()
    with c2:
        if st.button("💾 Save Draft",use_container_width=True,key="sub_save"):
            save_draft(); st.success("Draft saved!")
        df=st.file_uploader("📂 Load Draft (.json)",type=["json"],key="load_draft_sub")
        if df:
            try:
                loaded=json.load(df)
                for k,v in loaded.items():
                    if k in ss: ss[k]=v
                st.success("Draft loaded!"); st.rerun()
            except Exception as e: st.error(f"Error: {e}")
    with c3:
        if not ss.declaration_agreed:
            st.warning("⚠️ Please agree to the declaration first.")
        elif not ss.cibil_consent:
            st.warning("⚠️ Please provide CIBIL consent.")
        else:
            if st.button("🖨️ Generate PDF Application",type="primary",use_container_width=True,key="gen_pdf_btn"):
                with st.spinner("Building PDF..."):
                    try:
                        pdf_bytes=generate_pdf(ss)
                        st.download_button(
                            "⬇️ Download Application PDF",
                            data=pdf_bytes,
                            file_name=f"MSME_Application_{ss.application_id}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key="dl_pdf_btn",
                        )
                        st.success("✅ PDF ready!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"PDF error: {e}")
                        import traceback; st.code(traceback.format_exc())
