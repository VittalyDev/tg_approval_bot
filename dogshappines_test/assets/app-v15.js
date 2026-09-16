(() => {
  'use strict';

  const wait = (tries = 200) => {
    if (window.V14 && window.api && window.showView && window.openBooking && window.loadExecutorSchedule) return boot();
    if (tries <= 0) return console.error('v15: runtime not ready');
    setTimeout(() => wait(tries - 1), 50);
  };

  function boot() {
    const q = id => document.getElementById(id);
    const safe = v => window.esc ? esc(v ?? '') : String(v ?? '');
    const note = t => window.toast ? toast(t) : alert(t);
    const pad = n => String(n).padStart(2, '0');
    const iso = d => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
    const today = () => iso(new Date());
    const fmtDate = s => {
      const d = new Date(`${s}T12:00:00`);
      return Number.isNaN(d.getTime()) ? s : new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'long',year:'numeric'}).format(d);
    };
    const fmtDuration = min => {
      min = Number(min || 0);
      if (min === 1440) return '1 сутки';
      if (min === 2880) return '2 суток';
      if (min === 90) return '1 ч 30 мин';
      if (min >= 60 && min % 60 === 0) return `${min/60} ч`;
      return `${min} мин`;
    };
    const statusText = s => ({
      open:'Ожидает подтверждения',accepted:'Подтверждён',in_progress:'В процессе',
      done:'Завершён',cancelled:'Отменён',declined:'Отклонён'
    }[s] || s);
    const avatar = src => /^https?:|^\/uploads\//i.test(src || '') ? src : `/assets/${src || 'service-walk.webp'}`;
    const DURS = {
      1:[[30,'30 мин'],[60,'1 час'],[90,'1,5 часа']],
      2:[[720,'12 часов'],[1440,'1 сутки'],[2880,'2 суток']],
      3:[[30,'30 мин'],[60,'1 час'],[120,'2 часа']],
      4:[[60,'1 час'],[90,'1,5 часа']],
      5:[[30,'30 мин'],[60,'1 час']],
      6:[[60,'1 час'],[120,'2 часа']],
      7:[[30,'30 мин'],[60,'1 час']],
      8:[[30,'30 мин'],[60,'1 час'],[120,'2 часа']]
    };

    window.V15 = {
      pets: [],
      bookingSlots: [],
      editOrder: null,
      execCal: {orders:[],blocks:[]},
      execCalMonth: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
      execCalDay: today()
    };

    function closeSheet() { q('v15Sheet')?.remove(); }
    window.closeV15Sheet = closeSheet;

    function sheet(title, body, actions='') {
      closeSheet();
      const d = document.createElement('div');
      d.id = 'v15Sheet';
      d.className = 'v14-sheet-backdrop';
      d.onclick = e => { if (e.target === d) closeSheet(); };
      d.innerHTML = `<div class="v14-sheet v15-sheet" onclick="event.stopPropagation()">
        <div class="v14-sheet-handle"></div>
        <div class="v14-sheet-head"><h2>${safe(title)}</h2><button onclick="closeV15Sheet()"><i class="fa-solid fa-xmark"></i></button></div>
        <div class="v14-sheet-body">${body}</div>
        ${actions ? `<div class="v14-sheet-actions">${actions}</div>` : ''}
      </div>`;
      document.body.append(d);
    }

    async function syncPets() {
      V15.pets = await api('/api/pets');
      return V15.pets;
    }

    function applyPetToBooking(p) {
      if (!p) return;
      V14.bookingPetId = Number(p.id);
      bookingPet = p.name;
      const name = q('bookingPetName');
      if (name) name.textContent = p.name;
      const img = document.querySelector('#view-booking .pet-pick img');
      if (img) img.src = avatar(p.photo_url || '/assets/service-walk.webp');
    }

    const baseLoadPets = window.loadPets;
    window.loadPets = async () => {
      const r = await baseLoadPets();
      try { await syncPets(); } catch (_) {}
      return r;
    };

    window.selectPetV14 = async (id, name) => {
      if (!V15.pets.length) await syncPets();
      const p = V15.pets.find(x => Number(x.id) === Number(id)) || {id, name, photo_url:''};
      applyPetToBooking(p);
      if (returnFromPets === 'booking') showView('booking');
      else note('Питомец выбран');
    };

    function currentSlotIsPast(date, time) {
      if (date !== today()) return false;
      const [h,m] = String(time).split(':').map(Number);
      const d = new Date();
      d.setHours(h || 0, m || 0, 0, 0);
      return d.getTime() < Date.now() + 5 * 60 * 1000;
    }

    async function fetchSlots(executorId, date, duration, excludeOrderId=0) {
      if (!executorId || !date) return [];
      const r = await api(`/api/executors/${Number(executorId)}/slots?date=${encodeURIComponent(date)}&duration=${Number(duration)||60}${excludeOrderId?`&exclude_order_id=${Number(excludeOrderId)}`:''}`);
      return r.slots || [];
    }

    async function refreshBookingSlots() {
      const host = q('v15BookingSlots');
      const input = q('bookTime');
      const date = q('bookDate')?.value;
      if (!host || !input || !date) return;
      host.innerHTML = '<span class="v15-slots-loading">Проверяем расписание…</span>';
      try {
        let slots = await fetchSlots(Number(selectedSitter), date, Number(bookingDuration));
        slots = slots.map(s => ({...s, available:s.available && !currentSlotIsPast(date,s.time)}));
        V15.bookingSlots = slots;
        let chosen = input.value;
        if (!slots.some(s => s.time === chosen && s.available)) chosen = slots.find(s => s.available)?.time || '';
        input.value = chosen;
        host.innerHTML = slots.map(s => `<button type="button" class="v15-slot ${s.time===chosen?'active':''}" ${s.available?'':`disabled title="${safe(s.reason||'Недоступно')}"`} onclick="selectBookingSlotV15('${s.time}',this)"><b>${s.time}</b>${s.available?'':'<small>занято</small>'}</button>`).join('') || '<div class="v15-no-slots">На этот день свободного времени нет</div>';
      } catch (e) {
        host.innerHTML = `<div class="v15-no-slots">${safe(e.message)}</div>`;
      }
    }
    window.refreshBookingSlotsV15 = refreshBookingSlots;
    window.selectBookingSlotV15 = (time, btn) => {
      q('bookTime').value = time;
      q('v15BookingSlots')?.querySelectorAll('.v15-slot').forEach(x => x.classList.remove('active'));
      btn?.classList.add('active');
    };

    function installBookingSlotPicker() {
      const input = q('bookTime');
      const date = q('bookDate');
      if (!input || !date) return;
      input.classList.add('v15-hidden-time');
      let host = q('v15BookingSlots');
      if (!host) {
        host = document.createElement('div');
        host.id = 'v15BookingSlots';
        host.className = 'v15-slot-grid';
        input.insertAdjacentElement('afterend', host);
      }
      if (!date.dataset.v15Slots) {
        date.dataset.v15Slots = '1';
        date.addEventListener('change', refreshBookingSlots);
      }
      const durations = q('durationChoices');
      if (durations && !durations.dataset.v15Slots) {
        durations.dataset.v15Slots = '1';
        durations.addEventListener('click', () => setTimeout(refreshBookingSlots, 20));
      }
      refreshBookingSlots();
    }

    const baseOpenBooking = window.openBooking;
    window.openBooking = async (...args) => {
      await baseOpenBooking(...args);
      try {
        await syncPets();
        const p = V15.pets.find(x => Number(x.id) === Number(V14.bookingPetId)) || V15.pets[0];
        if (p) applyPetToBooking(p);
      } catch (_) {}
      installBookingSlotPicker();
    };

    function timeline(events) {
      return (events || []).length ? events.map(e => `<div><i></i><span><b>${safe(e.text)}</b><small>${new Date(e.created_at).toLocaleString('ru-RU',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}</small></span></div>`).join('') : '<div class="v14-muted">Событий пока нет</div>';
    }

    window.openOrderDetailsV14 = async id => {
      try {
        const o = await api(`/api/orders/${id}`);
        const canEdit = currentRole === 'client' && ['open','accepted'].includes(o.status);
        sheet(`Заказ №${id}`, `
          <div class="v15-order-pet">
            <img src="${avatar(o.pet_photo_url || '/assets/service-walk.webp')}">
            <div><small>ПИТОМЕЦ</small><b>${safe(o.pet_name || 'Питомец')}</b><span>${safe(o.item_name)}</span></div>
          </div>
          <div class="v14-detail-grid">
            <div><span>Дата</span><b>${fmtDate(o.scheduled_date)}</b></div>
            <div><span>Время</span><b>${safe(o.scheduled_time)} · ${fmtDuration(o.duration_min)}</b></div>
            <div><span>Статус</span><b>${statusText(o.status)}</b></div>
            <div><span>Стоимость</span><b>${Number(o.price||0).toLocaleString('ru-RU')} ₽</b></div>
            ${o.executor_name?`<div class="wide"><span>Исполнитель</span><b>${safe(o.executor_name)}</b></div>`:''}
            ${o.address?`<div class="wide"><span>Адрес</span><b>${safe(o.address)}</b></div>`:''}
            ${o.notes?`<div class="wide"><span>Комментарий</span><b>${safe(o.notes)}</b></div>`:''}
          </div>
          <div class="v14-timeline">${timeline(o.events)}</div>`,
          `${canEdit?`<button class="btn btn-gold" onclick="openEditOrderV15(${id})"><i class="fa-solid fa-pen"></i> Изменить заказ</button>`:''}
           ${!['cancelled','declined'].includes(o.status)?`<button class="btn btn-dark" onclick="closeV15Sheet();openOrderChatV14(${id})">Открыть чат</button>`:''}
           ${o.report_ready?`<button class="btn btn-dark" onclick="closeV15Sheet();openReportV14(${id})">Фотоотчёт</button>`:''}`
        );
      } catch (e) { note(e.message); }
    };

    function editDurationOptions(itemId, current) {
      const opts = DURS[Number(itemId)] || [[60,'1 час']];
      return opts.map(([v,l]) => `<option value="${v}" ${Number(v)===Number(current)?'selected':''}>${safe(l)}</option>`).join('');
    }

    async function refreshEditSlotsV15() {
      const o = V15.editOrder, host = q('v15EditSlots'), input = q('v15EditTime');
      if (!o || !host || !input) return;
      const date = q('v15EditDate')?.value;
      const duration = Number(q('v15EditDuration')?.value || o.duration_min || 60);
      const executor = Number(o.executor_id || o.target_executor_id || 0);
      if (!executor) {
        host.innerHTML = '<input id="v15EditNativeTime" class="field" type="time" value="'+safe(input.value)+'" onchange="document.getElementById(\'v15EditTime\').value=this.value">';
        return;
      }
      host.innerHTML = '<span class="v15-slots-loading">Проверяем расписание…</span>';
      try {
        let slots = await fetchSlots(executor, date, duration, o.id);
        slots = slots.map(s => ({...s, available:s.available && !currentSlotIsPast(date,s.time)}));
        let chosen = input.value;
        if (!slots.some(s => s.time===chosen && s.available)) chosen = slots.find(s=>s.available)?.time || '';
        input.value = chosen;
        host.innerHTML = slots.map(s => `<button type="button" class="v15-slot ${s.time===chosen?'active':''}" ${s.available?'':'disabled'} onclick="selectEditSlotV15('${s.time}',this)"><b>${s.time}</b>${s.available?'':'<small>занято</small>'}</button>`).join('') || '<div class="v15-no-slots">Нет свободного времени</div>';
      } catch (e) { host.innerHTML = `<div class="v15-no-slots">${safe(e.message)}</div>`; }
    }
    window.refreshEditSlotsV15 = refreshEditSlotsV15;
    window.selectEditSlotV15 = (time, btn) => {
      q('v15EditTime').value = time;
      q('v15EditSlots')?.querySelectorAll('.v15-slot').forEach(x=>x.classList.remove('active'));
      btn?.classList.add('active');
    };

    window.openEditOrderV15 = async id => {
      try {
        const [o,pets] = await Promise.all([api(`/api/orders/${id}`), syncPets()]);
        V15.editOrder = o;
        const selectedPet = pets.find(p=>Number(p.id)===Number(o.pet_id)) || pets[0];
        sheet('Изменить заказ', `
          <div class="v15-edit-form">
            <label>Дата<input id="v15EditDate" class="field" type="date" min="${today()}" value="${safe(o.scheduled_date)}" onchange="refreshEditSlotsV15()"></label>
            <label>Длительность<select id="v15EditDuration" class="field" onchange="refreshEditSlotsV15()">${editDurationOptions(o.item_id,o.duration_min)}</select></label>
            <label>Время<input id="v15EditTime" type="hidden" value="${safe(o.scheduled_time)}"><div id="v15EditSlots" class="v15-slot-grid"></div></label>
            <label>Питомец
              <div class="v15-edit-pet"><img id="v15EditPetImg" src="${avatar(selectedPet?.photo_url || o.pet_photo_url || '/assets/service-walk.webp')}">
              <select id="v15EditPet" class="field" onchange="updateEditPetPreviewV15()">${pets.map(p=>`<option value="${p.id}" ${Number(p.id)===Number(o.pet_id)?'selected':''}>${safe(p.name)} · ${safe(p.breed||'')}</option>`).join('')}</select></div>
            </label>
            <label>Адрес<input id="v15EditAddress" class="field" value="${safe(o.address||'')}"></label>
            <label>Комментарий<textarea id="v15EditNotes" class="field textarea">${safe(o.notes||'')}</textarea></label>
            ${o.status==='accepted'?'<div class="v15-reconfirm-note"><i class="fa-solid fa-circle-info"></i> Если поменять дату, время или длительность, исполнитель подтвердит заказ заново.</div>':''}
          </div>`,
          `<button class="btn btn-dark" onclick="openOrderDetailsV14(${id})">Назад</button><button class="btn btn-gold" onclick="saveOrderEditV15(${id})">Сохранить</button>`
        );
        refreshEditSlotsV15();
      } catch (e) { note(e.message); }
    };
    window.updateEditPetPreviewV15 = () => {
      const p = V15.pets.find(x=>Number(x.id)===Number(q('v15EditPet')?.value));
      if (p && q('v15EditPetImg')) q('v15EditPetImg').src = avatar(p.photo_url || '/assets/service-walk.webp');
    };
    window.saveOrderEditV15 = async id => {
      const time = q('v15EditTime')?.value;
      if (!time) return note('Выберите свободное время');
      try {
        const r = await api(`/api/orders/${id}/edit`, {method:'POST',body:JSON.stringify({
          scheduled_date:q('v15EditDate')?.value,
          scheduled_time:time,
          duration_min:Number(q('v15EditDuration')?.value||60),
          pet_id:Number(q('v15EditPet')?.value),
          address:q('v15EditAddress')?.value||'',
          notes:q('v15EditNotes')?.value||''
        })});
        note(r.requires_reconfirm ? 'Изменения сохранены. Исполнитель подтвердит новое время.' : 'Заказ обновлён');
        if (window.loadOrders) await loadOrders();
        await openOrderDetailsV14(id);
      } catch (e) { note(e.message); }
    };

    function injectExecutorCalendar() {
      if (q('view-executor-calendar')) return;
      const section = document.createElement('section');
      section.id = 'view-executor-calendar';
      section.className = 'view hidden';
      section.innerHTML = `
        <div class="screen-head"><button class="back" onclick="showView('executor-schedule')"><i class="fa-solid fa-chevron-left"></i></button><h1>Календарь</h1></div>
        <div class="calendar-shell">
          <div class="calendar-head"><button onclick="shiftExecutorMonthV15(-1)"><i class="fa-solid fa-chevron-left"></i></button><b id="v15ExecCalMonth"></b><button onclick="shiftExecutorMonthV15(1)"><i class="fa-solid fa-chevron-right"></i></button></div>
          <div class="calendar-week"><span>Пн</span><span>Вт</span><span>Ср</span><span>Чт</span><span>Пт</span><span>Сб</span><span>Вс</span></div>
          <div id="v15ExecCalGrid" class="calendar-grid"></div>
        </div>
        <div class="v15-exec-cal-head"><b id="v15ExecCalDayTitle"></b><button onclick="openAvailabilitySheetV14()"><i class="fa-solid fa-plus"></i> Закрыть время</button></div>
        <div id="v15ExecCalItems" class="list"></div>`;
      q('app')?.append(section);
    }

    function blockTouchesDay(block, key) {
      const dayStart = new Date(`${key}T00:00:00`);
      const dayEnd = new Date(`${key}T23:59:59`);
      const a = new Date(block.start_at), b = new Date(block.end_at);
      return a <= dayEnd && b >= dayStart;
    }

    function renderExecutorCalendar() {
      const m=V15.execCalMonth, year=m.getFullYear(), month=m.getMonth();
      const first=new Date(year,month,1), start=(first.getDay()+6)%7, days=new Date(year,month+1,0).getDate();
      const title=q('v15ExecCalMonth');
      if(title)title.textContent=new Intl.DateTimeFormat('ru-RU',{month:'long',year:'numeric'}).format(first);
      const cells=[];
      for(let i=0;i<start;i++)cells.push('<span class="v14-cal-empty"></span>');
      for(let d=1;d<=days;d++){
        const key=`${year}-${pad(month+1)}-${pad(d)}`;
        const orders=(V15.execCal.orders||[]).filter(o=>o.scheduled_date===key);
        const blocks=(V15.execCal.blocks||[]).filter(b=>blockTouchesDay(b,key));
        cells.push(`<button class="v14-cal-day ${key===today()?'today':''} ${key===V15.execCalDay?'selected':''} ${orders.length||blocks.length?'has':''}" onclick="selectExecutorDayV15('${key}')"><span>${d}</span><em>${orders.slice(0,2).map(o=>`<i class="${o.status==='done'?'done':o.status==='in_progress'?'progress':o.status==='accepted'?'accepted':'open'}"></i>`).join('')}${blocks.length?'<i class="v15-block-dot"></i>':''}</em></button>`);
      }
      q('v15ExecCalGrid').innerHTML=cells.join('');
      renderExecutorDay();
    }

    function renderExecutorDay() {
      const key=V15.execCalDay, host=q('v15ExecCalItems');
      if(q('v15ExecCalDayTitle'))q('v15ExecCalDayTitle').textContent=fmtDate(key);
      const rows=(V15.execCal.orders||[]).filter(o=>o.scheduled_date===key).sort((a,b)=>(a.scheduled_time||'').localeCompare(b.scheduled_time||''));
      const blocks=(V15.execCal.blocks||[]).filter(b=>blockTouchesDay(b,key));
      const html=[];
      rows.forEach(o=>html.push(`<button class="v15-exec-cal-order" onclick="openOrderDetailsV14(${o.id})"><time>${safe(o.scheduled_time)}</time><span><b>${safe(o.item_name)}</b><small>${safe(o.pet_name||'Питомец')} · ${fmtDuration(o.duration_min)}</small></span><em>${statusText(o.status)}</em></button>`));
      blocks.forEach(b=>html.push(`<div class="v15-exec-cal-block"><i class="fa-solid fa-lock"></i><span><b>Недоступное время</b><small>${new Date(b.start_at).toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'})}–${new Date(b.end_at).toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'})}${b.note?` · ${safe(b.note)}`:''}</small></span><button onclick="deleteAvailabilityV14(${b.id})"><i class="fa-solid fa-xmark"></i></button></div>`));
      host.innerHTML=html.join('')||'<div class="v14-empty compact"><i class="fa-regular fa-calendar-check"></i><b>День свободен</b><span>Заявок и закрытого времени нет.</span></div>';
    }

    window.loadExecutorCalendarV15=async()=>{
      V15.execCal=await api('/api/calendar?role=executor');
      renderExecutorCalendar();
    };
    window.selectExecutorDayV15=key=>{V15.execCalDay=key;renderExecutorCalendar()};
    window.shiftExecutorMonthV15=delta=>{V15.execCalMonth=new Date(V15.execCalMonth.getFullYear(),V15.execCalMonth.getMonth()+delta,1);renderExecutorCalendar()};
    window.openExecutorCalendarV15=async()=>{injectExecutorCalendar();await showView('executor-calendar');await loadExecutorCalendarV15()};

    injectExecutorCalendar();

    const baseSchedule=window.loadExecutorSchedule;
    window.loadExecutorSchedule=async()=>{
      await baseSchedule();
      const toolbar=q('executorSchedule')?.querySelector('.v14-schedule-toolbar');
      if(toolbar && !toolbar.querySelector('.v15-schedule-actions')){
        const old=toolbar.querySelector('button');
        const actions=document.createElement('div');
        actions.className='v15-schedule-actions';
        actions.innerHTML=`<button class="btn btn-dark" onclick="openExecutorCalendarV15()"><i class="fa-regular fa-calendar-days"></i> Календарь</button><button class="btn btn-gold" onclick="openAvailabilitySheetV14()"><i class="fa-solid fa-plus"></i> Закрыть время</button>`;
        old?.remove();
        toolbar.append(actions);
      }
    };

    const baseShow=window.showView;
    window.showView=async v=>{
      const r=await baseShow(v);
      if(v==='executor-calendar')await loadExecutorCalendarV15();
      return r;
    };

    const baseDelete=window.deleteAvailabilityV14;
    if(baseDelete){
      window.deleteAvailabilityV14=async id=>{
        await baseDelete(id);
        if(!q('view-executor-calendar')?.classList.contains('hidden'))await loadExecutorCalendarV15();
      };
    }

    syncPets().catch(()=>{});
  }

  wait();
})();