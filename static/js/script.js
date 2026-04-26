// Dark mode
const html = document.documentElement;
const darkBtn = document.getElementById('darkToggle');
const saved = localStorage.getItem('theme') || 'light';
html.setAttribute('data-theme', saved);
darkBtn.textContent = saved === 'dark' ? '☀️' : '🌙';
darkBtn.addEventListener('click', () => {
  const t = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', t);
  localStorage.setItem('theme', t);
  darkBtn.textContent = t === 'dark' ? '☀️' : '🌙';
});

// Pill groups
function pillGroup(id) {
  const group = document.getElementById(id);
  let val = group.querySelector('.pill.active')?.dataset.val || '';
  group.addEventListener('click', e => {
    if (!e.target.classList.contains('pill')) return;
    group.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    e.target.classList.add('active');
    val = e.target.dataset.val;
    if (id === 'regimeGroup') toggleDeductions(val);
  });
  return { get: () => val };
}

const ageCtrl = pillGroup('ageGroup');
const regimeCtrl = pillGroup('regimeGroup');

function toggleDeductions(regime) {
  const sec = document.getElementById('deductionsSection');
  sec.style.display = regime === 'new' ? 'none' : 'block';
}

// Deductions accordion
const dedToggle = document.getElementById('deductionsToggle');
const dedBody = document.getElementById('deductionsBody');
const toggleIcon = dedToggle.querySelector('.toggle-icon');
dedToggle.addEventListener('click', () => {
  dedBody.classList.toggle('open');
  toggleIcon.classList.toggle('open');
});

// Income formatter
const incomeInput = document.getElementById('income');
const incomeDisplay = document.getElementById('incomeDisplay');
function formatInr(n) {
  if (!n || isNaN(n)) return '';
  if (n >= 10000000) return `₹${(n/10000000).toFixed(2)} Cr`;
  if (n >= 100000) return `₹${(n/100000).toFixed(2)} L`;
  return `₹${Number(n).toLocaleString('en-IN')}`;
}
incomeInput.addEventListener('input', () => {
  incomeDisplay.textContent = formatInr(incomeInput.value);
});

// Calculate
document.getElementById('calcBtn').addEventListener('click', calculate);

async function calculate() {
  const income = parseFloat(incomeInput.value);
  if (!income || income <= 0) { alert('Please enter a valid annual income.'); return; }

  const btnText = document.getElementById('btnText');
  const spinner = document.getElementById('spinner');
  btnText.textContent = 'Calculating...';
  spinner.classList.add('active');

  try {
    const res = await fetch('/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        income,
        age: ageCtrl.get(),
        regime: regimeCtrl.get(),
        d80c: parseFloat(document.getElementById('d80c').value) || 0,
        d80d: parseFloat(document.getElementById('d80d').value) || 0,
        hra: parseFloat(document.getElementById('hra').value) || 0,
        other: parseFloat(document.getElementById('other').value) || 0,
      })
    });
    const data = await res.json();
    if (data.error) { alert('Error: ' + data.error); return; }
    renderResults(data);
  } catch(e) {
    alert('Network error. Please try again.');
  } finally {
    btnText.textContent = 'Calculate Tax';
    spinner.classList.remove('active');
  }
}

function fmt(n) {
  return '₹' + Math.round(n).toLocaleString('en-IN');
}

function renderResults(data) {
  const results = document.getElementById('results');
  results.classList.remove('hidden');
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });

  const rec = data.recommended;
  const savings = data.savings;

  // Recommendation banner
  const banner = document.getElementById('recBanner');
  if (savings > 0) {
    const isNew = rec === 'new';
    banner.style.background = isNew ? 'var(--accent-light)' : 'var(--warning-light)';
    banner.style.color = isNew ? 'var(--accent)' : 'var(--warning)';
    banner.style.border = `1px solid ${isNew ? 'var(--accent)' : 'var(--warning)'}`;
    banner.innerHTML = `✅ <strong>${isNew ? 'New' : 'Old'} Tax Regime</strong> saves you <strong>${fmt(savings)}</strong> more this year.`;
  } else {
    banner.innerHTML = '✅ Both regimes result in equal tax for your income.';
    banner.style.background = 'var(--primary-light)';
    banner.style.color = 'var(--primary)';
    banner.style.border = '1px solid var(--primary)';
  }

  // Regime cards
  const cards = document.getElementById('regimeCards');
  const regime = regimeCtrl.get();
  const showNew = regime !== 'old';
  const showOld = regime !== 'new';

  let cardsHTML = '';
  if (showNew) {
    const n = data.new_regime;
    cardsHTML += `
      <div class="regime-card ${rec === 'new' ? 'recommended' : ''}">
        <span class="rec-badge">✓ Recommended</span>
        <h3>New Tax Regime</h3>
        <div class="tax-amount">${fmt(n.total_tax)}</div>
        <div class="tax-label">Total Tax Payable</div>
        <div class="tax-meta">
          <div class="meta-row"><span>Base Tax</span><span>${fmt(n.base_tax)}</span></div>
          ${n.rebate > 0 ? `<div class="meta-row"><span>87A Rebate</span><span>- ${fmt(n.rebate)}</span></div>` : ''}
          ${n.surcharge > 0 ? `<div class="meta-row"><span>Surcharge</span><span>${fmt(n.surcharge)}</span></div>` : ''}
          <div class="meta-row"><span>Health & Ed. Cess (4%)</span><span>${fmt(n.cess)}</span></div>
          <div class="meta-row"><span>Effective Tax Rate</span><span>${n.effective_rate}%</span></div>
          <div class="meta-row take-home-row"><span>Monthly Take-Home</span><span>${fmt(n.take_home / 12)}/mo</span></div>
        </div>
      </div>`;
  }
  if (showOld) {
    const o = data.old_regime;
    cardsHTML += `
      <div class="regime-card ${rec === 'old' ? 'recommended' : ''}">
        <span class="rec-badge">✓ Recommended</span>
        <h3>Old Tax Regime</h3>
        <div class="tax-amount">${fmt(o.total_tax)}</div>
        <div class="tax-label">Total Tax Payable</div>
        <div class="tax-meta">
          <div class="meta-row"><span>Deductions Applied</span><span>- ${fmt(o.deductions)}</span></div>
          <div class="meta-row"><span>Base Tax</span><span>${fmt(o.base_tax)}</span></div>
          ${o.rebate > 0 ? `<div class="meta-row"><span>87A Rebate</span><span>- ${fmt(o.rebate)}</span></div>` : ''}
          ${o.surcharge > 0 ? `<div class="meta-row"><span>Surcharge</span><span>${fmt(o.surcharge)}</span></div>` : ''}
          <div class="meta-row"><span>Health & Ed. Cess (4%)</span><span>${fmt(o.cess)}</span></div>
          <div class="meta-row"><span>Effective Tax Rate</span><span>${o.effective_rate}%</span></div>
          <div class="meta-row take-home-row"><span>Monthly Take-Home</span><span>${fmt(o.take_home / 12)}/mo</span></div>
        </div>
      </div>`;
  }
  cards.innerHTML = cardsHTML;
  if (!showNew || !showOld) cards.style.gridTemplateColumns = '1fr';

  // Breakdown
  const bSec = document.getElementById('breakdownSection');
  let tabs = '';
  let tables = '';
  const activeTab = showNew ? 'new' : 'old';

  if (showNew && data.new_regime.breakdown.length > 0) {
    tabs += `<button class="tab-btn ${activeTab === 'new' ? 'active' : ''}" onclick="switchTab('new')">New Regime</button>`;
    tables += `<div id="tab-new" class="${activeTab !== 'new' ? 'hidden' : ''}">${buildTable(data.new_regime.breakdown, data.new_regime.total_tax)}</div>`;
  }
  if (showOld && data.old_regime.breakdown.length > 0) {
    tabs += `<button class="tab-btn ${activeTab === 'old' ? 'active' : ''}" onclick="switchTab('old')">Old Regime</button>`;
    tables += `<div id="tab-old" class="${activeTab !== 'old' ? 'hidden' : ''}">${buildTable(data.old_regime.breakdown, data.old_regime.total_tax)}</div>`;
  }

  bSec.innerHTML = `<h3>Slab-wise Breakdown</h3><div class="breakdown-tabs">${tabs}</div>${tables}`;
}

function buildTable(rows, total) {
  let html = `<table class="breakdown-table"><thead><tr><th>Slab</th><th>Rate</th><th>Taxable Amount</th><th>Tax</th></tr></thead><tbody>`;
  rows.forEach(r => {
    html += `<tr><td>${r.slab}</td><td>${r.rate}</td><td>${fmt(r.taxable)}</td><td>${fmt(r.tax)}</td></tr>`;
  });
  html += `<tr><td colspan="3">Total Tax (incl. cess)</td><td>${fmt(total)}</td></tr>`;
  html += `</tbody></table>`;
  return html;
}

function switchTab(tab) {
  document.querySelectorAll('.breakdown-tabs .tab-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  ['new','old'].forEach(t => {
    const el = document.getElementById('tab-' + t);
    if (el) el.classList.toggle('hidden', t !== tab);
  });
}

// Share
document.getElementById('shareBtn')?.addEventListener('click', () => {
  const income = incomeInput.value;
  const url = `${window.location.origin}/?income=${income}`;
  navigator.clipboard.writeText(url).then(() => {
    document.getElementById('shareBtn').textContent = 'Copied!';
    setTimeout(() => document.getElementById('shareBtn').textContent = 'Share Result', 2000);
  });
});

// Pre-fill from URL
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get('income')) {
  incomeInput.value = urlParams.get('income');
  incomeDisplay.textContent = formatInr(urlParams.get('income'));
  calculate();
}
