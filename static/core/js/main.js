/* ============================================================
   Children's Fruit — Main JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

  /* ── STICKY NAVBAR ────────────────────────────────────── */
  const nav = document.getElementById('mainNav');
  if (nav) {
    window.addEventListener('scroll', () => {
      nav.classList.toggle('scrolled', window.scrollY > 80);
    }, { passive: true });
  }

  /* ── KPI COUNTER ANIMATION ────────────────────────────── */
  function animateCounter(el, target, duration) {
    duration = duration || 2000;
    const start = performance.now();
    const easeOut = t => 1 - Math.pow(1 - t, 3);

    function step(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const value = Math.round(easeOut(progress) * target);
      el.textContent = value.toLocaleString('fr-FR');
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  const kpiObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        const el = entry.target;
        const target = parseInt(el.dataset.target, 10) || 0;
        animateCounter(el, target, 2200);
        kpiObserver.unobserve(el);
      }
    });
  }, { threshold: 0.35 });

  document.querySelectorAll('.kpi-counter').forEach(function (el) {
    kpiObserver.observe(el);
  });

  /* ── SMOOTH SCROLL ────────────────────────────────────── */
  document.querySelectorAll('a[href^="#"]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      const id = this.getAttribute('href');
      if (id === '#') return;
      const target = document.querySelector(id);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  /* ── AUTO-DISMISS ALERTS (5 s) ────────────────────────── */
  setTimeout(function () {
    document.querySelectorAll('.alert.auto-dismiss').forEach(function (el) {
      const alert = bootstrap.Alert.getOrCreateInstance(el);
      if (alert) alert.close();
    });
  }, 5000);

  /* ── ACTIVE NAV ITEM (hash) ───────────────────────────── */
  const currentPath = window.location.pathname;
  document.querySelectorAll('.navbar-nav .nav-link').forEach(function (link) {
    const href = link.getAttribute('href');
    if (href && href !== '#' && currentPath.startsWith(href) && href !== '/') {
      link.classList.add('active');
    }
  });

});
