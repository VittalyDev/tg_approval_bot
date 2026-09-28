(() => {
  'use strict';

  const wait = (tries = 240) => {
    if (window.V19 && typeof window.api === 'function') return boot();
    if (tries <= 0) return console.error('v20: runtime not ready');
    setTimeout(() => wait(tries - 1), 50);
  };

  function boot() {
    if (window.V20?.booted) return;
    window.V20 = { booted: true, version: 20, step: 0, data: {}, catalog: [], settings: null };

    const q = id => document.getElementById(id);
    const esc = value => String(value ?? '')
      .replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')
      .replaceAll('"','&quot;').replaceAll("'","&#39;");
    const toast = text => window.toast ? window.toast(text) : alert(text);

    if (!q('v20-style')) {
      const link = document.createElement('link');
      link.id = 'v20-style';
      link.rel = 'stylesheet';
      link.href = '/assets/app-v20.css?v=20';
      document.head.append(link);
    }

    const yesNo = (name, value) => `
      <div class="v20-choice-row">
        <label class="v20-choice"><input type="radio" name="${name}" value="Да" ${value === 'Да' ? 'checked' : ''}><span>Да</span></label>
        <label class="v20-choice"><input type="radio" name="${name}" value="Нет" ${value === 'Нет' ? 'checked' : ''}><span>Нет</span></label>
      </div>`;

    const radio = (name, options, value) => `
      <div class="v20-choice-grid">${options.map(x => `
        <label class="v20-choice"><input type="radio" name="${name}" value="${esc(x)}" ${value === x ? 'checked' : ''}><span>${esc(x)}</span></label>
      `).join('')}</div>`;

    const selectedValues = selector => [...document.querySelectorAll(selector + ':checked')].map(x => x.value);

    function close() {
      q('v20ExecutorApplication')?.remove();
      document.body.classList.remove('v20-lock');
    }
    window.closeExecutorApplicationV20 = close;

    function field(id, label, value = '', placeholder = '', type = 'text', attrs = '') {
      return `<label class="v20-field"><span>${esc(label)}</span><input id="${id}" type="${type}" value="${esc(value)}" placeholder="${esc(placeholder)}" ${attrs}></label>`;
    }

    function textarea(id, label, value = '', placeholder = '', attrs = '') {
      return `<label class="v20-field"><span>${esc(label)}</span><textarea id="${id}" placeholder="${esc(placeholder)}" ${attrs}>${esc(value)}</textarea></label>`;
    }

    function serviceChecks(selected) {
      const set = new Set((selected || []).map(Number));
      return `<div class="v20-check-grid">${V20.catalog.map(item => `
        <label class="v20-check"><input type="checkbox" name="v20_services" value="${item.id}" ${set.has(Number(item.id)) ? 'checked' : ''}><span><i class="fa-solid fa-paw"></i>${esc(item.name)}</span></label>
      `).join('')}</div>`;
    }

    function dayChecks(selected) {
      const days = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
      const set = new Set(selected || []);
      return `<div class="v20-days">${days.map(day => `
        <label><input type="checkbox" name="v20_work_days" value="${day}" ${set.has(day) ? 'checked' : ''}><span>${day}</span></label>
      `).join('')}</div>`;
    }

    function stepMarkup(step) {
      const d = V20.data;
      if (step === 0) return `
        <div class="v20-step-title"><em>01</em><div><h3>Общая информация</h3><p>Основные данные для профиля и связи с вами.</p></div></div>
        <div class="v20-grid two">
          ${field('v20_full_name','ФИО',d.full_name,'Анна Иванова','text','maxlength="120"')}
          ${field('v20_age','Возраст',d.age || '','Например, 27','number','min="18" max="80"')}
        </div>
        <div class="v20-field"><span>Основная деятельность в сервисе</span>
          ${radio('v20_primary_activity',['Выгульщик','Зооняня','Кинолог','Другое'],d.primary_activity)}
        </div>
        <label class="v20-field"><span>Город</span><select id="v20_city">
          ${(V20.settings?.cities || ['Москва']).map(city => `<option ${city === (d.city || V20.settings?.city || 'Москва') ? 'selected' : ''}>${esc(city)}</option>`).join('')}
        </select></label>
        ${field('v20_areas','Предпочтительные районы работы',d.preferred_areas,'Например, Хамовники, Арбат','text','maxlength="180"')}
        <div class="v20-grid two">
          ${field('v20_phone','Контактный телефон',d.phone,'+7 999 123-45-67','tel','maxlength="30"')}
          ${field('v20_telegram','Ник в Telegram',d.telegram_username,'@username','text','maxlength="80"')}
        </div>
        <div class="v20-field"><span>Статус самозанятости</span>
          ${radio('v20_self_employed',['Оформлена','Нет','В процессе'],d.self_employed_status)}
        </div>
        <div class="v20-field"><span>Если самозанятости нет, нужна помощь с оформлением?</span>
          ${yesNo('v20_self_employed_help',d.self_employed_help)}
        </div>`;

      if (step === 1) return `
        <div class="v20-step-title"><em>02</em><div><h3>Специализация и услуги</h3><p>Что вы умеете и с какими питомцами работаете.</p></div></div>
        <div class="v20-field"><span>Какие услуги вы оказываете?</span>${serviceChecks(d.services)}</div>
        ${field('v20_animals','С какими животными работаете?',d.animals,'Собаки, кошки','text','maxlength="220"')}
        ${textarea('v20_restrictions','Есть ли ограничения по породам, размерам или характеру?',d.restrictions,'Например: не беру собак тяжелее 45 кг','maxlength="500"')}
        <div class="v20-grid two">
          ${field('v20_experience_years','Опыт работы, лет',d.experience_years ?? '','Например, 3','number','min="0" max="50" step="0.5"')}
          ${field('v20_education','Профильное образование / сертификаты',d.education,'Если есть — перечислите','text','maxlength="300"')}
        </div>
        ${textarea('v20_recent_courses','Курсы повышения квалификации за последние 2 года',d.recent_courses,'Название курса и год, либо «нет»','maxlength="500"')}`;

      if (step === 2) return `
        <div class="v20-step-title"><em>03</em><div><h3>Условия оказания услуг</h3><p>Где и в каком формате вы готовы работать.</p></div></div>
        <div class="v20-field"><span>Где оказываются услуги?</span>
          ${radio('v20_service_location',['У клиента','У исполнителя','На улице / выезд','В салоне'],d.service_location)}
        </div>
        <div class="v20-field"><span>Есть отдельное помещение для животных?</span>${yesNo('v20_separate_room',d.separate_room)}</div>
        ${field('v20_simultaneous','Сколько животных одновременно берёте в работу?',d.simultaneous_pets || '1','Например, 2','number','min="1" max="20"')}
        <div class="v20-grid two">
          <div class="v20-field"><span>Готовы подписать договор с сервисом?</span>${yesNo('v20_contract_ready',d.contract_ready)}</div>
          <div class="v20-field"><span>Принимаете срочные заказы?</span>${yesNo('v20_urgent_orders',d.urgent_orders)}</div>
        </div>`;

      if (step === 3) return `
        <div class="v20-step-title"><em>04</em><div><h3>Безопасность и ответственность</h3><p>Важно понимать, как вы действуете в сложных ситуациях.</p></div></div>
        <div class="v20-field"><span>Есть опыт работы с агрессивными или тревожными животными?</span>${yesNo('v20_anxious_experience',d.anxious_experience)}</div>
        <div class="v20-field"><span>Знаете основы первой помощи животным?</span>${yesNo('v20_first_aid',d.first_aid)}</div>
        ${textarea('v20_emergency','Как вы действуете в экстренной ситуации?',d.emergency_response,'Кратко опишите порядок действий','maxlength="700"')}
        <div class="v20-field"><span>Можете делать фото/видео отчёты и включать геолокацию во время заказа?</span>${yesNo('v20_reports_geo',d.reports_geo)}</div>`;

      if (step === 4) return `
        <div class="v20-step-title"><em>05</em><div><h3>График и доступность</h3><p>Клиентам и оператору будет проще не допускать накладок.</p></div></div>
        <div class="v20-field"><span>Дни работы</span>${dayChecks(d.work_days)}</div>
        ${field('v20_work_hours','Часы работы',d.work_hours,'Например, 09:00–21:00','text','maxlength="120"')}
        <div class="v20-grid two">
          <div class="v20-field"><span>Работаете в выходные?</span>${yesNo('v20_weekends',d.weekends)}</div>
          <div class="v20-field"><span>Работаете в праздники?</span>${yesNo('v20_holidays',d.holidays)}</div>
        </div>`;

      return `
        <div class="v20-step-title"><em>06</em><div><h3>Дополнительные вопросы</h3><p>Последний шаг — и кабинет исполнителя будет готов.</p></div></div>
        <div class="v20-field"><span>Согласны соблюдать стандарты сервиса?</span>${yesNo('v20_standards',d.standards_agreement)}</div>
        ${textarea('v20_cooperation','Что для вас важно в сотрудничестве с сервисом?',d.cooperation_priorities,'Например: понятное расписание, своевременная связь','maxlength="700"')}
        ${textarea('v20_extra','Есть ли дополнительная информация, которую нам нужно знать?',d.extra_info,'Необязательно','maxlength="700"')}
        ${field('v20_own_pet','Есть ли у вас свой питомец? :)',d.own_pet,'Например: корги Бублик, 4 года','text','maxlength="220"')}
        <label class="v20-consent"><input id="v20_confirm" type="checkbox" ${d.confirmed ? 'checked' : ''}><span>Подтверждаю, что данные анкеты актуальны, и согласен(на) использовать их для работы в сервисе.</span></label>`;
    }

    function readRadio(name) {
      return document.querySelector(`input[name="${name}"]:checked`)?.value || '';
    }

    function capture() {
      const d = V20.data;
      if (q('v20_full_name')) {
        d.full_name = q('v20_full_name').value.trim();
        d.age = Number(q('v20_age').value || 0);
        d.primary_activity = readRadio('v20_primary_activity');
        d.city = q('v20_city').value;
        d.preferred_areas = q('v20_areas').value.trim();
        d.phone = q('v20_phone').value.trim();
        d.telegram_username = q('v20_telegram').value.trim();
        d.self_employed_status = readRadio('v20_self_employed');
        d.self_employed_help = readRadio('v20_self_employed_help');
      }
      if (q('v20_animals')) {
        d.services = selectedValues('input[name="v20_services"]');
        d.animals = q('v20_animals').value.trim();
        d.restrictions = q('v20_restrictions').value.trim();
        d.experience_years = Number(q('v20_experience_years').value || 0);
        d.education = q('v20_education').value.trim();
        d.recent_courses = q('v20_recent_courses').value.trim();
      }
      if (q('v20_simultaneous')) {
        d.service_location = readRadio('v20_service_location');
        d.separate_room = readRadio('v20_separate_room');
        d.simultaneous_pets = Number(q('v20_simultaneous').value || 1);
        d.contract_ready = readRadio('v20_contract_ready');
        d.urgent_orders = readRadio('v20_urgent_orders');
      }
      if (q('v20_emergency')) {
        d.anxious_experience = readRadio('v20_anxious_experience');
        d.first_aid = readRadio('v20_first_aid');
        d.emergency_response = q('v20_emergency').value.trim();
        d.reports_geo = readRadio('v20_reports_geo');
      }
      if (q('v20_work_hours')) {
        d.work_days = selectedValues('input[name="v20_work_days"]');
        d.work_hours = q('v20_work_hours').value.trim();
        d.weekends = readRadio('v20_weekends');
        d.holidays = readRadio('v20_holidays');
      }
      if (q('v20_cooperation')) {
        d.standards_agreement = readRadio('v20_standards');
        d.cooperation_priorities = q('v20_cooperation').value.trim();
        d.extra_info = q('v20_extra').value.trim();
        d.own_pet = q('v20_own_pet').value.trim();
        d.confirmed = !!q('v20_confirm')?.checked;
      }
    }

    function validate(step) {
      const d = V20.data;
      if (step === 0) {
        if (d.full_name.length < 5) return 'Укажите ФИО';
        if (d.age < 18 || d.age > 80) return 'Укажите корректный возраст (18+)';
        if (!d.primary_activity) return 'Выберите основную деятельность';
        if (!d.preferred_areas) return 'Укажите районы работы';
        if ((d.phone.match(/\d/g) || []).length < 10) return 'Укажите контактный телефон';
        if (!d.telegram_username) return 'Укажите Telegram';
      }
      if (step === 1) {
        if (!d.services?.length) return 'Выберите хотя бы одну услугу';
        if (!d.animals) return 'Укажите, с какими животными работаете';
        if (d.experience_years < 0 || d.experience_years > 50) return 'Проверьте опыт работы';
      }
      if (step === 2) {
        if (!d.service_location) return 'Укажите, где оказываете услуги';
        if (!d.contract_ready) return 'Ответьте про договор с сервисом';
        if (!d.urgent_orders) return 'Ответьте про срочные заказы';
      }
      if (step === 3) {
        if (!d.first_aid) return 'Ответьте про первую помощь';
        if (d.emergency_response.length < 10) return 'Кратко опишите действия в экстренной ситуации';
        if (!d.reports_geo) return 'Ответьте про фото/видео отчёты и геолокацию';
      }
      if (step === 4) {
        if (!d.work_days?.length) return 'Выберите дни работы';
        if (!d.work_hours) return 'Укажите часы работы';
      }
      if (step === 5) {
        if (d.standards_agreement !== 'Да') return 'Для работы нужно согласиться соблюдать стандарты сервиса';
        if (!d.confirmed) return 'Подтвердите актуальность данных анкеты';
      }
      return '';
    }

    function render() {
      const host = q('v20ExecutorBody');
      if (!host) return;
      host.innerHTML = stepMarkup(V20.step);
      q('v20StepLabel').textContent = `Шаг ${V20.step + 1} из 6`;
      q('v20ProgressFill').style.width = `${((V20.step + 1) / 6) * 100}%`;
      q('v20Prev').style.visibility = V20.step === 0 ? 'hidden' : 'visible';
      q('v20Next').textContent = V20.step === 5 ? (V20.data._editing ? 'Сохранить изменения' : 'Отправить анкету') : 'Продолжить';
      q('v20Next').innerHTML += V20.step === 5 ? ' <i class="fa-solid fa-check"></i>' : ' <i class="fa-solid fa-arrow-right"></i>';
      q('v20ExecutorBody').scrollTop = 0;
    }

    window.v20PrevStep = () => {
      capture();
      if (V20.step > 0) V20.step -= 1;
      render();
    };

    window.v20NextStep = async () => {
      capture();
      const error = validate(V20.step);
      if (error) return toast(error);
      if (V20.step < 5) {
        V20.step += 1;
        render();
        return;
      }
      const btn = q('v20Next');
      if (btn) { btn.disabled = true; btn.textContent = 'Сохраняем…'; }
      try {
        const payload = { ...V20.data };
        delete payload._editing;
        await api('/api/executor/application', { method:'POST', body: JSON.stringify(payload) });
        if (window.V19) V19.settings = null;
        try { currentRole = 'executor'; localStorage.setItem('dh_role_v9','executor'); } catch (_) {}
        close();
        await window.showView('executor-home');
        toast(V20.data._editing ? 'Анкета обновлена' : 'Анкета сохранена. Кабинет исполнителя открыт');
      } catch (e) {
        toast(e?.message || 'Не удалось сохранить анкету');
        if (btn) { btn.disabled = false; render(); }
      }
    };

    window.openExecutorOnboardingV19 = async () => {
      try {
        const [settings, catalog, profile, application] = await Promise.all([
          api('/api/settings'),
          api('/api/catalog'),
          api('/api/executor/profile'),
          api('/api/executor/application')
        ]);
        V20.settings = settings || {};
        V20.catalog = catalog || [];
        const p = profile || {};
        const saved = application?.data || {};
        V20.data = {
          full_name: saved.full_name || p.name || '',
          age: saved.age || '',
          primary_activity: saved.primary_activity || '',
          city: saved.city || p.city || settings?.city || 'Москва',
          preferred_areas: saved.preferred_areas || p.area || '',
          phone: saved.phone || '',
          telegram_username: saved.telegram_username || '',
          self_employed_status: saved.self_employed_status || '',
          self_employed_help: saved.self_employed_help || '',
          services: saved.services || p.services || [],
          animals: saved.animals || '',
          restrictions: saved.restrictions || '',
          experience_years: saved.experience_years ?? '',
          education: saved.education || '',
          recent_courses: saved.recent_courses || '',
          service_location: saved.service_location || '',
          separate_room: saved.separate_room || '',
          simultaneous_pets: saved.simultaneous_pets || 1,
          contract_ready: saved.contract_ready || '',
          urgent_orders: saved.urgent_orders || '',
          anxious_experience: saved.anxious_experience || '',
          first_aid: saved.first_aid || '',
          emergency_response: saved.emergency_response || '',
          reports_geo: saved.reports_geo || '',
          work_days: saved.work_days || [],
          work_hours: saved.work_hours || '',
          weekends: saved.weekends || '',
          holidays: saved.holidays || '',
          standards_agreement: saved.standards_agreement || '',
          cooperation_priorities: saved.cooperation_priorities || '',
          extra_info: saved.extra_info || '',
          own_pet: saved.own_pet || '',
          confirmed: false,
          _editing: !!settings?.executor_onboarding_complete
        };
        V20.step = 0;
        close();
        const overlay = document.createElement('div');
        overlay.id = 'v20ExecutorApplication';
        overlay.className = 'v20-overlay';
        overlay.innerHTML = `
          <div class="v20-application">
            <div class="v20-app-head">
              <div class="v20-brand"><span><i class="fa-solid fa-paw"></i></span><div><small>DOG’S HAPPINESS</small><b>Анкета исполнителя</b></div></div>
              <button type="button" class="v20-close" onclick="closeExecutorApplicationV20()"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="v20-progress-meta"><span id="v20StepLabel">Шаг 1 из 6</span><em>${settings?.executor_onboarding_complete ? 'Редактирование профиля' : '≈ 3–5 минут'}</em></div>
            <div class="v20-progress"><span id="v20ProgressFill"></span></div>
            <div id="v20ExecutorBody" class="v20-body"></div>
            <div class="v20-footer">
              <button id="v20Prev" class="v20-btn ghost" type="button" onclick="v20PrevStep()"><i class="fa-solid fa-arrow-left"></i> Назад</button>
              <button id="v20Next" class="v20-btn gold" type="button" onclick="v20NextStep()">Продолжить <i class="fa-solid fa-arrow-right"></i></button>
            </div>
          </div>`;
        document.body.append(overlay);
        document.body.classList.add('v20-lock');
        render();
      } catch (e) {
        toast(e?.message || 'Не удалось открыть анкету');
      }
    };

    window.openExecutorProfileSettingsV14 = window.openExecutorOnboardingV19;
  }

  wait();
})();