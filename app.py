from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import pandas as pd
import requests
import io
import os

app = Flask(__name__)
CORS(app)

# ──────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────
FAST2SMS_API_KEY = "Plg2rVEOYs9u1yd60wvSF4hAQzCpjmcTZML3KiUtekGo7qJbHfyxuVBJ391fwG4AUao0THYncgdLiEvK"
ADMIN_MOBILE = "9088050201"
REPORT_FEE = 99

payment_store = {}

# ──────────────────────────────────────────────────────────
# TAX CALCULATION LOGIC
# ──────────────────────────────────────────────────────────
TAX_SLABS = [
    (300000,  600000, 0.05),
    (600000,  900000, 0.10),
    (900000, 1200000, 0.15),
    (1200000, 1500000, 0.20),
    (1500000, float('inf'), 0.30),
]

SLAB_LABELS = [
    "₹0 – ₹3L",
    "₹3L – ₹6L",
    "₹6L – ₹9L",
    "₹9L – ₹12L",
    "₹12L – ₹15L",
    "Above ₹15L",
]

def compute_tax(income: float) -> dict:
    tax = 0.0
    slab_details = []

    slab_details.append({
        "slab": SLAB_LABELS[0],
        "rate": "0%",
        "taxable_amount": min(income, 300000),
        "tax_on_slab": 0.0
    })

    for idx, (lower, upper, rate) in enumerate(TAX_SLABS):
        if income > lower:
            taxable = min(income, upper) - lower
            tax_on_slab = taxable * rate
            tax += tax_on_slab
            slab_details.append({
                "slab": SLAB_LABELS[idx + 1],
                "rate": f"{int(rate*100)}%",
                "taxable_amount": round(taxable),
                "tax_on_slab": round(tax_on_slab)
            })
        else:
            slab_details.append({
                "slab": SLAB_LABELS[idx + 1],
                "rate": f"{int(rate*100)}%",
                "taxable_amount": 0,
                "tax_on_slab": 0
            })

    tax_before_cess = round(tax)
    rebate_applied = income <= 700000
    if rebate_applied:
        tax_before_cess = 0

    cess = round(tax_before_cess * 0.04)
    final_tax = tax_before_cess + cess

    return {
        "income": income,
        "tax_before_cess": tax_before_cess,
        "cess": cess,
        "final_tax": final_tax,
        "rebate_applied": rebate_applied,
        "slab_details": slab_details
    }

def send_sms_to_admin(name: str, mobile: str, utr: str, income: float, tax: float) -> bool:
    if not FAST2SMS_API_KEY:
        return False
    message = (
        f"TaxCalc Alert: New payment. Name: {name}, Mobile: {mobile}, UTR: {utr}, "
        f"Income: Rs{int(income)}, Tax: Rs{int(tax)}. Verify at /approve/{mobile}"
    )
    url = "https://www.fast2sms.com/dev/bulkV2"
    headers = {"authorization": FAST2SMS_API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
    payload = {"route": "q", "message": message, "language": "english", "flash": 0, "numbers": ADMIN_MOBILE}
    try:
        resp = requests.post(url, headers=headers, data=payload, timeout=10)
        return bool(resp.json().get("return"))
    except:
        return False

# ──────────────────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────────────────

# NEW ROUTE: Serve the HTML page
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json()
    income = data.get("income")
    if income is None or not isinstance(income, (int, float)) or income < 0:
        return jsonify({"error": "Please provide a valid positive income value."}), 400
    return jsonify(compute_tax(float(income))), 200

@app.route("/payment-request", methods=["POST"])
def payment_request():
    data = request.get_json()
    name = data.get("name", "").strip()
    mobile = data.get("mobile", "").strip()
    utr = data.get("utr", "").strip()
    income = data.get("income", 0)
    final_tax = data.get("final_tax", 0)

    if not name or not mobile or not utr:
        return jsonify({"error": "Name, mobile, and UTR are required."}), 400
    if not mobile.isdigit() or len(mobile) != 10:
        return jsonify({"error": "Mobile must be a 10-digit number."}), 400

    payment_store[mobile] = {
        "name": name, "mobile": mobile, "utr": utr,
        "income": income, "final_tax": final_tax, "approved": False
    }
    sms_sent = send_sms_to_admin(name, mobile, utr, income, final_tax)
    return jsonify({"message": "Payment details received. Admin will verify shortly.", "sms_sent": sms_sent}), 200

@app.route("/status/<mobile>", methods=["GET"])
def check_status(mobile):
    record = payment_store.get(mobile)
    if not record:
        return jsonify({"error": "No payment request found for this mobile number."}), 404
    return jsonify({"mobile": mobile, "name": record["name"], "approved": record["approved"]}), 200

@app.route("/approve/<mobile>", methods=["GET"])
def approve_payment(mobile):
    record = payment_store.get(mobile)
    if not record:
        return f"<h2>❌ No record found for mobile: {mobile}</h2>", 404
    payment_store[mobile]["approved"] = True
    return f"<h2>✅ Payment Approved for {record['name']}</h2>", 200

@app.route("/download/<mobile>", methods=["GET"])
def download_report(mobile):
    record = payment_store.get(mobile)
    if not record:
        return jsonify({"error": "No payment request found."}), 404
    if not record["approved"]:
        return jsonify({"error": "Payment pending approval."}), 403

    income = record["income"]
    tax_data = compute_tax(float(income))
    
    rows = []
    for slab in tax_data["slab_details"]:
        rows.append({"Income Slab": slab["slab"], "Tax Rate": slab["rate"], "Taxable Amount (₹)": slab["taxable_amount"], "Tax on Slab (₹)": slab["tax_on_slab"]})
    df_slabs = pd.DataFrame(rows)

    summary_data = {
        "Field": ["Name", "Mobile", "Gross Annual Income (₹)", "Tax Before Cess (₹)", "Health & Education Cess 4% (₹)", "Section 87A Rebate Applied", "Final Tax Payable (₹)", "UTR"],
        "Value": [record["name"], mobile, f"₹{int(income):,}", f"₹{int(tax_data['tax_before_cess']):,}", f"₹{int(tax_data['cess']):,}", "Yes" if tax_data["rebate_applied"] else "No", f"₹{int(record['final_tax']):,}", record["utr"]]
    }
    df_summary = pd.DataFrame(summary_data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_summary.to_excel(writer, index=False, sheet_name="Tax Summary")
        df_slabs.to_excel(writer, index=False, sheet_name="Slab Breakdown")
    output.seek(0)

    filename = f"TaxReport_{mobile}.xlsx"
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=filename)

@app.route("/admin", methods=["GET"])
def admin_dashboard():
    rows = ""
    for mobile, r in payment_store.items():
        status = "✅ Approved" if r["approved"] else "⏳ Pending"
        btn = "" if r["approved"] else f"<a href='/approve/{mobile}'>Approve</a>"
        rows += f"<tr><td>{r['name']}</td><td>{mobile}</td><td>{r['utr']}</td><td>{status}</td><td>{btn}</td></tr>"
    
    return f"""
    <html><body><h1>Admin Dashboard</h1>
    <table border="1"><tr><th>Name</th><th>Mobile</th><th>UTR</th><th>Status</th><th>Action</th></tr>{rows}</table>
    </body></html>
    """, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
