(() => {
  'use strict';

  const wait = (tries = 240) => {
    if (window.V17 && window.V14 && typeof window.api === 'function' && typeof window.showView === 'function') return boot();
    if (tries <= 0) return console.error('v18: runtime not ready');
    setTimeout(() => wait(tries - 1), 50);
  };

  function boot() {
    if (window.V18?.booted) return;
    window.V18 = { booted: true, version: 18, audit: {}, repeatDraft: null };

    const q = id => document.getElementById(id);
    const note = text => typeof window.toast === 'function' ? toast(text) : console.log(text);
    let meCache = null;
    let meAt = 0;

    function installStyles() {
      if (document.getElementById('v18-style')) return;
      const link = document.createElement('link');
      link.id = 'v18-style';
      link.rel = 'stylesheet';
      link.href = '/assets/app-v18.css?v=18';
      document.head.append(link);
    }

    async function getMe(force = false) {
      if (!force && meCache && Date.now() - meAt < 5000) return meCache;
      meCache = await api('/api/me');
      meAt = Date.now();
      return meCache;
    }

    async function syncIdentity(force = false) {
      const me = await getMe(force);
      const city = me?.city || 'Москва';
      try { localStorage.setItem('dh_city_v9', city); } catch (_) {}
      const cityLabel = q('cityLabel');
      if (cityLabel) cityLabel.textContent = city;

      if (me?.role && (me.role === 'client' || me.role === 'executor')) {
        try { localStorage.setItem('dh_role_v9', me.role); } catch (_) {}
        try {
          if (typeof currentRole !== 'undefined' && !currentRole) currentRole = me.role;
        } catch (_) {}
      }

      const displayName = String(me?.first_name || me?.username || 'Пользователь').trim();
      const clientName = q('clientProfileName');
      if (clientName) clientName.textContent = displayName;
      return me;
    }

    function dedupeLoader(name, gap = 60) {
      const original = window[name];
      if (typeof original !== 'function' || original.__v18Deduped) return;
      let pending = null, lastKey = '', lastAt = 0, lastValue;
      const wrapped = async function (...args) {
        let key = '';
        try { key = JSON.stringify(args); } catch (_) { key = String(args.length); }
        if (pending && pending.key === key) return pending.promise;
        if (key === lastKey && Date.now() - lastAt < gap) return lastValue;
        const promise = Promise.resolve(original.apply(this, args));
        pending = { key, promise };
        try {
          const value = await promise;
          lastKey = key;
          lastAt = Date.now();
          lastValue = value;
          return value;
        } finally {
          if (pending?.promise === promise) pending = null;
        }
      };
      wrapped.__v18Deduped = true;
      window[name] = wrapped;
    }

    const baseClientProfile = window.loadClientProfile;
    if (typeof baseClientProfile === 'function') {
      window.loadClientProfile = async function (...args) {
        const result = await baseClientProfile.apply(this, args);
        await syncIdentity().catch(() => {});
        return result;
      };
    }

    const baseExecutorProfile = window.loadExecutorProfile;
    if (typeof baseExecutorProfile === 'function') {
      window.loadExecutorProfile = async function (...args) {
        const result = await baseExecutorProfile.apply(this, args);
        try {
          const [me, profile] = await Promise.all([getMe(), api('/api/executor/profile')]);
          const name = q('executorProfileName');
          if (name) name.textContent = profile?.display_name || profile?.name || me?.first_name || me?.username || 'Исполнитель';
        } catch (_) {}
        return result;
      };
    }

    function visibleClientRows() {
      const all = window.V14?.orders || [];
      let tab = 'current';
      try { if (typeof orderTab !== 'undefined') tab = orderTab || 'current'; } catch (_) {}
      if (tab === 'history') return all.filter(o => o.status === 'done');
      if (tab === 'cancelled') return all.filter(o => ['cancelled','declined'].includes(o.status));
      return all.filter(o => !['done','cancelled','declined'].includes(o.status));
    }

    function decorateClientOrders() {
      const host = q('ordersList');
      if (!host) return;
      const rows = visibleClientRows();
      const cards = [...host.querySelectorAll('.v14-order-card')];
      cards.forEach((card, index) => {
        const order = rows[index];
        if (!order || !['done','cancelled','declined'].includes(order.status)) return;
        const actions = card.querySelector('.v14-order-actions');
        if (!actions || actions.querySelector('.v18-repeat-action')) return;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'v18-repeat-action';
        button.innerHTML = order.status === 'declined'
          ? '<i class="fa-solid fa-user-group"></i>Другой исполнитель'
          : '<i class="fa-solid fa-rotate-right"></i>Повторить';
        button.addEventListener('click', () => window.rebookOrderV18(order.id));
        actions.append(button);
      });
    }

    const baseLoadOrders = window.loadOrders;
    if (typeof baseLoadOrders === 'function') {
      window.loadOrders = async function (...args) {
        const result = await baseLoadOrders.apply(this, args);
        decorateClientOrders();
        return result;
      };
    }

    const baseOpenBooking = window.openBooking;
    if (typeof baseOpenBooking === 'function') {
      window.openBooking = async function (...args) {
        const result = await baseOpenBooking.apply(this, args);
        const draft = V18.repeatDraft;
        if (draft && Number(draft.item_id) === Number(args[0])) {
          const address = q('bookAddress');
          const notes = q('bookNotes');
          if (address && draft.address) address.value = draft.address;
          if (notes && draft.notes) notes.value = draft.notes;
          V18.repeatDraft = null;
        }
        return result;
      };
    }

    window.rebookOrderV18 = async function (id) {
      try {
        const order = await api('/api/orders/' + Number(id));
        const serviceId = Number(order.item_id);
        if (!serviceId) return note('Не удалось определить услугу');
        try {
          if (typeof bookingDuration !== 'undefined') bookingDuration = Number(order.duration_min || 60);
          if (typeof bookingPet !== 'undefined') bookingPet = order.pet_name || '';
          if (window.V14) V14.bookingPetId = Number(order.pet_id || 0) || null;
        } catch (_) {}
        V18.repeatDraft = {
          item_id: serviceId,
          address: order.address || '',
          notes: order.notes || ''
        };

        const oldExecutor = Number(order.executor_id || order.target_executor_id || 0);
        if (order.status === 'declined' || !oldExecutor) {
          await window.openServiceExecutors(serviceId);
          return;
        }

        const available = await api('/api/executors?service_id=' + serviceId);
        if (available.some(x => Number(x.id) === oldExecutor)) {
          await window.openBooking(serviceId, oldExecutor);
        } else {
          await window.openServiceExecutors(serviceId);
          note('Выберите доступного исполнителя');
        }
      } catch (e) {
        note(e?.message || 'Не удалось повторить заказ');
      }
    };

    [
      'loadClientHome','loadExecutorHome','loadClientProfile','loadExecutorProfile',
      'loadOrders','loadExecutor','loadCalendar','loadExecutorSchedule',
      'loadLeaderboard','loadPets'
    ].forEach(name => dedupeLoader(name));

    const baseShow = window.showView;
    window.showView = async function (view, ...args) {
      const result = await baseShow.call(this, view, ...args);
      if (['client-home','client-profile','executor-profile'].includes(view)) syncIdentity().catch(() => {});
      if (view === 'orders') decorateClientOrders();
      return result;
    };

    function runAudit() {
      const missing = new Set();
      document.querySelectorAll('[onclick]').forEach(el => {
        const raw = el.getAttribute('onclick') || '';
        for (const match of raw.matchAll(/\b([A-Za-z_$][\w$]*)\s*\(/g)) {
          const name = match[1];
          if (['if','for','while','confirm','stopPropagation'].includes(name)) continue;
          if (typeof window[name] !== 'function' && typeof globalThis[name] !== 'function') missing.add(name);
        }
      });
      const ids = [...document.querySelectorAll('[id]')].map(x => x.id);
      const duplicates = [...new Set(ids.filter((id, i) => ids.indexOf(id) !== i))];
      V18.audit = { missingHandlers: [...missing], duplicateIds: duplicates };
      if (missing.size || duplicates.length) console.warn('v18 audit', V18.audit);
    }

    installStyles();
    syncIdentity(true).catch(() => {});
    setTimeout(runAudit, 1200);
    window.addEventListener('pageshow', () => syncIdentity(true).catch(() => {}));
  }

  wait();
})();