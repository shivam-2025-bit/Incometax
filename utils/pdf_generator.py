"""
PDF Report Generator using ReportLab
Generates a beautiful, detailed tax report after payment.
"""
import os
import tempfile
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Brand colors
PRIMARY   = colors.HexColor('#1a56db')
ACCENT    = colors.HexColor('#059669')
WARNING   = colors.HexColor('#d97706')
LIGHT_BG  = colors.HexColor('#f0f4ff')
LIGHT_GRN = colors.HexColor('#f0fdf4')
DARK_TXT  = colors.HexColor('#0d1117')
MID_TXT   = colors.HexColor('#4a5568')
BORDER    = colors.HexColor('#e2e8f0')


def _fmt(n):
    try:
        return f"\u20b9{float(n):,.0f}"
    except:
        return str(n)


def _pct(n):
    return f"{n}%"


def generate_pdf(result):
    """Generate PDF and return path to temp file."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    tmp.close()

    doc = SimpleDocTemplate(
        tmp.name,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    story  = []

    # ── Custom Styles ──────────────────────────────────────────────────────────
    h1 = ParagraphStyle('H1', parent=styles['Normal'],
        fontSize=22, textColor=PRIMARY, fontName='Helvetica-Bold',
        spaceAfter=4, alignment=TA_CENTER)
    h2 = ParagraphStyle('H2', parent=styles['Normal'],
        fontSize=13, textColor=PRIMARY, fontName='Helvetica-Bold',
        spaceBefore=14, spaceAfter=6)
    h3 = ParagraphStyle('H3', parent=styles['Normal'],
        fontSize=11, textColor=DARK_TXT, fontName='Helvetica-Bold',
        spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle('Body', parent=styles['Normal'],
        fontSize=9.5, textColor=MID_TXT, leading=14)
    sub = ParagraphStyle('Sub', parent=styles['Normal'],
        fontSize=9, textColor=MID_TXT, alignment=TA_CENTER)
    rec_style = ParagraphStyle('Rec', parent=styles['Normal'],
        fontSize=10, textColor=colors.white, fontName='Helvetica-Bold',
        alignment=TA_CENTER, leading=16)
    small = ParagraphStyle('Small', parent=styles['Normal'],
        fontSize=8, textColor=MID_TXT, leading=12)

    # ── Header ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("₹ TaxCalcIndia", h1))
    story.append(Paragraph("Official Income Tax Report — FY 2025-26 (AY 2026-27)", sub))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY))
    story.append(Spacer(1, 8))

    # ── Report Meta ────────────────────────────────────────────────────────────
    now = datetime.now().strftime("%d %B %Y, %I:%M %p")
    inc = result.get('income', 0)
    age_map = {'below60': 'Below 60 years', '60-80': '60–80 years', 'above80': 'Above 80 years'}
    age = age_map.get(result.get('age', 'below60'), 'Below 60')

    meta_data = [
        ["Report Generated:", now, "Financial Year:", "2025-26 (AY 2026-27)"],
        ["Annual Income:", _fmt(inc), "Age Category:", age],
        ["Source:", "TaxCalcIndia.com", "Disclaimer:", "Estimates only. Consult a CA."],
    ]
    meta_table = Table(meta_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
    meta_table.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (0,-1), DARK_TXT),
        ('TEXTCOLOR', (1,0), (1,-1), MID_TXT),
        ('TEXTCOLOR', (2,0), (2,-1), DARK_TXT),
        ('TEXTCOLOR', (3,0), (3,-1), MID_TXT),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [LIGHT_BG, colors.white]),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # ── Recommendation Banner ─────────────────────────────────────────────────
    rec  = result.get('recommended', 'new')
    sav  = result.get('savings', 0)
    reason = result.get('recommendation_reason', '')
    rec_color = ACCENT if rec == 'new' else WARNING
    rec_label = "✅  NEW TAX REGIME RECOMMENDED" if rec == "new" else "✅  OLD TAX REGIME RECOMMENDED"

    rec_tbl = Table([[Paragraph(rec_label, rec_style)]], colWidths=[17*cm])
    rec_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), rec_color),
        ('ROUNDEDCORNERS', [8]),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(rec_tbl)
    story.append(Spacer(1, 6))
    story.append(Paragraph(reason, body))
    story.append(Spacer(1, 14))

    # ── Summary Comparison Table ───────────────────────────────────────────────
    story.append(Paragraph("📊 Tax Summary Comparison", h2))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 6))

    nr  = result.get('new_regime', {})
    or_ = result.get('old_regime', {})

    def highlight(val, is_rec):
        color = ACCENT if is_rec else DARK_TXT
        style = ParagraphStyle('V', parent=styles['Normal'],
            fontSize=9.5, textColor=color,
            fontName='Helvetica-Bold' if is_rec else 'Helvetica')
        return Paragraph(val, style)

    sum_header = [
        Paragraph("Item", ParagraphStyle('TH', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white)),
        Paragraph("New Regime", ParagraphStyle('TH', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_RIGHT)),
        Paragraph("Old Regime", ParagraphStyle('TH', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_RIGHT)),
    ]

    def r(txt): return ParagraphStyle('R', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT)
    def cell(txt, bold=False, color=DARK_TXT):
        return Paragraph(txt, ParagraphStyle('C', parent=styles['Normal'],
            fontSize=9, textColor=color,
            fontName='Helvetica-Bold' if bold else 'Helvetica'))
    def rcell(txt, bold=False, color=DARK_TXT):
        return Paragraph(txt, ParagraphStyle('RC', parent=styles['Normal'],
            fontSize=9, textColor=color, alignment=TA_RIGHT,
            fontName='Helvetica-Bold' if bold else 'Helvetica'))

    nr_rec  = rec == 'new'
    or_rec  = rec == 'old'

    sum_rows = [
        sum_header,
        [cell("Gross Income"), rcell(_fmt(inc)), rcell(_fmt(inc))],
        [cell("Standard Deduction"), rcell(_fmt(nr.get('standard_deduction',75000))), rcell(_fmt(or_.get('deductions',{}).get('standard_deduction',50000)))],
        [cell("Total Deductions"), rcell("—"), rcell(_fmt(or_.get('deductions',{}).get('total',0)))],
        [cell("Taxable Income"), rcell(_fmt(nr.get('taxable_income',0))), rcell(_fmt(or_.get('taxable_income',0)))],
        [cell("Base Tax"), rcell(_fmt(nr.get('base_tax',0))), rcell(_fmt(or_.get('base_tax',0)))],
        [cell("Section 87A Rebate"), rcell(f"- {_fmt(nr.get('rebate_87a',0))}"), rcell(f"- {_fmt(or_.get('rebate_87a',0))}")],
        [cell("Surcharge"), rcell(_fmt(nr.get('surcharge',0))), rcell(_fmt(or_.get('surcharge',0)))],
        [cell("Health & Ed. Cess (4%)"), rcell(_fmt(nr.get('cess',0))), rcell(_fmt(or_.get('cess',0)))],
        [cell("TOTAL TAX PAYABLE", bold=True, color=PRIMARY), rcell(_fmt(nr.get('total_tax',0)), bold=True, color=ACCENT if nr_rec else DARK_TXT), rcell(_fmt(or_.get('total_tax',0)), bold=True, color=ACCENT if or_rec else DARK_TXT)],
        [cell("Effective Tax Rate", bold=True), rcell(_pct(nr.get('effective_rate',0)), bold=True), rcell(_pct(or_.get('effective_rate',0)), bold=True)],
        [cell("Monthly Take-Home", bold=True, color=ACCENT), rcell(_fmt(nr.get('take_home_monthly',0)), bold=True, color=ACCENT), rcell(_fmt(or_.get('take_home_monthly',0)), bold=True, color=ACCENT)],
        [cell("Annual Take-Home", bold=True), rcell(_fmt(nr.get('take_home_annual',0)), bold=True), rcell(_fmt(or_.get('take_home_annual',0)), bold=True)],
    ]

    sum_tbl = Table(sum_rows, colWidths=[7*cm, 5*cm, 5*cm])
    sum_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
        ('BACKGROUND', (0,-3), (-1,-3), LIGHT_BG),
        ('BACKGROUND', (0,-4), (-1,-4), colors.HexColor('#fffbeb')),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 16))

    # ── Slab Breakdowns ────────────────────────────────────────────────────────
    for regime_key, regime_label in [('new_regime', 'New Regime'), ('old_regime', 'Old Regime')]:
        regime = result.get(regime_key, {})
        bk = regime.get('breakdown', [])
        if not bk:
            continue

        story.append(KeepTogether([
            Paragraph(f"📋 Slab-wise Breakdown — {regime_label}", h2),
            HRFlowable(width="100%", thickness=1, color=BORDER),
            Spacer(1, 6),
        ]))

        bk_header = [
            Paragraph("Income Slab", ParagraphStyle('BH', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white)),
            Paragraph("Rate", ParagraphStyle('BH', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER)),
            Paragraph("Taxable Amount", ParagraphStyle('BH', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_RIGHT)),
            Paragraph("Tax on Slab", ParagraphStyle('BH', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_RIGHT)),
        ]
        bk_rows = [bk_header]
        for row in bk:
            bk_rows.append([
                cell(row['slab']),
                Paragraph(row['rate'], ParagraphStyle('C', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)),
                rcell(_fmt(row['taxable_amount'])),
                rcell(_fmt(row['tax_on_slab'])),
            ])
        bk_rows.append([
            cell("Total Tax (before cess)", bold=True, color=PRIMARY),
            Paragraph("", styles['Normal']),
            Paragraph("", styles['Normal']),
            rcell(_fmt(regime.get('base_tax',0)), bold=True, color=PRIMARY),
        ])

        bk_tbl = Table(bk_rows, colWidths=[7*cm, 2*cm, 4*cm, 4*cm])
        bk_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), PRIMARY),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, LIGHT_BG]),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e0e7ff')),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(bk_tbl)
        story.append(Spacer(1, 14))

    # ── Tax Saving Tips ────────────────────────────────────────────────────────
    story.append(Paragraph("💡 Personalised Tax Saving Tips", h2))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 6))

    ded = or_.get('deductions', {})
    tips = []
    if ded.get('section_80c', 0) < 150_000:
        remaining = 150_000 - ded.get('section_80c', 0)
        tips.append(f"• <b>Section 80C:</b> You can invest ₹{remaining:,.0f} more in PPF, ELSS, NSC, or LIC premium to save up to ₹{remaining*0.30:,.0f} in tax under Old Regime.")
    if ded.get('section_80d', 0) < 25_000:
        tips.append("• <b>Section 80D:</b> Purchase health insurance to claim up to ₹25,000 deduction (₹50,000 for senior citizens).")
    if ded.get('hra', 0) == 0:
        tips.append("• <b>HRA Exemption:</b> If you pay rent and are salaried, claim HRA exemption under the Old Regime to reduce taxable income.")
    tips.append("• <b>NPS (80CCD):</b> Contribute to NPS for an additional ₹50,000 deduction under Section 80CCD(1B) over and above 80C limit.")
    tips.append("• <b>Home Loan:</b> Interest on home loan is deductible up to ₹2L under Section 24(b) in the Old Regime.")
    if not tips:
        tips.append("• You appear to be utilising deductions well. Consider NPS for additional savings.")

    for tip in tips:
        story.append(Paragraph(tip, body))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 14))

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "⚠️ <b>Disclaimer:</b> This report is for informational purposes only and does not constitute professional tax advice. "
        "Tax calculations are based on FY 2025-26 slabs published under the Finance Act. "
        "Please consult a qualified Chartered Accountant for tax filing.",
        small))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Generated by TaxCalcIndia.com | {now} | Payment verified via Razorpay", small))

    doc.build(story)
    return tmp.name
