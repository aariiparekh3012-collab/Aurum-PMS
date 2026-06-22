/**
 * Aurum PMS — Landing page interactivity.
 *
 * Handles: ROI calculator, role tabs, FAQ accordion, scroll-based fade-in.
 */

/* ── ROI Calculator ───────────────────────────────── */

function calculateRoi() {
  const aum = parseFloat(document.getElementById('roiAum').value) || 0;
  const clients = parseFloat(document.getElementById('roiClients').value) || 0;
  const onboarding = parseFloat(document.getElementById('roiOnboarding').value) || 0;
  const hourly = parseFloat(document.getElementById('roiHourly').value) || 0;

  const AURUM_ONBOARDING_DAYS = 3;
  const HOURS_PER_DAY = 8;
  const MONTHLY_AURUM_COST = 30000;

  const newClientsPerYear = Math.max(1, Math.ceil(clients / 5));
  const timeSavedPerClient = onboarding - AURUM_ONBOARDING_DAYS;
  const totalHoursSaved = timeSavedPerClient * HOURS_PER_DAY * newClientsPerYear;
  const totalCostSavedL = (totalHoursSaved * hourly) / 100000;
  const annualAurumCostL = (MONTHLY_AURUM_COST * 12) / 100000;
  const netAnnualSavings = totalCostSavedL - annualAurumCostL;
  const paybackMonths = annualAurumCostL > 0
    ? annualAurumCostL / (netAnnualSavings / 12)
    : 0;

  document.getElementById('roiTimeSaved').textContent = timeSavedPerClient + ' days';
  document.getElementById('roiCostSaved').textContent = '₹' + totalCostSavedL.toFixed(1) + ' L';
  document.getElementById('roiRisk').textContent = '95%';
  document.getElementById('roiPayback').textContent = Math.max(0.5, paybackMonths.toFixed(1)) + ' months';
}

/* ── Role Tabs ────────────────────────────────────── */

function showRole(role) {
  document.querySelectorAll('.role-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.role-panel').forEach(p => p.classList.remove('active'));
  document.querySelector('[data-role="' + role + '"]').classList.add('active');
  document.getElementById('panel-' + role).classList.add('active');
}

/* ── FAQ Accordion ────────────────────────────────── */

function toggleFaq(header) {
  const item = header.parentElement;
  const isActive = item.classList.contains('active');
  document.querySelectorAll('.faq-item').forEach(el => el.classList.remove('active'));
  if (!isActive) item.classList.add('active');
}

/* ── Scroll Fade-in ───────────────────────────────── */

(function initFadeIn() {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.style.opacity = '1';
        e.target.style.transform = 'translateY(0)';
      }
    });
  }, { threshold: 0.1 });

  const selectors = [
    '.feature-card', '.step', '.tech-pill', '.testimonial-card',
    '.faq-item', '.security-badge', '.partner-card', '.roadmap__milestone',
  ].join(', ');

  document.querySelectorAll(selectors).forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity .5s ease, transform .5s ease';
    observer.observe(el);
  });
})();

/* ── Init ─────────────────────────────────────────── */
calculateRoi();
