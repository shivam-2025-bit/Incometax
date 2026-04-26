import os
import json
import hmac
import hashlib
import requests
from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS
import razorpay
from utils.tax_engine import calculate_tax
from utils.pdf_generator import generate_pdf
from utils.ai_summary import get_ai_summary
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
CORS(app)

# Razorpay credentials from environment
RAZORPAY_KEY_ID     = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
PAYMENT_AMOUNT      = 50000  # ₹500 in paise

rzp_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ─── Pages ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html', razorpay_key=RAZORPAY_KEY_ID)

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

# ─── Tax Calculation API ───────────────────────────────────────────────────────
@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        income  = float(data.get('income', 0))
        age     = data.get('age', 'below60')
        d80c    = float(data.get('d80c', 0))
        d80d    = float(data.get('d80d', 0))
        hra     = float(data.get('hra', 0))
        other   = float(data.get('other', 0))

        if income <= 0:
            return jsonify({'error': 'Please enter a valid income'}), 400

        result = calculate_tax(income, age, d80c, d80d, hra, other)

        # Store in session for PDF generation after payment
        session['last_result'] = result
        session['last_income'] = income

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─── AI Summary API ───────────────────────────────────────────────────────────
@app.route('/ai-summary', methods=['POST'])
def ai_summary():
    try:
        data = request.get_json()
        result = data.get('result', {})
        summary = get_ai_summary(result)
        return jsonify({'summary': summary})
    except Exception as e:
        return jsonify({'summary': 'AI summary temporarily unavailable. Please review the detailed breakdown above.'}), 200

# ─── Razorpay: Create Order ───────────────────────────────────────────────────
@app.route('/create-order', methods=['POST'])
def create_order():
    try:
        order = rzp_client.order.create({
            'amount': PAYMENT_AMOUNT,
            'currency': 'INR',
            'payment_capture': 1,
            'notes': {'purpose': 'TaxCalcIndia PDF Report'}
        })
        return jsonify({'order_id': order['id'], 'amount': PAYMENT_AMOUNT, 'currency': 'INR'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─── Razorpay: Verify Payment ─────────────────────────────────────────────────
@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    try:
        data = request.get_json()
        razorpay_order_id   = data.get('razorpay_order_id', '')
        razorpay_payment_id = data.get('razorpay_payment_id', '')
        razorpay_signature  = data.get('razorpay_signature', '')

        # Signature verification
        msg = f"{razorpay_order_id}|{razorpay_payment_id}"
        expected = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            msg.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, razorpay_signature):
            return jsonify({'success': False, 'error': 'Signature mismatch'}), 400

        # Mark session as paid
        session['paid'] = True
        session['payment_id'] = razorpay_payment_id
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── Download PDF ─────────────────────────────────────────────────────────────
@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    try:
        # Verify payment
        if not session.get('paid'):
            return jsonify({'error': 'Payment required'}), 402

        data = request.get_json()
        result = data.get('result') or session.get('last_result')
        if not result:
            return jsonify({'error': 'No calculation data found. Please recalculate.'}), 400

        pdf_path = generate_pdf(result)

        # Reset payment flag after download
        session.pop('paid', None)

        return send_file(
            pdf_path,
            as_attachment=True,
            download_name='TaxCalcIndia_Report.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False)
