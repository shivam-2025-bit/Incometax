"""
AI Summary using HuggingFace Inference API
Model: facebook/bart-large-cnn (summarisation)
Falls back to rule-based summary if API unavailable.
"""
import os
import requests

HF_API_TOKEN = os.environ.get('HF_API_TOKEN', '')
HF_MODEL     = "facebook/bart-large-cnn"
HF_API_URL   = f"https://api-inference.huggingface.co/models/{HF_MODEL}"


def _fmt(n):
    """Format number as Indian rupees."""
    try:
        return f"₹{float(n):,.0f}"
    except:
        return str(n)


def _build_text(result):
    """Convert tax result dict into plain English for summarisation."""
    inc  = result.get('income', 0)
    age  = result.get('age', 'below60')
    rec  = result.get('recommended', 'new')
    sav  = result.get('savings', 0)
    reason = result.get('recommendation_reason', '')

    nr = result.get('new_regime', {})
    or_ = result.get('old_regime', {})

    age_label = {'below60': 'below 60 years', '60-80': '60 to 80 years', 'above80': 'above 80 years'}.get(age, age)

    text = (
        f"The taxpayer has an annual income of {_fmt(inc)} and is in the age group of {age_label}. "
        f"Under the New Tax Regime for FY 2025-26, the taxable income after standard deduction of "
        f"{_fmt(nr.get('standard_deduction',0))} is {_fmt(nr.get('taxable_income',0))}. "
        f"The base tax computed is {_fmt(nr.get('base_tax',0))}. "
        f"Section 87A rebate of {_fmt(nr.get('rebate_87a',0))} is applied. "
        f"After adding surcharge of {_fmt(nr.get('surcharge',0))} and 4% health and education cess of "
        f"{_fmt(nr.get('cess',0))}, the total tax payable under the New Regime is {_fmt(nr.get('total_tax',0))}. "
        f"The effective tax rate is {nr.get('effective_rate',0)}%. "
        f"Monthly take-home salary under the New Regime is {_fmt(nr.get('take_home_monthly',0))}. "
        f"Under the Old Tax Regime, total deductions including standard deduction, 80C, 80D, HRA and others "
        f"amount to {_fmt(or_.get('deductions',{}).get('total',0))}. "
        f"Taxable income is {_fmt(or_.get('taxable_income',0))}. "
        f"Total tax payable under the Old Regime is {_fmt(or_.get('total_tax',0))} "
        f"at an effective rate of {or_.get('effective_rate',0)}%. "
        f"Monthly take-home under the Old Regime is {_fmt(or_.get('take_home_monthly',0))}. "
        f"The recommended regime is the {rec.upper()} TAX REGIME which saves {_fmt(sav)} in taxes. "
        f"{reason}"
    )
    return text


def get_ai_summary(result):
    """
    Generate a concise AI summary of the tax report.
    Uses HuggingFace BART if API token is available,
    otherwise returns a high-quality rule-based summary.
    """
    text = _build_text(result)

    if HF_API_TOKEN:
        try:
            headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
            payload = {
                "inputs": text,
                "parameters": {
                    "max_length": 200,
                    "min_length": 80,
                    "do_sample": False
                }
            }
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                output = response.json()
                if isinstance(output, list) and output:
                    return output[0].get('summary_text', _fallback_summary(result))
        except Exception:
            pass  # Fall through to rule-based

    return _fallback_summary(result)


def _fallback_summary(result):
    """High-quality rule-based summary when HF API is unavailable."""
    inc  = result.get('income', 0)
    rec  = result.get('recommended', 'new')
    sav  = result.get('savings', 0)
    nr   = result.get('new_regime', {})
    or_  = result.get('old_regime', {})

    rec_label = "New Tax Regime" if rec == "new" else "Old Tax Regime"
    other_label = "Old Tax Regime" if rec == "new" else "New Tax Regime"
    rec_tax   = nr['total_tax'] if rec == "new" else or_['total_tax']
    other_tax = or_['total_tax'] if rec == "new" else nr['total_tax']

    if rec_tax == 0:
        tax_line = "Your income falls within the exempt limit — you pay zero tax."
    else:
        tax_line = (
            f"You pay ₹{rec_tax:,.0f} under the {rec_label} vs ₹{other_tax:,.0f} "
            f"under the {other_label}, saving ₹{sav:,.0f}."
        )

    return (
        f"Based on your annual income of ₹{inc:,.0f}, the {rec_label} is recommended for FY 2025-26. "
        f"{tax_line} "
        f"Your monthly take-home is ₹{nr['take_home_monthly']:,.0f} (New) or "
        f"₹{or_['take_home_monthly']:,.0f} (Old). "
        f"Effective tax rates: {nr['effective_rate']}% (New) | {or_['effective_rate']}% (Old). "
        f"Tip: Maximise Section 80C investments (up to ₹1.5L) and NPS contributions to reduce tax under the Old Regime."
    )
