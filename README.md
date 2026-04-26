# 🇮🇳 TaxCalcIndia Pro — FY 2025-26
### Income Tax Calculator with Razorpay Payment, HuggingFace AI Summary & PDF Download

---

## 🚀 Features
- ✅ Old vs New Regime comparison
- ✅ Section 87A rebate, surcharge, 4% cess
- ✅ Slab-wise breakdown table
- ✅ Deductions: 80C, 80D, HRA, Standard
- ✅ AI Summary (HuggingFace BART)
- ✅ Pay ₹500 via Razorpay → Download PDF report
- ✅ ReportLab PDF with tips & breakdown
- ✅ Dark mode, mobile-first, AdSense-ready

---

## 📁 Project Structure
```
taxcalc-pro/
├── app.py                  ← Flask backend (routes, Razorpay, PDF)
├── requirements.txt        ← Python dependencies
├── Procfile                ← Render start command
├── .gitignore
├── .env.example            ← Copy to .env for local dev
├── utils/
│   ├── tax_engine.py       ← Full tax calculation engine
│   ├── pdf_generator.py    ← ReportLab PDF generator
│   └── ai_summary.py       ← HuggingFace AI summary
├── templates/
│   ├── index.html
│   ├── privacy.html
│   ├── terms.html
│   ├── about.html
│   └── contact.html
└── static/
    ├── css/style.css
    └── js/script.js
```

---

## 🔑 API Keys You Need

### 1. Razorpay
1. Go to https://dashboard.razorpay.com
2. Sign up → Settings → API Keys → Generate Key
3. Copy **Key ID** and **Key Secret**
4. For testing: use Test Mode keys (rzp_test_...)
5. For production: activate Live Mode

### 2. HuggingFace (AI Summary)
1. Go to https://huggingface.co/settings/tokens
2. Create account → New Token → Read access
3. Copy the token (starts with `hf_`)
4. AI summary works without this key (uses rule-based fallback)

---

## 💻 Local Development

```bash
# 1. Clone your repo
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env with your actual API keys

# 5. Run locally
python app.py

# Visit http://localhost:5000
```

---

## 🚀 Deploy to Render (Step by Step)

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "TaxCalcIndia Pro — initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Step 2: Create Render Web Service
1. Go to **render.com** → Sign in with GitHub
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name:** taxcalcindia
   - **Region:** Singapore
   - **Branch:** main
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** Free

### Step 3: Add Environment Variables on Render
In Render dashboard → your service → **Environment** tab → add:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | (any random 32-char string) |
| `RAZORPAY_KEY_ID` | rzp_test_xxxxx or rzp_live_xxxxx |
| `RAZORPAY_KEY_SECRET` | your razorpay secret |
| `HF_API_TOKEN` | hf_xxxxxxxx (optional) |

### Step 4: Deploy
Click **Save Changes** → Render auto-deploys → wait ~3 minutes → your app is live!

---

## 🧪 Testing Razorpay in Test Mode
Use these test card details:
- **Card Number:** 4111 1111 1111 1111
- **Expiry:** Any future date
- **CVV:** Any 3 digits
- **OTP:** 1234 (if prompted)

Or use UPI test ID: `success@razorpay`

---

## 🔄 After Going Live (Production Checklist)
- [ ] Switch Razorpay from Test to Live mode
- [ ] Update RAZORPAY_KEY_ID and KEY_SECRET to live keys
- [ ] Add custom domain in Render → Settings → Custom Domains
- [ ] Apply for Google AdSense at adsense.google.com
- [ ] Replace ad placeholder divs with real AdSense code

---

## ⚠️ Disclaimer
This tool provides tax estimates based on FY 2025-26 slabs. Not professional tax advice. Consult a CA for ITR filing.
