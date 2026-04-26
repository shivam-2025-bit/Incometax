"""
Tax Engine — FY 2025-26 (AY 2026-27)
Covers: New Regime, Old Regime, 87A Rebate, Surcharge, 4% Cess
"""

def _surcharge_rate(income):
    if income > 50_000_000:  return 0.37
    if income > 20_000_000:  return 0.25
    if income > 10_000_000:  return 0.15
    if income > 5_000_000:   return 0.10
    return 0.0

def _add_surcharge_cess(base_tax, income):
    sr   = _surcharge_rate(income)
    sur  = round(base_tax * sr, 2)
    cess = round((base_tax + sur) * 0.04, 2)
    total = round(base_tax + sur + cess, 2)
    return total, round(sur, 2), round(cess, 2)

# ── New Regime ─────────────────────────────────────────────────────────────────
def _new_regime(income):
    """
    FY 2025-26 New Regime Slabs:
    0 – 4L      : 0%
    4L – 8L     : 5%
    8L – 12L    : 10%
    12L – 16L   : 15%
    16L – 20L   : 20%
    20L – 24L   : 25%
    Above 24L   : 30%
    87A rebate  : Full rebate if income ≤ 12L (effective tax = 0)
    Standard deduction: ₹75,000 allowed under new regime
    """
    STANDARD_DED = 75_000
    taxable = max(0, income - STANDARD_DED)

    slabs = [
        (400_000,  0.00, "₹0 – ₹4 Lakh"),
        (800_000,  0.05, "₹4L – ₹8 Lakh"),
        (1_200_000, 0.10, "₹8L – ₹12 Lakh"),
        (1_600_000, 0.15, "₹12L – ₹16 Lakh"),
        (2_000_000, 0.20, "₹16L – ₹20 Lakh"),
        (2_400_000, 0.25, "₹20L – ₹24 Lakh"),
        (float('inf'), 0.30, "Above ₹24 Lakh"),
    ]

    tax = 0.0
    breakdown = []
    prev = 0

    for upper, rate, label in slabs:
        if taxable <= prev:
            break
        chunk = min(taxable, upper) - prev
        slab_tax = chunk * rate
        tax += slab_tax
        if chunk > 0:
            breakdown.append({
                "slab": label,
                "rate": f"{int(rate*100)}%",
                "taxable_amount": round(chunk, 2),
                "tax_on_slab": round(slab_tax, 2),
            })
        prev = upper

    # 87A Rebate — full rebate if taxable income ≤ 12L
    rebate = 0.0
    if taxable <= 1_200_000:
        rebate = tax
        tax = 0.0

    total, surcharge, cess = _add_surcharge_cess(tax, income)

    return {
        "standard_deduction": STANDARD_DED,
        "taxable_income": round(taxable, 2),
        "base_tax": round(tax + rebate, 2),
        "rebate_87a": round(rebate, 2),
        "tax_after_rebate": round(tax, 2),
        "surcharge": surcharge,
        "cess": cess,
        "total_tax": total,
        "take_home_annual": round(income - total, 2),
        "take_home_monthly": round((income - total) / 12, 2),
        "effective_rate": round((total / income * 100), 2) if income > 0 else 0,
        "breakdown": breakdown,
    }

# ── Old Regime ─────────────────────────────────────────────────────────────────
def _old_regime(income, age, d80c, d80d, hra, other):
    """
    Old Regime slabs (FY 2025-26):
    Below 60:  0-2.5L=0%, 2.5-5L=5%, 5-10L=20%, >10L=30%
    60-80:     0-3L=0%,   3-5L=5%,   5-10L=20%, >10L=30%
    Above 80:  0-5L=0%,              5-10L=20%, >10L=30%
    87A rebate: ₹12,500 if net income ≤ 5L
    """
    # Exemption limits
    if age == "above80":
        basic_exemption = 500_000
        slab_defs = [
            (500_000,  0.00, "₹0 – ₹5 Lakh (Exempt)"),
            (1_000_000, 0.20, "₹5L – ₹10 Lakh"),
            (float('inf'), 0.30, "Above ₹10 Lakh"),
        ]
    elif age == "60-80":
        basic_exemption = 300_000
        slab_defs = [
            (300_000,  0.00, "₹0 – ₹3 Lakh (Exempt)"),
            (500_000,  0.05, "₹3L – ₹5 Lakh"),
            (1_000_000, 0.20, "₹5L – ₹10 Lakh"),
            (float('inf'), 0.30, "Above ₹10 Lakh"),
        ]
    else:
        basic_exemption = 250_000
        slab_defs = [
            (250_000,  0.00, "₹0 – ₹2.5 Lakh (Exempt)"),
            (500_000,  0.05, "₹2.5L – ₹5 Lakh"),
            (1_000_000, 0.20, "₹5L – ₹10 Lakh"),
            (float('inf'), 0.30, "Above ₹10 Lakh"),
        ]

    # Deductions
    ded_80c   = min(d80c, 150_000)
    ded_80d   = min(d80d, 50_000)   # 50k for senior, 25k for others
    ded_hra   = hra
    ded_other = other
    total_deductions = ded_80c + ded_80d + ded_hra + ded_other
    STANDARD_DED = 50_000
    total_deductions += STANDARD_DED

    taxable = max(0, income - total_deductions)

    tax = 0.0
    breakdown = []
    prev = 0

    for upper, rate, label in slab_defs:
        if taxable <= prev:
            break
        chunk = min(taxable, upper) - prev
        slab_tax = chunk * rate
        tax += slab_tax
        if chunk > 0:
            breakdown.append({
                "slab": label,
                "rate": f"{int(rate*100)}%",
                "taxable_amount": round(chunk, 2),
                "tax_on_slab": round(slab_tax, 2),
            })
        prev = upper

    # 87A rebate
    rebate = 0.0
    if taxable <= 500_000:
        rebate = min(tax, 12_500)
        tax = max(0.0, tax - rebate)

    total, surcharge, cess = _add_surcharge_cess(tax, income)

    return {
        "standard_deduction": STANDARD_DED,
        "deductions": {
            "section_80c": round(ded_80c, 2),
            "section_80d": round(ded_80d, 2),
            "hra": round(ded_hra, 2),
            "other": round(ded_other, 2),
            "standard_deduction": STANDARD_DED,
            "total": round(total_deductions, 2),
        },
        "taxable_income": round(taxable, 2),
        "base_tax": round(tax + rebate, 2),
        "rebate_87a": round(rebate, 2),
        "tax_after_rebate": round(tax, 2),
        "surcharge": surcharge,
        "cess": cess,
        "total_tax": total,
        "take_home_annual": round(income - total, 2),
        "take_home_monthly": round((income - total) / 12, 2),
        "effective_rate": round((total / income * 100), 2) if income > 0 else 0,
        "breakdown": breakdown,
    }

# ── Master Calculate ───────────────────────────────────────────────────────────
def calculate_tax(income, age, d80c, d80d, hra, other):
    new = _new_regime(income)
    old = _old_regime(income, age, d80c, d80d, hra, other)

    savings = abs(new['total_tax'] - old['total_tax'])
    recommended = "new" if new['total_tax'] <= old['total_tax'] else "old"

    # Human-readable recommendation reason
    if new['total_tax'] == 0 and old['total_tax'] == 0:
        reason = "Both regimes result in zero tax — your income is within exempt limits."
    elif recommended == "new":
        reason = (
            f"New Regime saves you ₹{savings:,.0f} more this year. "
            f"New Regime tax: ₹{new['total_tax']:,.0f} vs Old Regime: ₹{old['total_tax']:,.0f}. "
            f"Switch to New Regime for lower taxes."
        )
    else:
        reason = (
            f"Old Regime saves you ₹{savings:,.0f} more this year because your deductions "
            f"(₹{old['deductions']['total']:,.0f}) reduce your taxable income significantly. "
            f"Old Regime tax: ₹{old['total_tax']:,.0f} vs New Regime: ₹{new['total_tax']:,.0f}."
        )

    return {
        "income": income,
        "age": age,
        "new_regime": new,
        "old_regime": old,
        "recommended": recommended,
        "savings": round(savings, 2),
        "recommendation_reason": reason,
    }
