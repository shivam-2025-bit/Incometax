"""
India Income Tax Calculator — Flask Backend
FY 2025-26 | New Tax Regime
Deploy: Render.com
"""
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import pandas as pd
import requests
import io
import os

# ✅ FIXED: Use __name__ (critical fix)
app = Flask(__name__)
CORS(app)

# ──────────────────────────────────────────────────────────
# CONFIG — Load from environment variables (SECURE)
# ──────────────────────────────────────────────────────────
FAST2SMS_API_KEY = os.environ.get("FAST2SMS_API_KEY", "")
ADMIN_MOBILE = os.environ.get("ADMIN_MOBILE", "9088050201")
REPORT_FEE = 99

# ──────────────────────────────────────────────────────────
# IN-MEMORY STORAGE (for demo; use DB in production)
# ──────────────────────────────────────────────────────────
payment_store = {}

# ──────────────────────────────────────────────────────────
# TAX CALCULATION LOGIC — New Tax Regime FY 2025-26
# ──────────────────────────────────────────────────────────
TAX_SLABS = [
    (300000, 600000, 0.05),
    (600000, 900000, 0.10),
    (900000, 1200000, 0.15),
    (1200000, 1500000, 0.20),
    (1500000, float('inf'), 0.30),
]

SLAB_LABELS = [
    "₹0 – ₹3L", "₹3L – ₹6L", "₹6L – ₹9L",
    "₹9L – ₹12L", "₹12L – ₹15L", "Above ₹15L",
]

def compute_tax(income: float) -> dict:
    tax = 0.0
    slab_details = []
    
    # Slab 0: 0–3L → 0%
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

# ──────────────────────────────────────────────────────────
# SMS HELPER — Fast2SMS
# ──────────────────────────────────────────────────────────
def send_sms_to_admin(name: str, mobile: str, utr: str, income: float, tax: float) -> bool:
    if not FAST2SMS_API_KEY:
        print(f"[SMS SKIPPED] No API key. Alert: {name} | {mobile}")
        return False
    
    message = (
        f"TaxCalc Alert: New payment. Name: {name}, Mobile: {mobile}, "
        f"UTR: {utr}, Income: Rs{int(income)}, Tax: Rs{int(tax)}. "
        f"Approve: /approve/{mobile}"
    )

    url = "https://www.fast2sms.com/dev/bulkV2"
    headers = {
        "authorization": FAST2SMS_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "route": "q",
        "message": message,
        "language": "english",
        "flash": 0,
        "numbers": ADMIN_MOBILE
    }

    try:
        resp = requests.post(url, headers=headers, data=payload, timeout=10)
        result = resp.json()
        if result.get("return"):
            print(f"[SMS SENT] {name} ({mobile})")
            return True
        return False
    except Exception as e:
        print(f"[SMS ERROR] {e}")
        return False

# ──────────────────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────────────────

@app.route("/")
def home():
    """Serve frontend HTML"""
    return send_from_directory(".", "index.html")

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json()
    income = data.get("income")
    
    if income is None or not isinstance(income, (int, float)) or income < 0:
        return jsonify({"error": "Please provide a valid positive income value."}), 400

    result = compute_tax(float(income))
    return jsonify(result), 200

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
        "name": name,
        "mobile": mobile,
        "utr": utr,
        "income": income,
        "final_tax": final_tax,
        "approved": False
    }

    print(f"[PAYMENT] {name} | {mobile} | UTR:{utr}")
    send_sms_to_admin(name, mobile, utr, income, final_tax)

    return jsonify({
        "message": "Payment details received. Admin will verify shortly.",
        "sms_sent": True
    }), 200

# ✅ FIXED: Route parameter syntax <mobile>
@app.route("/status/<mobile>", methods=["GET"])
def check_status(mobile):
    record = payment_store.get(mobile)
    if not record:
        return jsonify({"error": "No payment request found."}), 404
    return jsonify({
        "mobile": mobile,
        "name": record["name"],
        "approved": record["approved"]
    }), 200

@app.route("/approve/<mobile>", methods=["GET"])
def approve_payment(mobile):
    record = payment_store.get(mobile)
    if not record:
        return f"<h2>❌ No record for: {mobile}</h2>", 404
    
    payment_store[mobile]["approved"] = True
    print(f"[APPROVED] {record['name']} ({mobile})")
    
    return f"""
    <html><head><title>Approved</title></head>
    <body style="font-family:sans-serif;padding:40px;background:#0a0c10;color:#e8eaf0;">
        <h2 style="color:#22c55e;">✅ Payment Approved</h2>
        <p><strong>{record['name']}</strong> | {mobile}</p>
        <p>UTR: {record['utr']} | Tax: ₹{int(record['final_tax']):,}</p>
        <p style="color:#6b7280;">User can now download report.</p>
    </body></html>
    """, 200

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
        rows.append({
            "Income Slab": slab["slab"],
            "Tax Rate": slab["rate"],
            "Taxable Amount (₹)": slab["taxable_amount"],
            "Tax on Slab (₹)": slab["tax_on_slab"]
        })
    df_slabs = pd.DataFrame(rows)

    summary_data = {
        "Field": [
            "Name", "Mobile", "Gross Annual Income (₹)",
            "Tax Before Cess (₹)", "Cess 4% (₹)",
            "Section 87A Rebate", "Final Tax (₹)", "UTR"
        ],
        "Value": [
            record["name"], mobile, f"₹{int(income):,}",
            f"₹{int(tax_data['tax_before_cess']):,}",
            f"₹{int(tax_data['cess']):,}",
            "Yes" if tax_data["rebate_applied"] else "No",
            f"₹{int(record['final_tax']):,}", record["utr"]
        ]
    }
    df_summary = pd.DataFrame(summary_data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_summary.to_excel(writer, index=False, sheet_name="Summary")
        df_slabs.to_excel(writer, index=False, sheet_name="Slabs")
        
        # Formatting
        workbook = writer.book
        from openpyxl.styles import Font, PatternFill, Alignment
        for sheet in workbook.sheetnames:
            ws = workbook[sheet]
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1a1e2a")
                cell.alignment = Alignment(horizontal="center")
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = max_len + 4

    output.seek(0)
    filename = f"TaxReport_{record['name'].replace(' ','_')}_{mobile}.xlsx"
    
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route("/admin", methods=["GET"])
def admin_dashboard():
    if not payment_store:
        rows = "<tr><td colspan='6' style='text-align:center;'>No requests yet</td></tr>"
    else:
        rows = ""
        for mobile, r in payment_store.items():
            status = "✅ Approved" if r["approved"] else "⏳ Pending"
            action = "" if r["approved"] else f'<a href="/approve/{mobile}" style="color:#22c55e;">[Approve]</a>'
            rows += f"<tr><td>{r['name']}</td><td>{mobile}</td><td>{r['utr']}</td><td>₹{int(r['income']):,}</td><td>{status}</td><td>{action}</td></tr>"
    
    return f"""
    <html><head><title>Admin</title><meta http-equiv="refresh" content="30"/>
    <style>body{{font-family:sans-serif;padding:32px;background:#0a0c10;color:#e8eaf0}}
    table{{width:100%;border-collapse:collapse}}th,td{{padding:12px;border-bottom:1px solid #252a35}}
    th{{background:#181c24;color:#6b7280;font-size:0.78rem}}</style></head><body>
    <h1>🛠 Admin Dashboard</h1><p>Auto-refreshes every 30s</p>
    <table><thead><tr><th>Name</th><th>Mobile</th><th>UTR</th><th>Income</th><th>Status</th><th>Action</th></tr></thead>
    <tbody>{rows}</tbody></table></body></html>
    """, 200

# ──────────────────────────────────────────────────────────
# ENTRY POINT — Render compatible
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Server running on port {port}")
    app.run(host="0.0.0.0", port=port)
