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

// ===== Smooth anchor focus & scroll spy =====
const header = $('#header');
const scrollbar = $('#scrollbar');
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

$$('a[href^="#"]').forEach(a=>{
  a.addEventListener('click', e=>{
    const id = a.getAttribute('href').slice(1);
    const target = document.getElementById(id);
    if (target){ e.preventDefault(); target.scrollIntoView({behavior:'smooth'}); target.setAttribute('tabindex','-1'); target.focus({preventScroll:true}); }
  });
});

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

// ===== Projects: click to expand =====
const projects = $$('.project');
projects.forEach(card => {
  card.addEventListener('click', () => {
    card.classList.toggle('open');
  });
});

// ===== Contact: compose mailto + copy email =====
const form = $('#contactForm');
if (form) {
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const from = $('#fromEmail').value.trim();
    const msg = $('#message').value.trim();
    const subject = encodeURIComponent('Website Contact');
    const body = encodeURIComponent(`From: ${from}\n\n${msg}`);
    window.location.href = `mailto:jaydonchua2026@gmail.com?subject=${subject}&body=${body}`;
  });
}
const copyEmail = $('#copyEmail');
if (copyEmail && navigator.clipboard) {
  copyEmail.addEventListener('click', async () => {
    await navigator.clipboard.writeText('jaydonchua2026@gmail.com');
    copyEmail.textContent = 'Copied!';
    setTimeout(()=> copyEmail.textContent = 'Copy Email', 1200);
  });
}

/* ===== Cursor Glow logic (warm) ===== */
const cursorGlow = document.getElementById('cursorGlow');

// Move glow (smooth & centered) — lightweight, runs on pointer devices
let glowRAF = null, targetX = -1000, targetY = -1000, gx = -1000, gy = -1000;
function animateGlow(){
  gx += (targetX - gx) * 0.2;
  gy += (targetY - gy) * 0.2;
  cursorGlow.style.transform = `translate3d(${gx - 120}px, ${gy - 120}px, 0)`; // center (240/2 = 120)
  if (Math.abs(targetX - gx) > 0.1 || Math.abs(targetY - gy) > 0.1){
    glowRAF = requestAnimationFrame(animateGlow);
  } else {
    glowRAF = null;
  }
}
window.addEventListener('pointermove', (e) => {
  if (e.pointerType !== 'mouse') return;      // ignore touch/pen
  targetX = e.clientX; targetY = e.clientY;
  if (!glowRAF) glowRAF = requestAnimationFrame(animateGlow);
});

// Add “glowable” to interactive elements and drive local overlay position
const glowables = Array.from(document.querySelectorAll(
  'a, button, .btn, .card, .skill, .project, .chip, .stat, .nav-list a'
));
glowables.forEach(el => {
  el.classList.add('glowable');
  el.addEventListener('pointerenter', (e) => {
    if (e.pointerType !== 'mouse') return;
    cursorGlow?.classList.add('active');
    el.classList.add('is-hovering');
  });
  el.addEventListener('pointerleave', () => {
    cursorGlow?.classList.remove('active');
    el.classList.remove('is-hovering');
  });
  el.addEventListener('pointermove', (e) => {
    const r = el.getBoundingClientRect();
    const x = e.clientX - r.left;
    const y = e.clientY - r.top;
    el.style.setProperty('--gx', `${x}px`);
    el.style.setProperty('--gy', `${y}px`);
  });
});

