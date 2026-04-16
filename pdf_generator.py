"""
PDF Generator for MSME Loan Application — Union Bank of India Annexure I
Generates a complete, printable PDF with photos, signature spaces, all sections.
"""

import io, base64
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image as RLImage, PageBreak
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.colors import HexColor
from PIL import Image as PILImage

# ── Brand Colours ─────────────────────────────────────────────────────
NAVY    = HexColor("#1a3c6e")
GOLD    = HexColor("#e8a020")
LIGHT   = HexColor("#eef4fb")
GRAY    = HexColor("#6b7280")
LGRAY   = HexColor("#f3f4f6")
WHITE   = colors.white
BLACK   = colors.black
RED     = HexColor("#c0392b")

W, H = A4  # 595.27 x 841.89 pts

# ── Styles ─────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

sTitle   = S("sTitle",   fontName="Helvetica-Bold", fontSize=14, textColor=WHITE,  alignment=TA_CENTER, spaceAfter=2)
sSubHdr  = S("sSubHdr",  fontName="Helvetica-Bold", fontSize=9,  textColor=NAVY,   alignment=TA_CENTER, spaceAfter=4)
sLabel   = S("sLabel",   fontName="Helvetica-Bold", fontSize=7.5, textColor=NAVY,  spaceAfter=1)
sValue   = S("sValue",   fontName="Helvetica",      fontSize=8,   textColor=BLACK, spaceAfter=1)
sSmall   = S("sSmall",   fontName="Helvetica",      fontSize=7,   textColor=GRAY,  spaceAfter=1)
sSection = S("sSection", fontName="Helvetica-Bold", fontSize=9,   textColor=WHITE, spaceAfter=2, alignment=TA_LEFT)
sDecl    = S("sDecl",    fontName="Helvetica",      fontSize=7.5, textColor=BLACK, leading=11, spaceAfter=3, alignment=TA_JUSTIFY)
sCenter  = S("sCenter",  fontName="Helvetica",      fontSize=8,   textColor=BLACK, alignment=TA_CENTER)
sBold    = S("sBold",    fontName="Helvetica-Bold", fontSize=8,   textColor=BLACK)
sRed     = S("sRed",     fontName="Helvetica-Bold", fontSize=7,   textColor=RED,   alignment=TA_CENTER)

def _p(text, style=sValue):
    return Paragraph(str(text) if text else "—", style)

def _val(v):
    return str(v).strip() if v and str(v).strip() not in ["", "None"] else "—"

# ── Section Header ─────────────────────────────────────────────────────
def section_header(text):
    return Table(
        [[Paragraph(f"  {text}", sSection)]],
        colWidths=[W - 40*mm],
        style=TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), NAVY),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
        ])
    )

# ── Labelled Field ─────────────────────────────────────────────────────
def field_row(label, value, label_w=60*mm, value_w=None):
    vw = value_w or (W - 40*mm - label_w)
    return Table(
        [[_p(label, sLabel), _p(value, sValue)]],
        colWidths=[label_w, vw],
        style=TableStyle([
            ("GRID", (0,0), (-1,-1), 0.4, HexColor("#d1d5db")),
            ("BACKGROUND", (0,0), (0,-1), LGRAY),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
        ])
    )

def two_fields(l1, v1, l2, v2, lw=55*mm):
    full = W - 40*mm
    vw = (full - 2*lw) / 2
    return Table(
        [[_p(l1, sLabel), _p(v1, sValue), _p(l2, sLabel), _p(v2, sValue)]],
        colWidths=[lw, vw, lw, vw],
        style=TableStyle([
            ("GRID", (0,0), (-1,-1), 0.4, HexColor("#d1d5db")),
            ("BACKGROUND", (0,0), (0,-1), LGRAY),
            ("BACKGROUND", (2,0), (2,-1), LGRAY),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
        ])
    )

def three_fields(l1,v1,l2,v2,l3,v3, lw=42*mm):
    full = W - 40*mm
    vw = (full - 3*lw) / 3
    return Table(
        [[_p(l1,sLabel),_p(v1,sValue),_p(l2,sLabel),_p(v2,sValue),_p(l3,sLabel),_p(v3,sValue)]],
        colWidths=[lw,vw,lw,vw,lw,vw],
        style=TableStyle([
            ("GRID",(0,0),(-1,-1),0.4,HexColor("#d1d5db")),
            ("BACKGROUND",(0,0),(0,-1),LGRAY),
            ("BACKGROUND",(2,0),(2,-1),LGRAY),
            ("BACKGROUND",(4,0),(4,-1),LGRAY),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),3),
            ("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("LEFTPADDING",(0,0),(-1,-1),4),
        ])
    )

# ── Photo Box ─────────────────────────────────────────────────────────
def photo_box(b64_str=None, label="Photo"):
    W_box = 32*mm
    H_box = 38*mm
    if b64_str:
        try:
            img_data = base64.b64decode(b64_str)
            pil_img = PILImage.open(io.BytesIO(img_data))
            pil_img.thumbnail((int(W_box*3), int(H_box*3)))
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            buf.seek(0)
            rl_img = RLImage(buf, width=W_box, height=H_box)
            return Table(
                [[rl_img]],
                colWidths=[W_box],
                rowHeights=[H_box],
                style=TableStyle([
                    ("BOX",(0,0),(-1,-1),1,NAVY),
                    ("ALIGN",(0,0),(-1,-1),"CENTER"),
                    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ])
            )
        except:
            pass
    # Empty box with label
    return Table(
        [[Paragraph(f"<br/><br/><br/>{label}<br/>(Paste Photo)", sCenter)]],
        colWidths=[W_box],
        rowHeights=[H_box],
        style=TableStyle([
            ("BOX",(0,0),(-1,-1),1,NAVY),
            ("BACKGROUND",(0,0),(-1,-1),LIGHT),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ])
    )

def signature_box(label="Signature"):
    W_box = 50*mm
    H_box = 22*mm
    return Table(
        [[Paragraph(f"<br/><br/>{label}", sCenter)]],
        colWidths=[W_box],
        rowHeights=[H_box],
        style=TableStyle([
            ("BOX",(0,0),(-1,-1),1,NAVY),
            ("BACKGROUND",(0,0),(-1,-1),HexColor("#fafafa")),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("VALIGN",(0,0),(-1,-1),"BOTTOM"),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ])
    )

# ── Data table helper ─────────────────────────────────────────────────
def data_table(headers, rows, col_widths=None):
    full = W - 40*mm
    if col_widths is None:
        cw = full / len(headers)
        col_widths = [cw] * len(headers)
    header_row = [Paragraph(h, S("th", fontName="Helvetica-Bold", fontSize=7, textColor=WHITE)) for h in headers]
    body = [[Paragraph(str(c) if c else "—", S("td", fontName="Helvetica", fontSize=7)) for c in r] for r in rows]
    ts = TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NAVY),
        ("GRID", (0,0), (-1,-1), 0.4, HexColor("#d1d5db")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT]),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
    ])
    return Table([header_row] + body, colWidths=col_widths, style=ts, repeatRows=1)

# ══════════════════════════════════════════════════════════════════════
# MAIN GENERATOR
# ══════════════════════════════════════════════════════════════════════
def generate_pdf(ss) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=15*mm, bottomMargin=15*mm,
        title=f"MSME Application — {_val(ss.enterprise_name)}",
        author="Union Bank of India",
    )

    story = []
    sp = lambda n=4: Spacer(1, n*mm)

    # ── Cover / Title Page ────────────────────────────────────────────
    # Bank header
    story.append(Table(
        [[
            Paragraph("<b>यूनियन बैंक / Union Bank of India</b>", S("bh", fontName="Helvetica-Bold", fontSize=16, textColor=WHITE, alignment=TA_CENTER)),
        ]],
        colWidths=[W - 40*mm],
        style=TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),NAVY),
            ("TOPPADDING",(0,0),(-1,-1),10),
            ("BOTTOMPADDING",(0,0),(-1,-1),10),
        ])
    ))
    story.append(sp(1))
    story.append(Table(
        [[Paragraph("एमएसएमई के लिए आवेदन प्रपत्र / APPLICATION FORM FOR MSMEs (Annexure I)", sSubHdr)]],
        colWidths=[W - 40*mm],
        style=TableStyle([
            ("BOX",(0,0),(-1,-1),1.5,NAVY),
            ("BACKGROUND",(0,0),(-1,-1),LIGHT),
            ("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ])
    ))
    story.append(sp(1))
    story.append(Table(
        [[Paragraph("जांचसूची के अनुसार दस्तावेज के साथ प्रस्तुत किया जाना / To be submitted along with documents as per the checklist", sCenter)]],
        colWidths=[W - 40*mm],
        style=TableStyle([
            ("BOX",(0,0),(-1,-1),0.5,GRAY),
            ("BACKGROUND",(0,0),(-1,-1),HexColor("#f9fafb")),
            ("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ])
    ))
    story.append(sp(1))
    story.append(_p(f"(कार्यालय उपयोग हेतु / For Office Use Only)  |  Application ID: {_val(ss.application_id)}  |  Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}", sSmall))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=6))
    story.append(sp(2))

    # ── Section 1–6: Basic Details ────────────────────────────────────
    story.append(section_header("ENTERPRISE INFORMATION (Sections 1–10)"))
    story.append(sp(1))
    story.append(field_row("1. Name of the Enterprise *", _val(ss.enterprise_name)))
    story.append(field_row("2. Registered Office Address", _val(ss.regd_office_address)))
    story.append(field_row("3. Address of Factory/Shop/Administrative Office", _val(ss.factory_address)))
    story.append(two_fields("4. Date of Establishment/Incorporation", _val(ss.date_of_establishment), "5. State", _val(ss.state)))
    story.append(two_fields("6. Premises Type", _val(ss.premises_type), "   Premises Details", _val(ss.premises_details)))
    story.append(sp(1))

    story.append(Table(
        [[_p("Telephone (Office)", sLabel), _p(_val(ss.telephone), sValue),
          _p("Mobile No.", sLabel), _p(_val(ss.mobile), sValue),
          _p("Email Address", sLabel), _p(_val(ss.email), sValue),
          _p("PAN No.", sLabel), _p(_val(ss.pan), sValue)]],
        colWidths=[28*mm,28*mm,20*mm,28*mm,22*mm,40*mm,16*mm,30*mm],
        style=TableStyle([
            ("GRID",(0,0),(-1,-1),0.4,HexColor("#d1d5db")),
            ("BACKGROUND",(0,0),(0,-1),LGRAY),
            ("BACKGROUND",(2,0),(2,-1),LGRAY),
            ("BACKGROUND",(4,0),(4,-1),LGRAY),
            ("BACKGROUND",(6,0),(6,-1),LGRAY),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),3),
            ("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("LEFTPADDING",(0,0),(-1,-1),3),
        ])
    ))
    story.append(sp(1))

    story.append(field_row("7. Constitution", _val(ss.constitution)))
    story.append(two_fields("8. Udyam Registration No.", _val(ss.udyam_no), "MSME Category", _val(ss.msme_category)))
    story.append(two_fields("8A. GST Registration No.", _val(ss.gst_no), "GST Registration Date", _val(ss.gst_date)))
    story.append(two_fields("8B. GeM Registration", _val(ss.gem_registered), "GeM No.", _val(ss.gem_no)))
    story.append(two_fields("8C. IEC Code (if applicable)", _val(ss.iec_code), "NIC Code", _val(ss.nic_code)))
    story.append(two_fields("9. City/District for Loan", _val(ss.city_loan), "10. Preferred Branch", _val(ss.branch_loan)))
    story.append(sp(1))
    story.append(two_fields("12. Activity (Existing Since)", _val(ss.activity_existing), "Proposed Activity", _val(ss.activity_proposed)))
    zed_info = f"{_val(ss.zed_rated)}" + (f" — Grade: {_val(ss.zed_grade)}" if ss.zed_rated == "Yes" else "")
    story.append(two_fields("13. ZED Rated?", zed_info, "Website", _val(getattr(ss, 'website', ''))))
    story.append(two_fields("No. of Employees", _val(getattr(ss, 'num_employees', '')), "Annual Turnover (Last Year, ₹ Lacs)", _val(getattr(ss, 'turnover_last_year', ''))))
    story.append(sp(3))

    # ── Section 11: Directors / Proprietors with Photos ───────────────
    story.append(section_header("11. NAME OF PROPRIETOR / PARTNERS / DIRECTORS"))
    story.append(sp(2))

    directors = ss.directors if ss.directors else []
    photos = ss.photos if ss.photos else {}

    for i, d in enumerate(directors):
        dname = _val(d.get("name",""))
        story.append(KeepTogether([
            Table(
                [[Paragraph(f"Person {i+1}: {dname}", S("dh", fontName="Helvetica-Bold", fontSize=8.5, textColor=NAVY))]],
                colWidths=[W - 40*mm],
                style=TableStyle([
                    ("BACKGROUND",(0,0),(-1,-1),LIGHT),
                    ("TOPPADDING",(0,0),(-1,-1),4),
                    ("BOTTOMPADDING",(0,0),(-1,-1),4),
                    ("LEFTPADDING",(0,0),(-1,-1),6),
                    ("BOX",(0,0),(-1,-1),0.5,NAVY),
                ])
            ),
            sp(1),
        ]))

        # Photo + fields side by side
        photo_widget = photo_box(photos.get(str(i)), label=f"Photo\n{dname}")
        info_table = Table(
            [
                [_p("Full Name", sLabel), _p(d.get("name",""), sValue),
                 _p("Date of Birth", sLabel), _p(_val(d.get("dob","")), sValue)],
                [_p("Father's / Spouse's Name", sLabel), _p(d.get("father_spouse",""), sValue),
                 _p("Mobile No.", sLabel), _p(d.get("mobile",""), sValue)],
                [_p("Academic Qualification", sLabel), _p(d.get("qualification",""), sValue),
                 _p("Category (SC/ST/OBC/etc.)", sLabel), _p(d.get("category",""), sValue)],
                [_p("PAN No.", sLabel), _p(d.get("pan",""), sValue),
                 _p("Aadhar / DIN No.", sLabel), _p(d.get("aadhar_din",""), sValue)],
                [_p("Telephone (Residence)", sLabel), _p(d.get("telephone",""), sValue),
                 _p("Experience (Years)", sLabel), _p(d.get("experience",""), sValue)],
                [_p("Residential Address", sLabel), _p(d.get("address",""), sValue), _p("", sLabel), _p("", sValue)],
            ],
            colWidths=[38*mm, 50*mm, 38*mm, 44*mm],
            style=TableStyle([
                ("GRID",(0,0),(-1,-1),0.4,HexColor("#d1d5db")),
                ("BACKGROUND",(0,0),(0,-1),LGRAY),
                ("BACKGROUND",(2,0),(2,-1),LGRAY),
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("TOPPADDING",(0,0),(-1,-1),3),
                ("BOTTOMPADDING",(0,0),(-1,-1),3),
                ("LEFTPADDING",(0,0),(-1,-1),3),
            ])
        )

        # Signature space below photo
        sig_widget = signature_box(f"Signature\n{dname}")

        combo = Table(
            [[photo_widget, info_table]],
            colWidths=[36*mm, W - 40*mm - 36*mm],
            style=TableStyle([
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("LEFTPADDING",(0,0),(-1,-1),0),
                ("RIGHTPADDING",(0,0),(-1,-1),0),
                ("TOPPADDING",(0,0),(-1,-1),0),
                ("BOTTOMPADDING",(0,0),(-1,-1),0),
            ])
        )
        story.append(combo)
        story.append(sp(1))

        # Signature line
        story.append(Table(
            [[sig_widget, Spacer(1,1), Paragraph(f"<b>Signature of {dname or 'Proprietor/Partner/Director'}</b><br/>"
                "<i>(To be signed at designated branch only)</i>", S("si", fontName="Helvetica", fontSize=7, textColor=GRAY, leading=10))]],
            colWidths=[52*mm, 10*mm, W - 40*mm - 62*mm],
            style=TableStyle([
                ("VALIGN",(0,0),(-1,-1),"BOTTOM"),
                ("LEFTPADDING",(0,0),(-1,-1),0),
                ("BOTTOMPADDING",(0,0),(-1,-1),2),
            ])
        ))
        story.append(sp(3))

    # ── Section 14: Associate Concerns ───────────────────────────────
    story.append(section_header("14. ASSOCIATE CONCERNS & NATURE OF ASSOCIATION"))
    story.append(sp(1))
    assoc = ss.associate_concerns or []
    if assoc and any(a.get("name") for a in assoc):
        rows = [[a.get("name",""), a.get("address",""), a.get("banking_with",""), a.get("nature",""), a.get("extent","")] for a in assoc]
        story.append(data_table(
            ["Name of Associate Concern","Address","Presently Banking With","Nature of Association","Extent of Interest"],
            rows,
            [40*mm, 50*mm, 40*mm, 35*mm, 42*mm]
        ))
    else:
        story.append(_p("— No associate concerns declared —", sSmall))
    story.append(sp(2))

    # ── Section 15 ────────────────────────────────────────────────────
    story.append(two_fields(
        "15. Relationship with Bank Officials/Director?",
        _val(ss.bank_relationship),
        "   Details",
        _val(ss.bank_relationship_details)
    ))
    story.append(sp(3))

    # ── Section 16: Existing Facilities ──────────────────────────────
    story.append(section_header("16. BANKING / CREDIT FACILITIES (EXISTING)  —  (₹ in Lakhs)"))
    story.append(sp(1))
    ef = ss.existing_facilities or []
    ef_rows = [[f.get("type",""), f.get("limit",""), f.get("outstanding",""),
                f.get("banking_with",""), f.get("securities",""),
                f.get("roi",""), f.get("repayment","")] for f in ef]
    story.append(data_table(
        ["Type of Facility","Limit (₹ Lacs)","Outstanding","Presently Banking With","Securities","Rate of Interest","Repayment Terms"],
        ef_rows,
        [32*mm,22*mm,22*mm,38*mm,32*mm,22*mm,39*mm]
    ))
    story.append(sp(1))
    story.append(two_fields("CIF No. (if with Union Bank)", _val(ss.cif_no), "", ""))
    story.append(sp(1))
    story.append(Table(
        [[Paragraph("It is certified that our unit has not availed any loan from any other Bank/Financial Institution in the past and I am not indebted to any other Bank/Financial Institution other than those mentioned in column No. 16 above.", sDecl)]],
        colWidths=[W - 40*mm],
        style=TableStyle([
            ("BOX",(0,0),(-1,-1),0.5,NAVY),
            ("BACKGROUND",(0,0),(-1,-1),LIGHT),
            ("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),6),
        ])
    ))
    story.append(sp(3))

    # ── Section 17: Proposed Facilities ──────────────────────────────
    story.append(section_header("17. CREDIT FACILITIES PROPOSED  —  (₹ in Lakhs)  * Mandatory"))
    story.append(sp(1))
    pf = ss.proposed_facilities or []
    pf_rows = [[f.get("type",""), f.get("amount",""), f.get("purpose",""),
                f.get("primary_security",""), f.get("collateral_offered","No")] for f in pf]
    story.append(data_table(
        ["Type of Facility","Amount * (₹ Lacs)","Purpose *","Primary Security (Approx. Value)","Collateral Security Offered?"],
        pf_rows,
        [30*mm,28*mm,38*mm,60*mm,51*mm]
    ))
    story.append(sp(3))

    # ── Section 18: Machinery ─────────────────────────────────────────
    mach = ss.machinery_details or []
    if any(m.get("machine") for m in mach):
        story.append(section_header("18. MACHINERY DETAILS (for Term Loan)"))
        story.append(sp(1))
        m_rows = [[m.get("machine",""), m.get("purpose",""), m.get("imported",""),
                   m.get("supplier",""), m.get("total_cost",""),
                   m.get("contribution",""), m.get("loan_req",""),
                   "Yes" if m.get("second_hand") else "No"] for m in mach]
        story.append(data_table(
            ["Machine/Equipment","Purpose","Imported/Indigenous","Supplier","Total Cost (₹)","Promoter Contribution","Loan Required","Second Hand?"],
            m_rows,
            [32*mm,24*mm,20*mm,28*mm,20*mm,22*mm,22*mm,18*mm]
        ))
        story.append(sp(3))

    # ── Section 19: Collateral ────────────────────────────────────────
    story.append(section_header("19. COLLATERAL SECURITY DETAILS"))
    story.append(sp(1))
    story.append(_p("* As per RBI guidelines, banks are not to take collateral security for loans up to ₹10 Lakhs to MSE Units.", sSmall))
    story.append(sp(1))
    story.append(_p("19(a) Third Party Guarantors:", sBold))
    story.append(sp(1))
    cg = ss.collateral_guarantors or []
    cg_rows = [[g.get("name",""), g.get("father_spouse",""), g.get("address",""),
                g.get("telephone",""), g.get("mobile",""),
                g.get("net_worth",""), g.get("aadhar",""), g.get("pan","")] for g in cg]
    story.append(data_table(
        ["Name of Guarantor","Father/Spouse","Residential Address","Tel.(Res.)","Mobile","Net Worth (₹ Lacs)","Aadhar No.","PAN No."],
        cg_rows,
        [28*mm,28*mm,38*mm,18*mm,20*mm,22*mm,22*mm,18*mm]
    ))
    story.append(sp(2))
    story.append(_p("19(b) Other Collateral Security:", sBold))
    story.append(sp(1))
    co = ss.collateral_others or []
    co_rows = [[o.get("owner",""), o.get("nature",""), o.get("details",""), o.get("value","")] for o in co]
    story.append(data_table(
        ["Name of Owner of Collateral","Nature","Details","Value (₹ in Lacs)"],
        co_rows,
        [50*mm, 40*mm, 65*mm, 32*mm]
    ))
    story.append(sp(3))

    # ── Section 20: Financial Performance ────────────────────────────
    story.append(section_header("20. PAST PERFORMANCE / FUTURE ESTIMATES  —  (₹ in Lakhs)"))
    story.append(sp(1))
    pd = ss.performance_data or {}
    story.append(data_table(
        ["", "Past Year-II (Actual)","Past Year-I (Actual)","Current Year (Estimate)","Next Year (Projection)"],
        [
            ["Net Sales",   _val(pd.get("past2_net","—")), _val(pd.get("past1_net","—")), _val(pd.get("current_net","—")), _val(pd.get("next_net","—"))],
            ["Net Profit",  _val(pd.get("past2_pro","—")), _val(pd.get("past1_pro","—")), _val(pd.get("current_pro","—")), _val(pd.get("next_pro","—"))],
            ["Capital/Net Worth", _val(pd.get("past2_cap","—")), _val(pd.get("past1_cap","—")), _val(pd.get("current_cap","—")), _val(pd.get("next_cap","—"))],
        ],
        [42*mm, 36*mm, 36*mm, 36*mm, 37*mm]
    ))
    story.append(sp(3))

    # ── Section 21: Suppliers & Customers ────────────────────────────
    story.append(section_header("21. TOP 5 SUPPLIERS & TOP 5 CUSTOMERS"))
    story.append(sp(1))
    story.append(_p("Top 5 Suppliers:", sBold))
    story.append(sp(1))
    sup = ss.top_suppliers or []
    story.append(data_table(
        ["S.No","Name","Contact Number","Associated Since","% of Business (Purchase)","Credit Terms"],
        [[str(i+1)] + [s.get("name",""), s.get("contact",""), s.get("since",""), s.get("pct",""), s.get("terms","")] for i, s in enumerate(sup)],
        [12*mm, 38*mm, 32*mm, 28*mm, 38*mm, 39*mm]
    ))
    story.append(sp(2))
    story.append(_p("Top 5 Customers:", sBold))
    story.append(sp(1))
    cus = ss.top_customers or []
    story.append(data_table(
        ["S.No","Name","Contact Number","Associated Since","% of Business (Sale)","Credit Terms"],
        [[str(i+1)] + [c.get("name",""), c.get("contact",""), c.get("since",""), c.get("pct",""), c.get("terms","")] for i, c in enumerate(cus)],
        [12*mm, 38*mm, 32*mm, 28*mm, 38*mm, 39*mm]
    ))
    story.append(sp(3))

    # ── Section 22: Statutory ─────────────────────────────────────────
    story.append(section_header("22. STATUS REGARDING STATUTORY OBLIGATIONS"))
    story.append(sp(1))
    stat = ss.statutory or {}
    story.append(data_table(
        ["Statutory Obligation","Complied? (Yes/No/N.A.)"],
        [
            ["1. Registration under Shops and Establishment Act", _val(stat.get("shops_act",""))],
            ["2. Registration under MSME (Provisional/Final)", _val(stat.get("msme_reg",""))],
            ["3. Drug License", _val(stat.get("drug_license",""))],
            ["4. Latest Sales Tax Return Filed", _val(stat.get("sales_tax",""))],
            ["5. Latest Income Tax Return Filed", _val(stat.get("income_tax",""))],
            ["6. Any Other Statutory Dues Remaining Outstanding", _val(stat.get("other_dues",""))],
        ],
        [120*mm, 67*mm]
    ))
    story.append(sp(3))

    # ── Section 23: ID & Address Proof ───────────────────────────────
    story.append(section_header("23. ID PROOF & ADDRESS PROOF"))
    story.append(sp(1))
    story.append(field_row("23(a) ID Proof Submitted (type)", ""))
    story.append(field_row("23(b) Address Proof Submitted (type)", ""))
    story.append(sp(3))

    # ── Declaration Page ─────────────────────────────────────────────
    story.append(PageBreak())
    story.append(section_header("DECLARATION"))
    story.append(sp(2))
    story.append(Table(
        [[Paragraph(
            "I/We hereby certify that all information furnished by me/us is true, correct and complete; that I/We have no borrowing "
            "arrangements for the unit except as indicated in the application; that there is no overdue/statutory dues against "
            "me/us/promoters except as indicated in the application; that no legal action has been/is being taken/initiated against "
            "me/us/promoters by any Bank/FIs. I/We shall furnish all other information that may be required in connection with my/our "
            "application; that this may also be exchanged by you with any agency you may deemed fit and you, your representatives or "
            "Reserve Bank of India or any other agency as authorized by you, may, at any time, inspect/verify my/our assets, books of "
            "accounts etc. in our factory/business premises as given above. You may take appropriate safeguards/action for recovery of "
            "Bank's dues including publication of defaulter's name in website/submission to RBI; further agree that my/our loan shall "
            "be governed by the rules of your Bank which may be in force from time to time.",
            sDecl
        )]],
        colWidths=[W - 40*mm],
        style=TableStyle([
            ("BOX",(0,0),(-1,-1),1,NAVY),
            ("BACKGROUND",(0,0),(-1,-1),LIGHT),
            ("TOPPADDING",(0,0),(-1,-1),8),
            ("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(0,0),(-1,-1),8),
            ("RIGHTPADDING",(0,0),(-1,-1),8),
        ])
    ))
    story.append(sp(4))

    # ── Photo + Signature blocks for all directors ────────────────────
    story.append(_p("PHOTOGRAPHS & SIGNATURES OF PROPRIETOR / PARTNER / DIRECTOR(S)", sBold))
    story.append(sp(1))
    story.append(_p(
        "Only one photo of proprietor/each partner/each working Director is required to be affixed. "
        "Each photo will be certified/attested by the Branch Team with name and signatures on the photograph with Branch stamp. "
        "The concerned staff will put his name below the signatures. To be signed at the designated branch only.",
        sSmall
    ))
    story.append(sp(2))

    # Build grid of photo+sig boxes
    directors = ss.directors or []
    photos = ss.photos or {}
    # Up to 4 per row
    row_size = 4
    for row_start in range(0, max(len(directors), 1), row_size):
        chunk = directors[row_start:row_start+row_size]
        # Pad to row_size if needed
        while len(chunk) < row_size:
            chunk.append(None)

        photo_cells = []
        sig_cells   = []
        name_cells  = []

        for ci, d in enumerate(chunk):
            real_idx = row_start + ci
            if d is not None:
                pb = photo_box(photos.get(str(real_idx)), label=f"Photo\n{d.get('name','')}")
                sb = signature_box(f"Signature")
                name = d.get("name","") or f"Person {real_idx+1}"
            else:
                pb = photo_box(None, "Space for Photo")
                sb = signature_box("Space for Signature")
                name = ""

            photo_cells.append(pb)
            sig_cells.append(sb)
            name_cells.append(Paragraph(name, S("nc", fontName="Helvetica", fontSize=7, textColor=NAVY, alignment=TA_CENTER)))

        col_w = (W - 40*mm) / row_size

        story.append(Table(
            [photo_cells, sig_cells, name_cells],
            colWidths=[col_w]*row_size,
            style=TableStyle([
                ("ALIGN",(0,0),(-1,-1),"CENTER"),
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("TOPPADDING",(0,0),(-1,-1),4),
                ("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("LEFTPADDING",(0,0),(-1,-1),3),
                ("RIGHTPADDING",(0,0),(-1,-1),3),
            ])
        ))
        story.append(sp(2))

    story.append(sp(3))

    # ── Date / Place / Signature line ─────────────────────────────────
    story.append(Table(
        [[
            _p("Date: ______________________", sValue),
            _p("Place: _____________________", sValue),
            _p("Applicant's Signature: ___________________________", sValue),
        ]],
        colWidths=[(W - 40*mm)/3]*3,
        style=TableStyle([
            ("BOX",(0,0),(-1,-1),0.5,NAVY),
            ("GRID",(0,0),(-1,-1),0.3,HexColor("#d1d5db")),
            ("TOPPADDING",(0,0),(-1,-1),8),
            ("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(0,0),(-1,-1),6),
        ])
    ))
    story.append(sp(4))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD))
    story.append(sp(2))
    story.append(_p(
        "केवल निर्दिष्ट शाखा में ही हस्ताक्षर किए जाएं / To be signed at the designated branch only",
        S("ft", fontName="Helvetica-Bold", fontSize=8, textColor=NAVY, alignment=TA_CENTER)
    ))
    story.append(sp(6))

    # ── Checklist Page ────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(section_header("DOCUMENTS CHECKLIST (For Loans upto ₹2.00 Crore)"))
    story.append(sp(2))

    checklist_items = [
        "Proof of Identity — Voter's ID card / Passport / Driving License / PAN card / Signature identification from present bankers of proprietor, partner or Director (if a company).",
        "Proof of Residence — Recent telephone bills, electricity bill, property tax receipt / Passport / Voter's ID card of proprietor, partner or Director (if a company).",
        "Proof of Business Address.",
        "Applicant should not be a defaulter in any Bank / FI.",
        "Last three years Balance Sheets of the units along with Income Tax / GST returns etc. (Applicable for all cases from ₹2 Lacs and above). For cases where total exposure from all Banks/FI is below ₹25 Lakh, unaudited balance sheets are also acceptable. For ₹25.00 Lakh and above, audited balance sheets are necessary.",
        "Memorandum and Articles of Association of the Company / Partnership Deed of partners etc.",
        "Assets and Liabilities statement of promoters and guarantors along with latest Income Tax Returns.",
        "Rent Agreement (if business premises on rent) and clearance from Pollution Control Board, if applicable.",
        "SSI / MSME Registration, if applicable.",
        "Projected Balance Sheets for the next two years in case of Working Capital limits and for the period of the loan in case of Term Loan (for all cases of ₹2 Lacs and above).",
        "In case of takeover of advances, sanction letters of facilities being availed from existing bankers/Financial Institutions along with detailed terms and conditions.",
        "Photocopies of lease deeds / title deeds of all properties being offered as primary and collateral securities.",
        "Position of accounts from the existing bankers and confirmation about the asset being Standard with them (in case of takeover).",
        "Copy of GST Returns, if applicable.",
        "The Audited Balance Sheets are necessary for limit of ₹25.00 Lacs and above.",
    ]

    for ci, item in enumerate(checklist_items):
        story.append(Table(
            [[
                Paragraph(f"☐", S("cb", fontName="Helvetica", fontSize=12, textColor=NAVY)),
                Paragraph(f"<b>{ci+1}.</b> {item}", S("cli", fontName="Helvetica", fontSize=7.5, leading=11)),
            ]],
            colWidths=[8*mm, W - 40*mm - 8*mm],
            style=TableStyle([
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("TOPPADDING",(0,0),(-1,-1),2),
                ("BOTTOMPADDING",(0,0),(-1,-1),2),
                ("LEFTPADDING",(0,0),(-1,-1),2),
                ("ROWBACKGROUNDS",(0,0),(-1,-1),[WHITE, LIGHT]),
            ])
        ))

    story.append(sp(2))
    story.append(Table(
        [[Paragraph("<i>The check list is only indicative and not exhaustive and depending upon the local requirements at different places addition could be made as per necessity.</i>", sSmall)]],
        colWidths=[W - 40*mm],
        style=TableStyle([
            ("BOX",(0,0),(-1,-1),0.5,GOLD),
            ("BACKGROUND",(0,0),(-1,-1),HexColor("#fffbeb")),
            ("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),6),
        ])
    ))
    story.append(sp(3))

    # ── Footer on last page ───────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
    story.append(sp(1))
    story.append(Table(
        [[
            _p(f"Application ID: {_val(ss.application_id)}", sSmall),
            _p(f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}", S("fs", fontName="Helvetica", fontSize=7, textColor=GRAY, alignment=TA_CENTER)),
            _p("Union Bank of India — MSME Credit Portal", S("fr", fontName="Helvetica", fontSize=7, textColor=GRAY, alignment=TA_RIGHT)),
        ]],
        colWidths=[(W-40*mm)/3]*3,
        style=TableStyle([("TOPPADDING",(0,0),(-1,-1),2)])
    ))

    # ── Build ─────────────────────────────────────────────────────────
    doc.build(story)
    buf.seek(0)
    return buf.read()
