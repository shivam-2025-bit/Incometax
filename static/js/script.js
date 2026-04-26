'use strict';

/* ── Theme ─────────────────────────────────────────────────────────────────── */
const html = document.documentElement;
const darkBtn = document.getElementById('darkBtn');
(function(){
  const t = localStorage.getItem('theme') || 'light';
  html.setAttribute('data-theme', t);
  darkBtn.textContent = t === 'dark' ? '☀️' : '🌙';
})();
darkBtn.addEventListener('click', () => {
  const t = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', t);
  localStorage.setItem('theme', t);
  darkBtn.textContent = t === 'dark' ? '☀️' : '🌙';
});

/* ── Pill groups ────────────────────────────────────────────────────────────── */
function makePills(id) {
  const wrap = document.getElementById(id);
  wrap.addEventListener('click', e => {
    if (!e.target.classList.contains('pill')) return;
    wrap.querySelectorAll('.pill').forEach(p => p.classList.remove('on'));
    e.target.classList.add('on');
  });
  return { get: () => wrap.querySelector('.pill.on')?.dataset.v || '' };
}
const agePills = makePills('agePills');

/* ── Accordion ──────────────────────────────────────────────────────────────── */
const accTrigger = document.getElementById('accTrigger');
const accBody    = document.getElementById('accBody');
const accArrow   = accTrigger.querySelector('.acc-arrow');
accTrigger.addEventListener('click', () => {
  accBody.classList.toggle('open');
  accArrow.classList.toggle('open');
});

/* ── Income display ─────────────────────────────────────────────────────────── */
const incomeEl    = document.getElementById('income');
const incomeWords = document.getElementById('incomeWords');
function toWords(n) {
  if (!n || isNaN(n) || n <= 0) return '';
  n = Number(n);
  if (n >= 10_000_000) return `₹${(n/10_000_000).toFixed(2)} Crore`;
  if (n >= 100_000)    return `₹${(n/100_000).toFixed(2)} Lakh`;
  return `₹${n.toLocaleString('en-IN')}`;
}
incomeEl.addEventListener('input', () => { incomeWords.textContent = toWords(incomeEl.value); });

/* ── Helpers ────────────────────────────────────────────────────────────────── */
const fmt = n => '₹' + Math.round(n).toLocaleString('en-IN');
const pct = n => `${n}%`;
let lastResult = null;

/* ── Calculate ──────────────────────────────────────────────────────────────── */
document.getElementById('calcBtn').addEventListener('click', doCalculate);

async function doCalculate() {
  const income = parseFloat(incomeEl.value);
  if (!income || income <= 0) { alert('Please enter a valid annual income.'); return; }

  const btnLabel = document.getElementById('btnLabel');
  const calcSpin = document.getElementById('calcSpin');
  btnLabel.textContent = 'Calculating…';
  calcSpin.classList.add('on');

  try {
    const res = await fetch('/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        income,
        age:   agePills.get(),
        d80c:  parseFloat(document.getElementById('d80c').value)  || 0,
        d80d:  parseFloat(document.getElementById('d80d').value)  || 0,
        hra:   parseFloat(document.getElementById('hra').value)   || 0,
        other: parseFloat(document.getElementById('other').value) || 0,
      })
    });
    const data = await res.json();
    if (data.error) { alert('Error: ' + data.error); return; }
    lastResult = data;
    renderResults(data);
  } catch(e) {
    alert('Network error. Please try again.');
  } finally {
    btnLabel.textContent = '⚡ Calculate Tax Now';
    calcSpin.classList.remove('on');
  }
}

/* ── Render Results ─────────────────────────────────────────────────────────── */
function renderResults(d) {
  const section = document.getElementById('results');
  section.classList.remove('hidden');

  // Reset AI
  document.getElementById('aiBody').innerHTML = '<p class="ai-hint">Click "Generate Summary" for an AI-powered explanation of your tax calculation.</p>';
  document.getElementById('aiBtn').disabled = false;

  // Recommendation banner
  const banner = document.getElementById('recBanner');
  const isNew  = d.recommended === 'new';
  banner.style.cssText = `background:${isNew ? 'var(--grn-lt)' : 'var(--amb-lt)'};color:${isNew ? 'var(--green)' : 'var(--amber)'};border:1px solid ${isNew ? 'var(--green)' : 'var(--amber)'};`;
  banner.textContent = d.recommendation_reason;

  // Regime cards
  renderRegimeCards(d);

  // Breakdown tabs
  renderBreakdown(d);

  // Deductions detail
  renderDedDetail(d.old_regime);

  // Tips
  renderTips(d);

  // Scroll
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderRegimeCards(d) {
  const nr = d.new_regime, or_ = d.old_regime;
  const grid = document.getElementById('regimeGrid');
  grid.innerHTML = [
    regimeCard('New Tax Regime', nr, d.recommended === 'new', true),
    regimeCard('Old Tax Regime', or_, d.recommended === 'old', false),
  ].join('');
}

function regimeCard(title, r, isWinner, isNew) {
  return `
  <div class="rcard${isWinner ? ' winner' : ''}">
    <span class="rec-tag">✓ Recommended</span>
    <h3>${title}</h3>
    <div class="tax-big">${fmt(r.total_tax)}</div>
    <div class="tax-lbl">Total Tax Payable</div>
    <div class="meta">
      ${isNew ? `<div class="mrow"><span>Standard Deduction</span><span>- ${fmt(r.standard_deduction)}</span></div>` : ''}
      <div class="mrow"><span>Taxable Income</span><span>${fmt(r.taxable_income)}</span></div>
      <div class="mrow"><span>Base Tax</span><span>${fmt(r.base_tax)}</span></div>
      ${r.rebate_87a > 0 ? `<div class="mrow"><span>87A Rebate</span><span style="color:var(--green)">- ${fmt(r.rebate_87a)}</span></div>` : ''}
      ${r.surcharge > 0 ? `<div class="mrow"><span>Surcharge</span><span>${fmt(r.surcharge)}</span></div>` : ''}
      <div class="mrow"><span>Cess (4%)</span><span>${fmt(r.cess)}</span></div>
      <div class="mrow total"><span>Total Tax</span><span>${fmt(r.total_tax)}</span></div>
      <div class="mrow"><span>Effective Rate</span><span>${pct(r.effective_rate)}</span></div>
      <div class="mrow hi"><span>Monthly Take-Home</span><span>${fmt(r.take_home_monthly)}</span></div>
      <div class="mrow hi"><span>Annual Take-Home</span><span>${fmt(r.take_home_annual)}</span></div>
    </div>
  </div>`;
}

function renderBreakdown(d) {
  const tabsEl   = document.getElementById('tabs');
  const contentEl = document.getElementById('tabContent');

  tabsEl.innerHTML = `
    <button class="tab on" onclick="switchTab('new',this)">New Regime</button>
    <button class="tab" onclick="switchTab('old',this)">Old Regime</button>`;

  contentEl.innerHTML = `
    <div id="tab-new">${buildTable(d.new_regime.breakdown, d.new_regime.total_tax)}</div>
    <div id="tab-old" class="hidden">${buildTable(d.old_regime.breakdown, d.old_regime.total_tax)}</div>`;
}

function buildTable(rows, total) {
  if (!rows || rows.length === 0) return '<p style="color:var(--text3);font-size:13px;padding:8px 0">No taxable slabs — income is fully exempt.</p>';
  let html = `<table><thead><tr><th>Income Slab</th><th>Rate</th><th>Taxable Amount</th><th>Tax on Slab</th></tr></thead><tbody>`;
  rows.forEach(r => {
    html += `<tr><td>${r.slab}</td><td style="text-align:right">${r.rate}</td><td>${fmt(r.taxable_amount)}</td><td>${fmt(r.tax_on_slab)}</td></tr>`;
  });
  html += `<tr class="total-row"><td colspan="3"><strong>Total Tax (incl. surcharge & cess)</strong></td><td><strong>${fmt(total)}</strong></td></tr>`;
  html += `</tbody></table>`;
  return html;
}

window.switchTab = function(tab, btn) {
  ['new','old'].forEach(t => {
    const el = document.getElementById('tab-'+t);
    if (el) el.classList.toggle('hidden', t !== tab);
  });
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('on'));
  btn.classList.add('on');
};

function renderDedDetail(or_) {
  const el = document.getElementById('dedDetail');
  const d  = or_.deductions || {};
  if (!d.total) { el.innerHTML = ''; return; }
  el.innerHTML = `
    <h3>📝 Deductions Applied (Old Regime)</h3>
    <table>
      <thead><tr><th>Deduction</th><th>Section</th><th>Amount Claimed</th></tr></thead>
      <tbody>
        <tr><td>Standard Deduction</td><td>—</td><td>${fmt(d.standard_deduction)}</td></tr>
        <tr><td>PPF / ELSS / LIC / NSC</td><td>80C</td><td>${fmt(d.section_80c)}</td></tr>
        <tr><td>Health Insurance Premium</td><td>80D</td><td>${fmt(d.section_80d)}</td></tr>
        <tr><td>HRA Exemption</td><td>—</td><td>${fmt(d.hra)}</td></tr>
        <tr><td>Other Deductions</td><td>—</td><td>${fmt(d.other)}</td></tr>
        <tr class="total-row"><td colspan="2"><strong>Total Deductions</strong></td><td><strong>${fmt(d.total)}</strong></td></tr>
      </tbody>
    </table>`;
}

function renderTips(d) {
  const grid = document.getElementById('tipsGrid');
  const ded  = d.old_regime.deductions || {};
  const tips = [];

  if ((ded.section_80c || 0) < 150_000)
    tips.push({ title: 'Max out 80C', text: `Invest ₹${(150_000 - (ded.section_80c||0)).toLocaleString('en-IN')} more in PPF/ELSS/NSC/LIC to save up to ₹${((150_000-(ded.section_80c||0))*0.3).toLocaleString('en-IN')} in Old Regime.` });
  if ((ded.section_80d || 0) < 25_000)
    tips.push({ title: 'Health Insurance (80D)', text: 'Claim up to ₹25,000 on health insurance. Senior citizens can claim ₹50,000.' });
  if (!(ded.hra || 0))
    tips.push({ title: 'HRA Exemption', text: 'Salaried & living on rent? Claim HRA exemption under Old Regime to cut taxable income.' });
  tips.push({ title: 'NPS (80CCD)', text: 'Extra ₹50,000 deduction via NPS under Section 80CCD(1B) — over and above your 80C limit.' });
  tips.push({ title: 'Home Loan (24b)', text: 'Interest on home loan is deductible up to ₹2L under Section 24(b) in Old Regime.' });
  tips.push({ title: 'Compare Annually', text: 'Recalculate every year after budget — the best regime can change as your income and investments grow.' });

  grid.innerHTML = tips.map(t => `<div class="tip"><strong>${t.title}</strong><p>${t.text}</p></div>`).join('');
}

/* ── AI Summary ─────────────────────────────────────────────────────────────── */
document.getElementById('aiBtn').addEventListener('click', async () => {
  if (!lastResult) { alert('Please calculate first.'); return; }
  const btn  = document.getElementById('aiBtn');
  const body = document.getElementById('aiBody');
  btn.disabled = true;
  btn.textContent = 'Generating…';
  body.innerHTML = '<p class="ai-loading">🤖 AI is analysing your tax data…</p>';

  try {
    const res = await fetch('/ai-summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ result: lastResult })
    });
    const data = await res.json();
    body.innerHTML = `<p>${data.summary.replace(/₹/g, '₹').replace(/\n/g,'<br>')}</p>`;
    btn.textContent = '✅ Summary Generated';
  } catch(e) {
    body.innerHTML = '<p style="color:#f87171">Could not load AI summary. Please try again.</p>';
    btn.textContent = 'Retry';
    btn.disabled = false;
  }
});

/* ── Razorpay Payment + PDF Download ───────────────────────────────────────── */
document.getElementById('payBtn').addEventListener('click', initiatePayment);

async function initiatePayment() {
  if (!lastResult) { alert('Please calculate your tax first.'); return; }

  const btn      = document.getElementById('payBtn');
  const payLabel = document.getElementById('payLabel');
  const paySpin  = document.getElementById('paySpin');

  payLabel.style.display = 'none';
  paySpin.classList.add('on');
  btn.disabled = true;

  try {
    // 1. Create Razorpay order
    const orderRes = await fetch('/create-order', { method: 'POST' });
    const orderData = await orderRes.json();
    if (orderData.error) { alert('Could not create order: ' + orderData.error); return; }

    // 2. Open Razorpay checkout
    const rzp = new Razorpay({
      key: RAZORPAY_KEY,
      amount: orderData.amount,
      currency: orderData.currency,
      order_id: orderData.order_id,
      name: 'TaxCalcIndia',
      description: 'Detailed Tax Report — FY 2025-26',
      image: '',
      prefill: { name: '', email: '', contact: '' },
      theme: { color: '#1a56db' },
      handler: async function(response) {
        // 3. Verify payment
        payLabel.textContent = '🔍 Verifying payment…';
        payLabel.style.display = 'inline';
        paySpin.classList.add('on');

        const verRes = await fetch('/verify-payment', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            razorpay_order_id:   response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature:  response.razorpay_signature,
          })
        });
        const verData = await verRes.json();
        if (!verData.success) { alert('Payment verification failed. Contact support.'); return; }

        // 4. Download PDF
        payLabel.textContent = '📥 Generating PDF…';
        const pdfRes = await fetch('/download-pdf', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ result: lastResult })
        });

        if (pdfRes.ok) {
          const blob = await pdfRes.blob();
          const url  = URL.createObjectURL(blob);
          const a    = document.createElement('a');
          a.href = url; a.download = 'TaxCalcIndia_Report.pdf'; a.click();
          URL.revokeObjectURL(url);
          payLabel.textContent = '✅ Download Started!';
          paySpin.classList.remove('on');
          setTimeout(() => {
            payLabel.textContent = '🔒 Pay & Download PDF';
            btn.disabled = false;
          }, 4000);
        } else {
          const err = await pdfRes.json();
          alert('PDF generation failed: ' + (err.error || 'Unknown error'));
          payLabel.textContent = '🔒 Pay & Download PDF';
          btn.disabled = false;
        }
      },
      modal: {
        ondismiss: function() {
          payLabel.style.display = 'inline';
          payLabel.textContent = '🔒 Pay & Download PDF';
          paySpin.classList.remove('on');
          btn.disabled = false;
        }
      }
    });
    rzp.open();

  } catch(e) {
    alert('Error initiating payment: ' + e.message);
  } finally {
    paySpin.classList.remove('on');
  }
}

/* ── Pre-fill from URL ──────────────────────────────────────────────────────── */
const params = new URLSearchParams(window.location.search);
if (params.get('income')) {
  incomeEl.value = params.get('income');
  incomeWords.textContent = toWords(params.get('income'));
}
