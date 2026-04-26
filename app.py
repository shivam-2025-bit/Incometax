from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

def calculate_new_regime(income):
    slabs = [
        (400000, 0.00),
        (400000, 0.05),
        (400000, 0.10),
        (400000, 0.15),
        (400000, 0.20),
        (float('inf'), 0.30),
    ]
    thresholds = [0, 400000, 800000, 1200000, 1600000, 2000000, float('inf')]
    tax = 0
    breakdown = []
    for i, (limit, rate) in enumerate(slabs):
        lower = thresholds[i]
        upper = thresholds[i + 1]
        if income <= lower:
            break
        taxable = min(income, upper) - lower
        slab_tax = taxable * rate
        tax += slab_tax
        if rate > 0:
            breakdown.append({
                "slab": f"₹{lower//100000}L – ₹{upper//100000}L" if upper != float('inf') else f"Above ₹{lower//100000}L",
                "rate": f"{int(rate*100)}%",
                "taxable": taxable,
                "tax": slab_tax
            })
    # 87A rebate: if income <= 12,00,000 => full rebate (no tax)
    rebate = 0
    if income <= 1200000:
        rebate = tax
        tax = 0
    return tax, rebate, breakdown

def calculate_old_regime(income, age, deductions):
    basic_exemption = 250000
    if age == "60-80":
        basic_exemption = 300000
    elif age == "above80":
        basic_exemption = 500000

    taxable = max(0, income - deductions - basic_exemption)
    slabs = []
    tax = 0
    breakdown = []

    if age == "above80":
        ranges = [(500000, 0.20), (500000, 0.30), (float('inf'), 0.30)]
        thresholds = [500000, 1000000, float('inf')]
        for i, (limit, rate) in enumerate(ranges):
            lower = basic_exemption + (thresholds[i-1] if i > 0 else 0)
            if income <= basic_exemption:
                break
    else:
        tax_income = income - deductions
        tax_income = max(0, tax_income)
        tax = 0
        breakdown = []
        slabs_def = [
            (basic_exemption, 0),
            (basic_exemption + 250000, 0.05),
            (basic_exemption + 750000, 0.20),
            (float('inf'), 0.30),
        ]
        prev = 0
        for i, (upper, rate) in enumerate(slabs_def):
            if tax_income <= prev:
                break
            chunk = min(tax_income, upper) - prev
            slab_tax = chunk * rate
            tax += slab_tax
            if rate > 0 and chunk > 0:
                breakdown.append({
                    "slab": f"₹{prev//100000}L – {'₹'+str(upper//100000)+'L' if upper != float('inf') else 'Above'}",
                    "rate": f"{int(rate*100)}%",
                    "taxable": chunk,
                    "tax": slab_tax
                })
            prev = upper

    # 87A rebate for old regime: income <= 5L
    rebate = 0
    net_income = income - deductions
    if net_income <= 500000:
        rebate = min(tax, 12500)
        tax = max(0, tax - rebate)

    return tax, rebate, breakdown

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        income = float(data.get('income', 0))
        age = data.get('age', 'below60')
        regime = data.get('regime', 'new')
        d80c = float(data.get('d80c', 0))
        d80d = float(data.get('d80d', 0))
        hra = float(data.get('hra', 0))
        other = float(data.get('other', 0))

        if income < 0:
            return jsonify({"error": "Income cannot be negative"}), 400

        total_deductions = min(d80c, 150000) + min(d80d, 25000) + hra + other

        new_tax, new_rebate, new_breakdown = calculate_new_regime(income)
        old_tax, old_rebate, old_breakdown = calculate_old_regime(income, age, total_deductions)

        surcharge_rate = 0
        if income > 5000000:
            surcharge_rate = 0.10
        if income > 10000000:
            surcharge_rate = 0.15
        if income > 20000000:
            surcharge_rate = 0.25
        if income > 50000000:
            surcharge_rate = 0.37

        def add_cess(tax):
            surcharge = tax * surcharge_rate
            cess = (tax + surcharge) * 0.04
            return round(tax + surcharge + cess, 2), round(surcharge, 2), round(cess, 2)

        new_total, new_surcharge, new_cess = add_cess(new_tax)
        old_total, old_surcharge, old_cess = add_cess(old_tax)

        result = {
            "income": income,
            "new_regime": {
                "base_tax": round(new_tax, 2),
                "rebate": round(new_rebate, 2),
                "surcharge": new_surcharge,
                "cess": new_cess,
                "total_tax": new_total,
                "effective_rate": round((new_total / income * 100), 2) if income > 0 else 0,
                "take_home": round(income - new_total, 2),
                "breakdown": new_breakdown
            },
            "old_regime": {
                "deductions": round(total_deductions, 2),
                "base_tax": round(old_tax, 2),
                "rebate": round(old_rebate, 2),
                "surcharge": old_surcharge,
                "cess": old_cess,
                "total_tax": old_total,
                "effective_rate": round((old_total / income * 100), 2) if income > 0 else 0,
                "take_home": round(income - old_total, 2),
                "breakdown": old_breakdown
            },
            "recommended": "new" if new_total <= old_total else "old",
            "savings": round(abs(new_total - old_total), 2)
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False)
