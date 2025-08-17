// ===== Helpers =====
const $ = (sel, ctx=document) => ctx.querySelector(sel);
const $$ = (sel, ctx=document) => Array.from(ctx.querySelectorAll(sel));

// ===== Mobile nav =====
const navToggle = $('#navToggle');
const navMenu = $('#navMenu');
if (navToggle) {
  navToggle.addEventListener('click', () => {
    const shown = navMenu.classList.toggle('show');
    navToggle.setAttribute('aria-expanded', String(shown));
  });
}

// ===== Theme toggle =====
const themeToggle = $('#themeToggle');
const storedTheme = localStorage.getItem('theme');
if (storedTheme === 'dark') document.documentElement.classList.add('dark');
if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', document.documentElement.classList.contains('dark') ? 'dark' : 'light');
  });
}

// ===== Reveal on scroll =====
const revealTargets = $$('.observe');
if ('IntersectionObserver' in window) {
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('is-visible'); });
  }, { threshold: 0.15 });
  revealTargets.forEach(el => io.observe(el));
} else {
  revealTargets.forEach(el => el.classList.add('is-visible'));
}

// ===== Skills filter =====
const chips = $$('.chip');
const skills = $$('.skill');
function setFilter(tag){
  chips.forEach(c => c.setAttribute('aria-pressed', String(c.dataset.filter === tag)));
  skills.forEach(s => {
    const show = tag === 'all' || (s.dataset.tags || '').includes(tag);
    s.style.display = show ? '' : 'none';
  });
}
chips.forEach(c => c.addEventListener('click', () => setFilter(c.dataset.filter)));
setFilter('all');

// ===== Smooth anchor focus =====
$$('a[href^="#"]').forEach(a=>{
  a.addEventListener('click', e=>{
    const id = a.getAttribute('href').slice(1);
    const target = document.getElementById(id);
    if (target){ e.preventDefault(); target.scrollIntoView({behavior:'smooth'}); target.setAttribute('tabindex','-1'); target.focus({preventScroll:true}); }
  });
});

// ===== Dynamic year =====
const y = $('#year'); if (y) y.textContent = new Date().getFullYear();

// ===== Scroll progress + compact header + scroll spy =====
const scrollbar = $('#scrollbar');
const header = $('#header');
const navlinks = $$('.navlink');
const sections = navlinks.map(a => $(a.getAttribute('href'))).filter(Boolean);

function onScroll() {
  const y = window.scrollY || document.documentElement.scrollTop;
  const docHeight = document.documentElement.scrollHeight - window.innerHeight;
  const progress = docHeight > 0 ? (y / docHeight) * 100 : 0;
  if (scrollbar) scrollbar.style.width = progress + '%';

  if (header) header.classList.toggle('compact', y > 10);

  let current = null;
  for (const sec of sections) {
    const r = sec.getBoundingClientRect();
    if (r.top <= 120 && r.bottom >= 200) { current = sec; break; }
  }
  navlinks.forEach(a => a.classList.toggle('active', current && a.getAttribute('href') === '#' + current.id));
}
document.addEventListener('scroll', onScroll, { passive: true });
onScroll();

// ===== Parallax orbs (rAF) =====
const parallaxEls = $$('[data-parallax]');
let ticking = false;
function parallaxUpdate() {
  const y = window.scrollY || 0;
  parallaxEls.forEach(el => {
    const speed = parseFloat(el.dataset.speed || '0.1');
    el.style.transform = `translate3d(0, ${y * speed}px, 0)`;
  });
  ticking = false;
}
window.addEventListener('scroll', () => {
  if (!ticking) { window.requestAnimationFrame(parallaxUpdate); ticking = true; }
}, { passive: true });
parallaxUpdate();

// ===== Subtle 3D tilt on hover (cards) =====
const tilts = $$('.tilt, .tilt-small');
tilts.forEach(el => {
  let rect;
  function updateRect(){ rect = el.getBoundingClientRect(); }
  updateRect();
  window.addEventListener('resize', updateRect);

  el.addEventListener('mousemove', (e) => {
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    const rx = (0.5 - y) * 6;   // up to 6deg
    const ry = (x - 0.5) * 6;
    el.style.transform = `perspective(700px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-4px)`;
  });
  el.addEventListener('mousel
