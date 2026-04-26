# 🇮🇳 India Income Tax Calculator — FY 2025-26

A free, modern, mobile-responsive Indian income tax calculator with Old vs New regime comparison, Section 87A rebate, surcharge, cess, and slab-wise breakdown.

## Features
- Old vs New Tax Regime comparison
- Section 87A rebate logic
- Surcharge & 4% Health/Education cess
- Deductions: 80C, 80D, HRA, Others
- Age-based exemptions
- Dark mode
- AdSense-ready (Privacy, Terms, About, Contact pages)

## Tech Stack
- Backend: Python Flask
- Frontend: HTML5, CSS3, Vanilla JS
- Deployment: Render (via GitHub)

## Local Development

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
pip install -r requirements.txt
python app.py
```
Visit http://localhost:5000

## Deploy to Render

1. Push this repo to GitHub
2. Go to render.com → New → Web Service
3. Connect your GitHub repo
4. Set:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Click Create Web Service

## Project Structure

```
├── app.py              # Flask backend
├── requirements.txt    # Python dependencies
├── Procfile            # Render/Gunicorn config
├── .gitignore
├── templates/
│   ├── index.html      # Main calculator
│   ├── privacy.html
│   ├── terms.html
│   ├── about.html
│   └── contact.html
└── static/
    ├── css/style.css
    └── js/script.js
```

## License
MIT
