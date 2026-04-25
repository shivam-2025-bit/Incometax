"""
==========================================================
  India Income Tax Calculator — Flask Backend
  FY 2025-26 | New Tax Regime
==========================================================

  Routes:
    POST /calculate           — Compute tax
    POST /payment-request     — Store UTR + send SMS to admin
    GET  /status/<mobile>     — Check approval status
    GET  /approve/<mobile>    — Admin approves a payment
    GET  /download/<mobile>   — Download Excel report (if approved)

  Run:
    pip install flask pandas openpyxl requests flask-cors
    python app.py

==========================================================
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS          # allows browser to call Flask
import pandas as pd
import requests
import io
import os

app = Flask(__name__)
CORS(app)   # enable CORS so the HTML page can call the API

# ──────────────────────────────────────────────────────────
# CONFIG — Edit these before running
# ──────────────────────────────────────────────────────────

# Fast2SMS API key — sign up at https://fast2sms.com (free tier available)
# Leave empty to skip SMS (useful for local testing)
FAST2SMS_API_KEY = "Plg2rVEOYs9u1yd60wvSF4hAQzCpjmcTZML3KiUtekGo7qJbHfyxuVBJ391fwG4AUao0THYncgdLiEvK"

# Admin mobile number that receives SMS alerts
ADMIN_MOBILE = "9088050201"   # ← change to your number

# Report fee (display only — not enforced in code)
REPORT_FEE = 99

# ──────────────────────────────────────────────────────────
# IN-MEMORY STORAGE  (no database needed)
# Format: { "mobile": { "name", "utr", "income", "final_tax", "approved" } }
# ──────────────────────────────────────────────────────────
payment_store = {}


# ──────────────────────────────────────────────────────────
# TAX CALCULATION LOGIC
# ──────────────────────────────────────────────────────────

# New Tax Regime slabs for FY 2025-26
TAX_SLABS = [
    (300000,  600000, 0.05),   # 3L–6L  → 5%
    (600000,  900000, 0.10),   # 6L–9L  → 10%
    (900000, 1200000, 0.15),   # 9L–12L → 15%
    (1200000, 1500000, 0.20),  # 12L–15L → 20%
    (1500000, float('inf'), 0.30),  # >15L → 30%
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
    """
    Compute income tax under New Tax Regime.
    Returns a dict with:
      - tax_before_cess
      - cess
      - final_tax
      - rebate_applied (bool)
      - slab_details (list)
    """
    tax = 0.0
    slab_details = []

    # Slab 0: 0–3L → 0%
    slab_details.append({
        "slab": SLAB_LABELS[0],
        "rate": "0%",
        "taxable_amount": min(income, 300000),
        "tax_on_slab": 0.0
    })

    # Slabs 1–5
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

    # Section 87A rebate: if income ≤ ₹7L, tax = 0
    rebate_applied = income <= 700000
    if rebate_applied:
        tax_before_cess = 0

    # 4% Health & Education Cess
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
# SMS HELPER
# ──────────────────────────────────────────────────────────

def send_sms_to_admin(name: str, mobile: str, utr: str, income: float, tax: float) -> bool:
    """
    Sends an SMS alert to the admin using Fast2SMS.
    Returns True if successful, False otherwise.
    """
    if not FAST2SMS_API_KEY or FAST2SMS_API_KEY == "Plg2rVEOYs9u1yd60wvSF4hAQzCpjmcTZML3KiUtekGo7qJbHfyxuVBJ391fwG4AUao0THYncgdLiEvK":
        print(f"[SMS SKIPPED] No API key. Alert: {name} | {mobile} | UTR:{utr}")
        return False

    message = (
        f"TaxCalc Alert: New payment submitted. "
        f"Name: {name}, Mobile: {mobile}, UTR: {utr}, "
        f"Income: Rs{int(income)}, Tax: Rs{int(tax)}. "
        f"Verify and approve at /approve/{mobile}"
    )

    url = "https://www.fast2sms.com/dev/bulkV2"
    headers = {
        "authorization": FAST2SMS_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "route": "q",          # transactional route
        "message": message,
        "language": "english",
        "flash": 0,
        "numbers": ADMIN_MOBILE
    }

    try:
        resp = requests.post(url, headers=headers, data=payload, timeout=10)
        result = resp.json()
        if result.get("return"):
            print(f"[SMS SENT] Admin alerted about {name} ({mobile})")
            return True
        else:
            print(f"[SMS FAILED] {result}")
            return False
    except Exception as e:
        print(f"[SMS ERROR] {e}")
        return False


# ──────────────────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────────────────

@app.route("/calculate", methods=["POST"])
def calculate():
    """
    POST /calculate
    Body: { "income": 1200000 }
    Returns tax breakdown as JSON.
    """
    data = request.get_json()
    income = data.get("income")

    # Validation
    if income is None or not isinstance(income, (int, float)) or income < 0:
        return jsonify({"error": "Please provide a valid positive income value."}), 400

    result = compute_tax(float(income))
    return jsonify(result), 200


@app.route("/payment-request", methods=["POST"])
def payment_request():
    """
    POST /payment-request
    Body: { "name", "mobile", "utr", "income", "final_tax" }
    Stores details + sends admin SMS alert.
    """
    data = request.get_json()
    name      = data.get("name", "").strip()
    mobile    = data.get("mobile", "").strip()
    utr       = data.get("utr", "").strip()
    income    = data.get("income", 0)
    final_tax = data.get("final_tax", 0)

    # Basic validation
    if not name or not mobile or not utr:
        return jsonify({"error": "Name, mobile, and UTR are required."}), 400

    if not mobile.isdigit() or len(mobile) != 10:
        return jsonify({"error": "Mobile must be a 10-digit number."}), 400

    # Store in memory (not yet approved)
    payment_store[mobile] = {
        "name":      name,
        "mobile":    mobile,
        "utr":       utr,
        "income":    income,
        "final_tax": final_tax,
        "approved":  False
    }

    print(f"[PAYMENT REQUEST] {name} | {mobile} | UTR:{utr}")

    # Send SMS alert to admin
    sms_sent = send_sms_to_admin(name, mobile, utr, income, final_tax)

    return jsonify({
        "message": "Payment details received. Admin will verify and approve shortly.",
        "sms_sent": sms_sent
    }), 200


@app.route("/status/<mobile>", methods=["GET"])
def check_status(mobile):
    """
    GET /status/<mobile>
    Returns approval status for a given mobile number.
    """
    record = payment_store.get(mobile)

    if not record:
        return jsonify({"error": "No payment request found for this mobile number."}), 404

    return jsonify({
        "mobile":   mobile,
        "name":     record["name"],
        "approved": record["approved"]
    }), 200


@app.route("/approve/<mobile>", methods=["GET"])
def approve_payment(mobile):
    """
    GET /approve/<mobile>
    Admin calls this URL after verifying payment manually.
    """
    record = payment_store.get(mobile)

    if not record:
        return f"<h2>❌ No record found for mobile: {mobile}</h2>", 404

    # Mark as approved
    payment_store[mobile]["approved"] = True
    print(f"[APPROVED] {record['name']} ({mobile})")

    return f"""
    <html>
    <head><title>Approved</title></head>
    <body style="font-family:sans-serif; padding:40px; background:#0a0c10; color:#e8eaf0;">
        <h2 style="color:#22c55e;">✅ Payment Approved</h2>
        <p>User: <strong>{record['name']}</strong></p>
        <p>Mobile: <strong>{mobile}</strong></p>
        <p>UTR: <strong>{record['utr']}</strong></p>
        <p>Income: <strong>₹{int(record['income']):,}</strong></p>
        <p>Tax: <strong>₹{int(record['final_tax']):,}</strong></p>
        <hr/>
        <p style="color:#6b7280;">User can now download their report.</p>
    </body>
    </html>
    """, 200


@app.route("/download/<mobile>", methods=["GET"])
def download_report(mobile):
    """
    GET /download/<mobile>
    If approved, generates and returns an Excel (.xlsx) report.
    Otherwise returns 403.
    """
    record = payment_store.get(mobile)

    if not record:
        return jsonify({"error": "No payment request found. Please submit payment first."}), 404

    if not record["approved"]:
        return jsonify({"error": "Payment pending approval. Please wait for admin to verify."}), 403

    # ── Generate Excel report ─────────────────────────────
    income    = record["income"]
    final_tax = record["final_tax"]

    # Re-compute full breakdown for the report
    tax_data = compute_tax(float(income))

    # Build a pandas DataFrame with the slab breakdown
    rows = []
    for slab in tax_data["slab_details"]:
        rows.append({
            "Income Slab":        slab["slab"],
            "Tax Rate":           slab["rate"],
            "Taxable Amount (₹)": slab["taxable_amount"],
            "Tax on Slab (₹)":   slab["tax_on_slab"]
        })

    df_slabs = pd.DataFrame(rows)

    # Summary data
    summary_data = {
        "Field": [
            "Name",
            "Mobile",
            "Gross Annual Income (₹)",
            "Tax Before Cess (₹)",
            "Health & Education Cess 4% (₹)",
            "Section 87A Rebate Applied",
            "Final Tax Payable (₹)",
            "UTR / Transaction Reference"
        ],
        "Value": [
            record["name"],
            mobile,
            f"₹{int(income):,}",
            f"₹{int(tax_data['tax_before_cess']):,}",
            f"₹{int(tax_data['cess']):,}",
            "Yes" if tax_data["rebate_applied"] else "No",
            f"₹{int(final_tax):,}",
            record["utr"]
        ]
    }
    df_summary = pd.DataFrame(summary_data)

    # Write to an in-memory Excel file using openpyxl
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # Sheet 1: Summary
        df_summary.to_excel(writer, index=False, sheet_name="Tax Summary")

        # Sheet 2: Slab Breakdown
        df_slabs.to_excel(writer, index=False, sheet_name="Slab Breakdown")

        # Basic formatting
        workbook = writer.book
        from openpyxl.styles import Font, PatternFill, Alignment

        for sheet_name in workbook.sheetnames:
            ws = workbook[sheet_name]

            # Bold header row
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1a1e2a")
                cell.alignment = Alignment(horizontal="center")

            # Auto-width columns
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


# ──────────────────────────────────────────────────────────
# ADMIN DASHBOARD (simple HTML page to view all requests)
# ──────────────────────────────────────────────────────────

@app.route("/admin", methods=["GET"])
def admin_dashboard():
    """
    GET /admin
    Simple HTML page showing all payment requests.
    Click 'Approve' to approve each one.
    """
    if not payment_store:
        rows = "<tr><td colspan='6' style='text-align:center; color:#6b7280;'>No requests yet</td></tr>"
    else:
        rows = ""
        for mobile, r in payment_store.items():
            status_badge = (
                "<span style='color:#22c55e;'>✅ Approved</span>"
                if r["approved"] else
                "<span style='color:#f97316;'>⏳ Pending</span>"
            )
            approve_btn = (
                ""
                if r["approved"] else
                f"<a href='/approve/{mobile}' style='color:#3b82f6;'>Approve ▶</a>"
            )
            rows += f"""
            <tr>
                <td>{r['name']}</td>
                <td>{mobile}</td>
                <td>{r['utr']}</td>
                <td>₹{int(r['income']):,}</td>
                <td>{status_badge}</td>
                <td>{approve_btn}</td>
            </tr>
            """

    return f"""
    <html>
    <head>
        <title>Admin Dashboard</title>
        <meta http-equiv="refresh" content="30"/>
        <style>
            body {{ font-family: sans-serif; padding: 32px; background: #0a0c10; color: #e8eaf0; }}
            h1 {{ font-size: 1.5rem; margin-bottom: 4px; }}
            p  {{ color: #6b7280; font-size: 0.85rem; margin-bottom: 24px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background: #181c24; padding: 12px; text-align: left; border-bottom: 1px solid #252a35; color: #6b7280; font-size: 0.78rem; text-transform: uppercase; }}
            td {{ padding: 12px; border-bottom: 1px solid #1a1e2a; font-size: 0.88rem; }}
            a  {{ text-decoration: none; }}
        </style>
    </head>
    <body>
        <h1>🛠 Admin Dashboard</h1>
        <p>Auto-refreshes every 30 seconds. Verify payment in your bank app, then click Approve.</p>
        <table>
            <thead>
                <tr>
                    <th>Name</th><th>Mobile</th><th>UTR</th>
                    <th>Income</th><th>Status</th><th>Action</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </body>
    </html>
    """, 200


# ──────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
