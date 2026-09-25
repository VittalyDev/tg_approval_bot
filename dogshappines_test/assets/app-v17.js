(() => {
  'use strict';

  const wait = (tries = 240) => {
    if (window.V16 && window.V15 && window.V14 && typeof window.api === 'function' && typeof window.showView === 'function') return boot();
    if (tries <= 0) return console.error('v17: runtime not ready');
    setTimeout(() => wait(tries - 1), 50);
  };

  function boot() {
    if (window.V17?.booted) return;
    window.V17 = { booted: true, version: 17 };

    const q = id => document.getElementById(id);
    const FALLBACK_SITTER = '/assets/service-walk.webp';
    const FALLBACK_PET = '/assets/service-walk.webp';
    const locks = new Set();
    let executorProfilePromise = null;
    let clientProfilePromise = null;

    function installStyles() {
      if (document.getElementById('v17-style')) return;
      const link = document.createElement('link');
      link.id = 'v17-style';
      link.rel = 'stylesheet';
      link.href = '/assets/app-v17.css?v=17';
      document.head.append(link);
    }

    function avatar(src, fallback = FALLBACK_SITTER) {
      const s = String(src || '').trim();
      if (!s) return fallback;
      if (/^(https?:|data:|blob:|\/uploads\/|\/assets\/)/i.test(s)) return s;
      return `/assets/${s}`;
    }

    function loadImage(src) {
      return new Promise(resolve => {
        const probe = new Image();
        probe.decoding = 'async';
        probe.onload = () => resolve(src);
        probe.onerror = () => resolve('');
        probe.src = src;
      });
    }

    async function setExecutorPhoto(src) {
      const wrap = document.querySelector('#view-executor-profile .executor-profile-cover');
      const img = wrap?.querySelector('img');
      if (!wrap || !img) return;
      wrap.classList.remove('v17-photo-ready');
      const wanted = avatar(src);
      const ok = await loadImage(wanted);
      const finalSrc = ok || FALLBACK_SITTER;
      if (img.src !== new URL(finalSrc, location.href).href) img.src = finalSrc;
      img.loading = 'eager';
      img.decoding = 'async';
      img.alt = 'Фото исполнителя';
      requestAnimationFrame(() => wrap.classList.add('v17-photo-ready'));
    }

    function ensureExecutorEditButton() {
      const menu = q('view-executor-profile')?.querySelector('.menu');
      if (!menu || q('v14EditExecProfile')) return;
      const b = document.createElement('button');
      b.id = 'v14EditExecProfile';
      b.type = 'button';
      b.onclick = () => window.openExecutorProfileSettingsV14?.();
      b.innerHTML = '<i class="fa-regular fa-id-card"></i><span>Редактировать профиль</span><i class="fa-solid fa-chevron-right"></i>';
      menu.prepend(b);
    }

    const fallbackExecutorProfile = window.loadExecutorProfile;
    window.loadExecutorProfile = async function () {
      if (executorProfilePromise) return executorProfilePromise;
      executorProfilePromise = (async () => {
        const wrap = document.querySelector('#view-executor-profile .executor-profile-cover');
        wrap?.classList.remove('v17-photo-ready');
        try {
          const [stats, profile] = await Promise.all([
            api('/api/executor/stats'),
            api('/api/executor/profile')
          ]);
          const h = q('executorProfileStats');
          if (h) h.innerHTML = `<div><strong>${Number(stats.completed || 0)}</strong><span>Завершено</span></div><div><strong>${Number(stats.rating || 5).toFixed(1)}</strong><span>Рейтинг</span></div><div><strong>${Number(stats.rank || 0)}</strong><span>Место</span></div>`;
          const name = q('executorProfileName');
          if (name && profile?.name) name.textContent = profile.name;
          await setExecutorPhoto(profile?.image || profile?.photo_url || '');
          ensureExecutorEditButton();
          return { stats, profile };
        } catch (e) {
          console.warn('v17 executor profile:', e);
          await setExecutorPhoto('');
          if (typeof fallbackExecutorProfile === 'function') {
            try { return await fallbackExecutorProfile(); } catch (_) {}
          }
          throw e;
        } finally {
          executorProfilePromise = null;
        }
      })();
      return executorProfilePromise;
    };

    /* The old client-profile chain fetched pets + orders and then fetched stats again.
       Render the same information from the dedicated stats endpoint in one request. */
    const fallbackClientProfile = window.loadClientProfile;
    window.loadClientProfile = async function () {
      if (clientProfilePromise) return clientProfilePromise;
      clientProfilePromise = (async () => {
        try {
          const s = await api('/api/client/stats');
          const h = q('clientProfileStats');
          if (h) h.innerHTML = `<div><strong>${Number(s.pets || 0)}</strong><span>Питомцев</span></div><div><strong>${Number(s.orders || 0)}</strong><span>Заказов</span></div><div><strong>${Number(s.done || 0)}</strong><span>Завершено</span></div>`;
          const done = Number(s.done || 0);
          const a = q('achievements');
          if (a) a.innerHTML = [
            ['fa-paw','Первый шаг','Выполнить первый заказ',done >= 1],
            ['fa-star','Опытный','Выполнить 5 заказов',done >= 5],
            ['fa-trophy','Постоянный клиент','Выполнить 10 заказов',done >= 10]
          ].map(([i,t,d,ok]) => `<div class="achievement"><i class="fa-solid ${i}"></i><span><b>${t}</b><small>${d}</small></span><span>${ok ? 'Готово' : 'Закрыто'}</span></div>`).join('');
          return s;
        } catch (e) {
          console.warn('v17 client profile:', e);
          if (typeof fallbackClientProfile === 'function') return fallbackClientProfile();
          throw e;
        } finally {
          clientProfilePromise = null;
        }
      })();
      return clientProfilePromise;
    };

    function guardAction(name, keyer = args => `${name}:${JSON.stringify(args)}`) {
      const fn = window[name];
      if (typeof fn !== 'function' || fn.__v17Guarded) return;
      const wrapped = async function (...args) {
        const key = keyer(args);
        if (locks.has(key)) return;
        locks.add(key);
        try { return await fn.apply(this, args); }
        finally { setTimeout(() => locks.delete(key), 250); }
      };
      wrapped.__v17Guarded = true;
      window[name] = wrapped;
    }

    [
      'submitBooking','buyTariff','acceptOrder','rejectOrderV14','setOrderStatus',
      'cancelOrder','savePet','saveExecutorProfileV14','saveAvailabilityV14',
      'deleteAvailabilityV14','submitReviewV14','saveReviewV14'
    ].forEach(name => guardAction(name));

    function installImageSafety(root = document) {
      root.querySelectorAll?.('img').forEach(img => {
        if (!img.alt) img.alt = '';
        img.decoding = 'async';
        if (!img.closest('.hero,.intro,.role-screen,.executor-profile-cover,.executor-hero')) img.loading = 'lazy';
      });
    }

    document.addEventListener('error', event => {
      const img = event.target;
      if (!(img instanceof HTMLImageElement) || img.dataset.v17Fallback) return;
      img.dataset.v17Fallback = '1';
      img.classList.add('v17-image-fallback');
      img.src = img.closest('.pet-pick,.v14-pet-card,.v15-order-pet,.v15-edit-pet') ? FALLBACK_PET : FALLBACK_SITTER;
    }, true);

    function networkBadge() {
      let el = q('v17Network');
      if (!el) {
        el = document.createElement('div');
        el.id = 'v17Network';
        el.className = 'v17-network';
        el.textContent = 'Нет соединения. Данные обновятся после подключения.';
        document.body.append(el);
      }
      el.classList.toggle('show', !navigator.onLine);
    }
    window.addEventListener('offline', networkBadge);
    window.addEventListener('online', () => {
      networkBadge();
      if (typeof window.toast === 'function') toast('Соединение восстановлено');
    });

    const previousShow = window.showView;
    window.showView = async function (view, ...args) {
      if (view === 'executor-profile') {
        document.querySelector('#view-executor-profile .executor-profile-cover')?.classList.remove('v17-photo-ready');
      }
      const result = await previousShow.call(this, view, ...args);
      installImageSafety(document.querySelector(`#view-${view}`) || document);
      return result;
    };

    const observer = new MutationObserver(mutations => {
      for (const m of mutations) for (const node of m.addedNodes) if (node.nodeType === 1) installImageSafety(node);
    });
    observer.observe(document.body, { childList: true, subtree: true });

    installStyles();
    installImageSafety();
    networkBadge();

    /* Prefetch while the profile is still hidden, so opening it never flashes the old stock photo. */
    const role = (() => {
      try { return typeof currentRole !== 'undefined' ? currentRole : localStorage.getItem('dh_role_v9'); }
      catch (_) { return ''; }
    })();
    if (role === 'executor') setTimeout(() => window.loadExecutorProfile().catch(() => {}), 80);
  }

  wait();
})();
