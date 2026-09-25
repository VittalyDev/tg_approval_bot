(() => {
  'use strict';

  const wait = (tries = 260) => {
    if (window.V18 && window.V14 && typeof window.api === 'function' && typeof window.showView === 'function') return boot();
    if (tries <= 0) return console.error('v19: runtime not ready');
    setTimeout(() => wait(tries - 1), 50);
  };

  function boot() {
    if (window.V19?.booted) return;
    window.V19 = { booted: true, version: 19, settings: null };
    const q = id => document.getElementById(id);
    const safe = v => window.esc ? esc(v ?? '') : String(v ?? '').replace(/[<>&"]/g, '');
    const note = t => window.toast ? toast(t) : alert(t);

    function installStyles() {
      if (q('v19-style')) return;
      const link = document.createElement('link');
      link.id = 'v19-style';
      link.rel = 'stylesheet';
      link.href = '/assets/app-v19.css?v=19';
      document.head.append(link);
    }

    async function settings(force = false) {
      if (!force && V19.settings) return V19.settings;
      V19.settings = await api('/api/settings');
      return V19.settings;
    }

    function closeModal() { q('v19ModalBackdrop')?.remove(); }
    window.closeV19Modal = closeModal;

    function modal(title, subtitle, body, actions = '') {
      closeModal();
      const d = document.createElement('div');
      d.id = 'v19ModalBackdrop';
      d.className = 'v19-modal-backdrop';
      d.onclick = e => { if (e.target === d) closeModal(); };
      d.innerHTML = `<div class="v19-modal" onclick="event.stopPropagation()">
        <div class="v19-modal-head"><div><h2>${safe(title)}</h2>${subtitle ? `<p>${safe(subtitle)}</p>` : ''}</div><button class="v19-modal-close" type="button" onclick="closeV19Modal()"><i class="fa-solid fa-xmark"></i></button></div>
        ${body}
        ${actions ? `<div class="v19-modal-actions">${actions}</div>` : ''}
      </div>`;
      document.body.append(d);
      return d;
    }

    function currentRoleValue() {
      try { return typeof currentRole !== 'undefined' ? currentRole : (localStorage.getItem('dh_role_v9') || 'client'); }
      catch (_) { return 'client'; }
    }

    function installRoleCtas() {
      const client = q('view-client-home');
      if (client && !q('v19ClientRoleCta')) {
        const c = document.createElement('div');
        c.id = 'v19ClientRoleCta';
        c.className = 'v19-role-cta';
        c.innerHTML = '<i class="fa-solid fa-briefcase"></i><span><b>Хотите работать с питомцами?</b><small>Станьте выгульщиком, зооняней или кинологом. Анкета занимает пару минут.</small></span><button type="button" onclick="startRoleSwitchV19()">Стать исполнителем</button>';
        client.querySelector('.topbar')?.insertAdjacentElement('afterend', c);
      }
      const exec = q('view-executor-home');
      if (exec && !q('v19ExecRoleCta')) {
        const c = document.createElement('div');
        c.id = 'v19ExecRoleCta';
        c.className = 'v19-role-cta';
        c.innerHTML = '<i class="fa-solid fa-paw"></i><span><b>Режим исполнителя</b><small>Нужно заказать услугу для своего питомца? Переключитесь в режим хозяина.</small></span><button type="button" onclick="startRoleSwitchV19()">Режим хозяина</button>';
        exec.querySelector('.topbar')?.insertAdjacentElement('afterend', c);
      }
    }

    const oldChooseRole = window.chooseRole;
    const oldSwitchRole = window.switchRoleV14;

    async function enterExecutorOrOnboard(action) {
      try {
        const s = await settings(true);
        if (!s.executor_onboarding_complete) {
          await window.openExecutorOnboardingV19();
          return false;
        }
        await action();
        return true;
      } catch (e) {
        note(e?.message || 'Не удалось переключить роль');
        return false;
      }
    }

    window.chooseRole = async role => {
      if (role !== 'executor') return oldChooseRole(role);
      return enterExecutorOrOnboard(() => oldChooseRole(role));
    };

    window.switchRoleV14 = async role => {
      if (role !== 'executor') {
        const result = await oldSwitchRole(role);
        V19.settings = null;
        return result;
      }
      return enterExecutorOrOnboard(async () => {
        const result = await oldSwitchRole(role);
        V19.settings = null;
        return result;
      });
    };

    window.startRoleSwitchV19 = async () => {
      if (currentRoleValue() === 'executor') return window.switchRoleV14('client');
      return window.switchRoleV14('executor');
    };

    window.openExecutorOnboardingV19 = async () => {
      try {
        const [s, catalog, profile] = await Promise.all([
          settings(true),
          api('/api/catalog'),
          api('/api/executor/profile')
        ]);
        const p = profile || {};
        const services = new Set((p.services || []).map(Number));
        modal(
          'Анкета исполнителя',
          'Это обязательный шаг перед публикацией профиля. Данные можно будет изменить позже.',
          `<div class="v19-form">
            <label><span>Имя, которое увидят клиенты</span><input id="v19ExecName" class="field" maxlength="80" value="${safe(p.name || '')}" placeholder="Например, Анна"></label>
            <label><span>Город</span><select id="v19ExecCity" class="field">${(s.cities || []).map(city => `<option ${city === (p.city || s.city) ? 'selected' : ''}>${safe(city)}</option>`).join('')}</select></label>
            <label><span>Район / зона работы</span><input id="v19ExecArea" class="field" maxlength="80" value="${safe(p.area || '')}" placeholder="Например, Хамовники"></label>
            <label><span>Опыт</span><input id="v19ExecExperience" class="field" maxlength="160" value="${safe(p.experience || '')}" placeholder="Например, 3 года, крупные и активные собаки"></label>
            <label><span>О себе</span><textarea id="v19ExecBio" class="field" maxlength="800" placeholder="Подход к питомцам, график, особенности работы">${safe(p.bio || '')}</textarea></label>
            <label><span>Цена от, ₽</span><input id="v19ExecPrice" class="field" type="number" min="300" max="10000" value="${Number(p.price || 700)}"></label>
            <div><span style="display:block;margin-bottom:7px;color:#d9c9af;font-size:10px;font-weight:800">Какие услуги вы оказываете</span><div class="v19-checks">${catalog.map(item => `<label><input type="checkbox" value="${item.id}" ${services.has(Number(item.id)) ? 'checked' : ''}><span>${safe(item.name)}</span></label>`).join('')}</div></div>
            <label class="v19-consent"><input id="v19ExecConsent" type="checkbox"><span>Согласен(на) на обработку данных анкеты для публикации профиля исполнителя в сервисе.</span></label>
          </div>`,
          '<button id="v19ExecSubmit" class="btn btn-gold btn-wide" type="button" onclick="submitExecutorOnboardingV19()">Сохранить анкету и стать исполнителем</button>'
        );
      } catch (e) {
        note(e?.message || 'Не удалось открыть анкету');
      }
    };

    window.submitExecutorOnboardingV19 = async () => {
      const services = [...document.querySelectorAll('.v19-checks input:checked')].map(x => Number(x.value));
      const payload = {
        display_name: q('v19ExecName')?.value?.trim() || '',
        city: q('v19ExecCity')?.value || '',
        area: q('v19ExecArea')?.value?.trim() || '',
        experience: q('v19ExecExperience')?.value?.trim() || '',
        bio: q('v19ExecBio')?.value?.trim() || '',
        price: Number(q('v19ExecPrice')?.value || 700),
        services
      };
      if (payload.display_name.length < 2) return note('Укажите имя');
      if (payload.area.length < 2) return note('Укажите район работы');
      if (payload.experience.length < 3) return note('Коротко укажите опыт');
      if (!services.length) return note('Выберите хотя бы одну услугу');
      if (!q('v19ExecConsent')?.checked) return note('Нужно подтвердить согласие на обработку данных');
      const btn = q('v19ExecSubmit');
      if (btn) { btn.disabled = true; btn.textContent = 'Сохраняем…'; }
      try {
        await api('/api/executor/onboarding', { method:'POST', body:JSON.stringify(payload) });
        V19.settings = null;
        try { currentRole = 'executor'; localStorage.setItem('dh_role_v9','executor'); } catch (_) {}
        closeModal();
        await window.showView('executor-home');
        note('Анкета сохранена. Профиль исполнителя опубликован');
      } catch (e) {
        note(e?.message || 'Не удалось сохранить анкету');
      } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Сохранить анкету и стать исполнителем'; }
      }
    };

    function installExecutorChoiceNote() {
      const host = q('v9ExecList');
      if (!host || q('v19ExecChoiceNote')) return;
      const n = document.createElement('div');
      n.id = 'v19ExecChoiceNote';
      n.className = 'v19-exec-choice-note';
      n.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i><span><b>Вы выбираете исполнителя сами.</b><br>Система показывает подходящих активных специалистов по услуге и городу; после выбора проверяется их расписание.</span>';
      host.insertAdjacentElement('beforebegin', n);
    }

    const oldOpenServiceExecutors = window.openServiceExecutors;
    window.openServiceExecutors = async function (...args) {
      const result = await oldOpenServiceExecutors.apply(this, args);
      installExecutorChoiceNote();
      return result;
    };

    function normalizeExecutorBadges(root = document) {
      root.querySelectorAll?.('.v13-badges em,.v9-badges .v9-badge').forEach(el => {
        if (el.textContent.trim() === 'Свободен') el.textContent = 'Принимает заявки';
      });
    }

    function installSupportView() {
      if (q('view-support')) return;
      const section = document.createElement('section');
      section.id = 'view-support';
      section.className = 'view hidden';
      section.innerHTML = `<div class="screen-head"><button class="back" onclick="goHome()"><i class="fa-solid fa-chevron-left"></i></button><h1>Поддержка</h1></div>
        <div class="v19-support-intro"><b>Помощник Dog’s Happiness</b><small>Сначала отвечает бот. Если вопрос не решён, можно одним нажатием передать диалог оператору.</small></div>
        <div id="v19SupportMessages" class="v19-support-messages"></div>
        <button id="v19OperatorButton" class="v19-operator-btn" type="button" onclick="requestOperatorV19()"><i class="fa-solid fa-headset"></i> Позвать оператора</button>
        <div class="v19-support-compose"><input id="v19SupportInput" maxlength="1200" placeholder="Напишите вопрос" onkeydown="if(event.key==='Enter'){event.preventDefault();sendSupportV19()}"><button type="button" onclick="sendSupportV19()"><i class="fa-solid fa-paper-plane"></i></button></div>`;
      q('app')?.append(section);
    }

    function installSupportEntrypoints() {
      document.querySelectorAll('#view-client-home .advantages>div:last-child').forEach(el => {
        el.style.cursor = 'pointer';
        el.setAttribute('role','button');
        el.onclick = () => window.openSupportV19();
      });
      for (const viewId of ['view-client-home','view-executor-home']) {
        const view = q(viewId);
        if (!view || view.querySelector('.v19-support-cta')) continue;
        const btn = document.createElement('button');
        btn.className = 'v19-support-cta';
        btn.type = 'button';
        btn.onclick = () => window.openSupportV19();
        btn.innerHTML = '<span><b>Нужна помощь?</b><small>Спросите бота или подключите оператора</small></span><i class="fa-solid fa-chevron-right"></i>';
        view.append(btn);
      }
      for (const viewId of ['view-client-profile','view-executor-profile']) {
        const menu = q(viewId)?.querySelector('.menu');
        if (menu && !menu.querySelector('.v19-profile-support')) {
          const b = document.createElement('button');
          b.className = 'v19-profile-support';
          b.type = 'button';
          b.onclick = () => window.openSupportV19();
          b.innerHTML = '<i class="fa-solid fa-headset"></i><span>Поддержка</span><i class="fa-solid fa-chevron-right"></i>';
          menu.append(b);
        }
      }
    }

    function supportTextType(m) {
      if (m.sender === 'user') return 'user';
      if (m.sender === 'operator') return 'operator';
      return 'bot';
    }

    async function loadSupportV19() {
      const host = q('v19SupportMessages');
      if (!host) return;
      try {
        const data = await api('/api/support/messages');
        host.innerHTML = (data.messages || []).map(m => `<div class="v19-msg ${supportTextType(m)}">${safe(m.text)}<small>${safe(m.created_at_label || '')}</small></div>`).join('');
        const op = q('v19OperatorButton');
        if (op && data.handoff_open) {
          op.disabled = true;
          op.innerHTML = '<i class="fa-solid fa-headset"></i> Оператор уже приглашён';
        }
        requestAnimationFrame(() => host.lastElementChild?.scrollIntoView({block:'end'}));
      } catch (e) {
        host.innerHTML = '<div class="v19-msg bot">Не удалось загрузить поддержку. Попробуйте ещё раз.</div>';
      }
    }

    window.openSupportV19 = async () => {
      installSupportView();
      await window.showView('support');
      await loadSupportV19();
    };

    window.sendSupportV19 = async () => {
      const input = q('v19SupportInput');
      const text = input?.value?.trim() || '';
      if (!text) return;
      input.value = '';
      try {
        await api('/api/support/messages', {method:'POST', body:JSON.stringify({text})});
        await loadSupportV19();
      } catch (e) { note(e?.message || 'Не удалось отправить сообщение'); }
    };

    window.requestOperatorV19 = async () => {
      try {
        await api('/api/support/handoff', {method:'POST', body:'{}'});
        await loadSupportV19();
        note('Диалог передан оператору');
      } catch (e) { note(e?.message || 'Не удалось позвать оператора'); }
    };

    window.renderTariffs = async () => {
      const [plans, sub] = await Promise.all([ensureTariffs(), api('/api/subscription')]);
      const host = q('tariffList');
      if (!host) return;
      host.innerHTML = plans.map(p => {
        const current = sub?.plan_id === p.id;
        return `<div class="tariff-card ${p.badge ? 'featured' : ''}">
          ${p.badge ? `<span class="tariff-badge">${safe(p.badge)}</span>` : ''}
          <h3>${safe(p.name)}</h3>
          <div class="tariff-price">${Number(p.price).toLocaleString('ru-RU')} ₽ <small>/ месяц</small></div>
          <div class="tariff-desc">${safe(p.desc)}</div>
          <div class="tariff-details"><div class="tariff-detail">${p.walks} прогулок</div><div class="tariff-detail">Фотоотчёт</div></div>
          <button class="btn ${current ? 'btn-dark' : 'btn-gold'} btn-wide" ${current ? 'disabled' : ''} onclick="payTariffV19('${p.id}')">${current ? 'Текущий тариф' : 'Оплатить'}</button>
        </div>`;
      }).join('');
      if (!q('v19PaymentHint')) {
        const h = document.createElement('div');
        h.id = 'v19PaymentHint';
        h.className = 'v19-payment-hint';
        h.textContent = 'Оплата подключается через ЮKassa. В тестовом режиме списание денег не выполняется.';
        host.insertAdjacentElement('afterend', h);
      }
    };
    window.buyTariff = id => window.payTariffV19(id);

    window.payTariffV19 = async id => {
      try {
        const r = await api('/api/payments/yookassa', {method:'POST', body:JSON.stringify({plan_id:id})});
        if (r.demo) {
          note('Тестовая оплата прошла. Абонемент подключён');
          await window.renderTariffs();
          if (typeof loadClientHome === 'function') await loadClientHome();
          return;
        }
        if (r.confirmation_url) {
          if (window.Telegram?.WebApp?.openLink) Telegram.WebApp.openLink(r.confirmation_url);
          else location.href = r.confirmation_url;
          return;
        }
        note('Не удалось открыть оплату');
      } catch (e) { note(e?.message || 'Не удалось создать платёж'); }
    };

    function installLegalModal() {
      let accepted = false;
      try { accepted = localStorage.getItem('dh_legal_v19') === '1'; } catch (_) {}
      if (accepted || q('v19Legal')) return;
      const d = document.createElement('div');
      d.id = 'v19Legal';
      d.className = 'v19-modal-backdrop';
      d.innerHTML = `<div class="v19-modal" onclick="event.stopPropagation()">
        <div class="v19-modal-head"><div><h2>Данные и cookies</h2><p>Временный информационный блок до финальной проверки документов юристом.</p></div></div>
        <div class="v19-legal-copy">Для работы Mini App используются локальное хранилище/cookies и данные профиля Telegram. Документы можно открыть по ссылкам: <a href="/assets/legal/privacy.html" target="_blank">политика конфиденциальности</a>, <a href="/assets/legal/personal-data.html" target="_blank">обработка персональных данных</a>, <a href="/assets/legal/cookies.html" target="_blank">cookies</a>.</div>
        <label class="v19-legal-row"><input id="v19LegalPersonal" type="checkbox"><span>Согласен(на) на обработку персональных данных для работы сервиса.</span></label>
        <label class="v19-legal-row"><input id="v19LegalCookies" type="checkbox"><span>Ознакомлен(а) с использованием cookies / локального хранилища.</span></label>
        <div class="v19-modal-actions"><button class="btn btn-gold btn-wide" type="button" onclick="acceptLegalV19()">Продолжить</button></div>
      </div>`;
      document.body.append(d);
    }

    window.acceptLegalV19 = async () => {
      if (!q('v19LegalPersonal')?.checked || !q('v19LegalCookies')?.checked) return note('Подтвердите оба пункта');
      try { await api('/api/legal/consent', {method:'POST', body:JSON.stringify({personal_data:true,cookies:true})}); } catch (_) {}
      try { localStorage.setItem('dh_legal_v19','1'); } catch (_) {}
      q('v19Legal')?.remove();
    };

    const baseShow = window.showView;
    window.showView = async function(view, ...args) {
      if (String(view).startsWith('executor-')) {
        try {
          const s = await settings();
          if (!s.executor_onboarding_complete) {
            const r = await baseShow.call(this, 'client-home');
            setTimeout(() => window.openExecutorOnboardingV19(), 0);
            return r;
          }
        } catch (_) {}
      }
      const result = await baseShow.call(this, view, ...args);
      installRoleCtas();
      installSupportEntrypoints();
      normalizeExecutorBadges(q('view-' + view) || document);
      if (view === 'service-executors') installExecutorChoiceNote();
      if (view === 'support') await loadSupportV19();
      return result;
    };

    const obs = new MutationObserver(mutations => {
      normalizeExecutorBadges();
      installRoleCtas();
      installSupportEntrypoints();
      if (q('v9ExecList')) installExecutorChoiceNote();
    });
    obs.observe(document.body, {childList:true, subtree:true});

    installStyles();
    installSupportView();
    installRoleCtas();
    installSupportEntrypoints();
    normalizeExecutorBadges();
    setTimeout(installLegalModal, 650);
    setTimeout(async () => {
      if (currentRoleValue() === 'executor') {
        try {
          const s = await settings(true);
          if (!s.executor_onboarding_complete) window.openExecutorOnboardingV19();
        } catch (_) {}
      }
    }, 900);
  }

  wait();
})();