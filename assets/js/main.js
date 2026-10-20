(() => {
  'use strict';

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Analytics events. The GA4 Google tag (loaded by GTM) reads gtag() commands from dataLayer,
     so each event goes straight to GA4; the plain { event } push is there for GTM triggers. */
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  const lang = document.documentElement.lang;
  const track = (event, params = {}) => {
    const data = { page_language: lang, ...params };
    gtag('event', event, data);
    window.dataLayer.push({ event: `site.${event}`, ...data });
  };

  document.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (!link) return;
    const href = link.getAttribute('href') || '';
    if (link.matches('.btn') && href.endsWith('#contact')) {
      const where = link.closest('header, .menu, .hero') ? link.closest('header, .menu, .hero').className.split(' ')[0] : 'page';
      track('cta_click', { cta_text: link.textContent.trim(), cta_location: where });
    } else if (href.startsWith('mailto:')) {
      track('contact_click', { contact_method: 'email' });
    } else if (href.startsWith('https://t.me/')) {
      track('contact_click', { contact_method: 'telegram' });
    } else if (link.closest('.lang')) {
      track('language_switch', { to_language: link.getAttribute('hreflang') });
    }
  });

  /* Mobile menu --------------------------------------------------------- */
  const menu = document.getElementById('menu');
  const openBtn = document.querySelector('[data-menu-open]');

  const setMenu = (open) => {
    if (!menu || !openBtn) return;
    if (open) {
      menu.hidden = false;
      requestAnimationFrame(() => menu.classList.add('is-open'));
      menu.querySelector('.menu__close')?.focus();
    } else {
      menu.classList.remove('is-open');
      setTimeout(() => { if (!menu.classList.contains('is-open')) menu.hidden = true; }, 300);
      openBtn.focus({ preventScroll: true });
    }
    openBtn.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('menu-open', open);
  };

  openBtn?.addEventListener('click', () => setMenu(true));
  menu?.querySelectorAll('[data-menu-close]').forEach((el) =>
    el.addEventListener('click', () => setMenu(false))
  );
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && menu?.classList.contains('is-open')) setMenu(false);
  });
  window.matchMedia('(min-width: 992px)').addEventListener('change', (e) => {
    if (e.matches && menu?.classList.contains('is-open')) setMenu(false);
  });

  /* Language switcher: keep the current section when switching ---------- */
  document.querySelectorAll('.lang a').forEach((a) => {
    a.addEventListener('click', () => {
      if (location.hash) a.href = a.getAttribute('href').split('#')[0] + location.hash;
    });
  });

  /* SmartRail video: load and play only while visible -------------------- */
  document.querySelectorAll('video[data-autoplay]').forEach((video) => {
    const load = () => {
      const source = video.querySelector('source[data-src]');
      if (source) {
        source.src = source.dataset.src;
        source.removeAttribute('data-src');
        video.load();
      }
    };
    if (reduceMotion || !('IntersectionObserver' in window)) {
      video.controls = true;
      video.preload = 'metadata';
      load();
      return;
    }
    new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          load();
          video.play().then(() => {
            if (!video.dataset.tracked) { video.dataset.tracked = '1'; track('video_start', { video_title: 'SmartRail' }); }
          }).catch(() => { video.controls = true; });
        } else {
          video.pause();
        }
      });
    }, { threshold: 0.25 }).observe(video);
  });

  /* Contact form -------------------------------------------------------- */
  const card = document.querySelector('[data-form-card]');
  const form = card?.querySelector('form');

  const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  const PHONE = /^\+?[\d\s()-]{7,}$/;
  const validators = {
    name: (v) => v.trim().length > 1,
    contact: (v) => EMAIL.test(v.trim()) || PHONE.test(v.trim()),
  };

  const validateField = (input) => {
    const check = validators[input.name];
    if (!check) return true;
    const ok = check(input.value);
    input.closest('.field')?.classList.toggle('is-invalid', !ok);
    input.setAttribute('aria-invalid', String(!ok));
    return ok;
  };

  if (form) {
    const fields = [...form.querySelectorAll('input[name="name"], input[name="contact"]')];
    fields.forEach((input) => {
      input.addEventListener('blur', () => { if (input.value) validateField(input); });
      input.addEventListener('input', () => {
        if (input.closest('.field')?.classList.contains('is-invalid')) validateField(input);
      });
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!fields.map(validateField).every(Boolean)) {
        form.querySelector('.is-invalid input')?.focus();
        return;
      }
      if (form.elements._gotcha?.value) return; // bot

      const formData = new FormData(form);
      formData.delete('_gotcha');
      const data = Object.fromEntries(formData);
      const button = form.querySelector('[type="submit"]');
      const { endpoint, fallbackEmail, msgSending, msgError, mailSubject } = form.dataset;

      if (!endpoint) {
        // No form endpoint configured — open an email draft instead.
        const body = `Name: ${data.name}\nCompany: ${data.company || '—'}\nContact: ${data.contact}\nLanguage: ${data.language}\n\n${data.message || ''}`;
        window.location.href = `mailto:${fallbackEmail}?subject=${encodeURIComponent(mailSubject)}&body=${encodeURIComponent(body)}`;
        return;
      }

      button.disabled = true;
      const label = button.textContent;
      button.textContent = msgSending;
      try {
        // Cloudflare Worker (tools/telegram-worker.js) posts the request to the team's Telegram chat
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        const json = await res.json().catch(() => ({}));
        if (!res.ok || !json.success) throw new Error(json.message || res.statusText);
        form.reset();
        card.classList.add('is-sent');
        track('generate_lead', { form_name: 'contact', lead_language: data.language });
        card.querySelector('.form-success button')?.focus();
      } catch {
        alert(`${msgError} ${fallbackEmail}`);
      } finally {
        button.disabled = false;
        button.textContent = label;
      }
    });

    card.querySelector('[data-form-reset]')?.addEventListener('click', () => {
      card.classList.remove('is-sent');
      form.querySelector('input:not([type="hidden"])')?.focus();
    });
  }

  /* Reveal on scroll ---------------------------------------------------- */
  const reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reduceMotion) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add('is-visible'));
  }

  /* Year ---------------------------------------------------------------- */
  document.querySelectorAll('[data-year]').forEach((el) => { el.textContent = new Date().getFullYear(); });
})();
