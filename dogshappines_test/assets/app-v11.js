/* Dog's Happiness v11 product-logic patch */
(() => {
  'use strict';

  const RUS_CITIES = ['Москва','Санкт-Петербург','Казань','Екатеринбург','Новосибирск','Сочи','Нижний Новгород','Краснодар'];
  const CITY_AREAS = {
    'Москва':['Хамовники','Пресненский','Арбат','Тверской'],
    'Санкт-Петербург':['Петроградский','Центральный','Василеостровский','Московский'],
    'Казань':['Вахитовский','Ново-Савиновский','Советский','Приволжский'],
    'Екатеринбург':['Центр','Втузгородок','Юго-Западный','Ботанический'],
    'Новосибирск':['Центральный','Заельцовский','Октябрьский','Ленинский'],
    'Сочи':['Центральный','Хоста','Адлер','Светлана'],
    'Нижний Новгород':['Нижегородский','Советский','Приокский','Канавинский'],
    'Краснодар':['Центральный','Фестивальный','Юбилейный','Черёмушки']
  };
  const serviceIcons = {1:'fa-person-walking',2:'fa-house',3:'fa-user',4:'fa-dog',5:'fa-stethoscope',6:'fa-scissors',7:'fa-house-circle-check',8:'fa-car-side'};
  const old = {
    showView: window.showView,
    loadClientHome: window.loadClientHome,
    openBooking: window.openBooking,
    selectDuration: window.selectDuration,
    submitBooking: window.submitBooking,
    loadOrders: window.loadOrders,
    loadExecutor: window.loadExecutor,
    cancelOrder: window.cancelOrder,
    loadLeaderboard: window.loadLeaderboard,
    openSettings: window.openSettings
  };
  let execFilter = 'all';
  let selectedCalendarDay = '';
  let orderCacheV11 = [];

  function city(){ const c=localStorage.getItem('dh_city_v9')||'Москва'; return RUS_CITIES.includes(c)?c:'Москва'; }
  function areaFor(s, i=0){ const a=CITY_AREAS[city()]||CITY_AREAS['Москва']; return a[(Number(s?.id||i)+i)%a.length]; }
  function icon(id){ return serviceIcons[Number(id)]||'fa-paw'; }
  function pad(n){ return String(n).padStart(2,'0'); }
  function localISO(d=new Date()){ return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`; }
  function parseLocal(date,time='00:00'){ const d=new Date(`${date}T${time}:00`); return Number.isNaN(d.getTime())?null:d; }
  function fmtDay(date){ const d=parseLocal(date,'12:00'); return d?new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'long'}).format(d):date; }
  function fmtShort(date){ const d=parseLocal(date,'12:00'); return d?new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'short'}).format(d).replace('.',''):date; }
  function statusClass(s){ return s==='done'?'done':s==='in_progress'?'progress':s==='accepted'?'accepted':s==='cancelled'?'cancelled':'open'; }
  function currentSitterForOrder(o){
    try{
      const map=JSON.parse(localStorage.getItem('dh_order_sitters_v9')||'{}');
      return sitters.find(x=>Number(x.id)===Number(map[o.id]))||null;
    }catch(_){ return null; }
  }
  function serviceById(id){ return (catalogCache||[]).find(x=>Number(x.id)===Number(id)); }
  function safeText(v){ return esc(v==null?'':v); }
  function removeSheet(){ document.getElementById('v11Sheet')?.remove(); }
  function sheet(title, body, actions=''){
    removeSheet();
    const d=document.createElement('div');
    d.id='v11Sheet'; d.className='v11-backdrop';
    d.onclick=e=>{ if(e.target===d)removeSheet(); };
    d.innerHTML=`<div class="v11-sheet"><div class="v11-handle"></div><div class="v11-sheet-head"><h2>${safeText(title)}</h2><button onclick="document.getElementById('v11Sheet')?.remove()"><i class="fa-solid fa-xmark"></i></button></div><div class="v11-sheet-body">${body}</div>${actions?`<div class="v11-sheet-actions">${actions}</div>`:''}</div>`;
    document.body.append(d);
  }
  function relativeDay(iso){
    const target=parseLocal(iso,'12:00'); if(!target)return '';
    const now=new Date(); now.setHours(12,0,0,0);
    const diff=Math.round((target-now)/86400000);
    if(diff===0)return 'Сегодня'; if(diff===1)return 'Завтра'; if(diff===-1)return 'Вчера';
    return fmtDay(iso);
  }
  function injectGlobal(){
    document.body.classList.add('v11');
    const hero=document.querySelector('#view-client-home .hero-copy');
    if(hero && !document.getElementById('v11HeroTrust')){
      const trust=document.createElement('div'); trust.id='v11HeroTrust'; trust.className='v11-hero-trust';
      trust.innerHTML='<span><i class="fa-solid fa-shield-halved"></i> Проверка исполнителей</span><span><i class="fa-solid fa-camera"></i> Отчёт после услуги</span>';
      hero.append(trust);
    }
    const addr=document.getElementById('bookAddress');
    if(addr && /Корзо|Суботиц|Арбат/i.test(addr.value||'')) addr.value='ул. Тверская, 12';
  }

  async function renderNextOrder(){
    const sub=document.getElementById('subscriptionCard'); if(!sub)return;
    let host=document.getElementById('v11NextOrder');
    if(!host){ host=document.createElement('div');host.id='v11NextOrder';sub.insertAdjacentElement('beforebegin',host); }
    let all=[];
    try{ all=await api('/api/orders'); }catch(_){ return; }
    const now=new Date();
    const future=all.filter(o=>!['done','cancelled'].includes(o.status)).map(o=>({...o,_d:parseLocal(o.scheduled_date,o.scheduled_time)})).filter(o=>o._d && o._d.getTime()>now.getTime()-1800000).sort((a,b)=>a._d-b._d);
    const o=future[0];
    if(!o){ host.innerHTML='';host.classList.add('hidden');return; }
    host.classList.remove('hidden');
    const sitter=currentSitterForOrder(o);
    host.innerHTML=`<div class="v11-section-head"><div><small>БЛИЖАЙШАЯ УСЛУГА</small><b>${relativeDay(o.scheduled_date)}, ${safeText(o.scheduled_time)}</b></div><span class="v11-status ${statusClass(o.status)}">${statusText(o.status)}</span></div>
      <div class="v11-next-card">
        <div class="v11-next-icon"><i class="fa-solid ${icon(o.item_id)}"></i></div>
        <div class="v11-next-main"><b>${safeText(o.item_name)}</b><small>${safeText(o.pet_name||'Питомец')} · ${o.duration_min||60} мин${sitter?` · ${safeText(sitter.name)}`:''}</small><span><i class="fa-solid fa-location-dot"></i> ${safeText((o.address||'').replace(/Москва|Арбат/gi,'Москва'))}</span></div>
        <button class="v11-round" onclick="showView('orders')"><i class="fa-solid fa-chevron-right"></i></button>
      </div>
      <div class="v11-next-actions"><button onclick="showView('chat')"><i class="fa-regular fa-message"></i> Чат</button><button onclick="showView('orders')"><i class="fa-regular fa-rectangle-list"></i> Детали</button></div>`;
  }

  function injectBooking(){
    const view=document.getElementById('view-booking'); if(!view)return;
    const submit=document.getElementById('bookingSubmit');
    if(submit && !document.getElementById('v11BookingSummary')){
      const box=document.createElement('div'); box.id='v11BookingSummary'; box.className='v11-booking-summary';
      submit.insertAdjacentElement('beforebegin',box);
    }
    const date=document.getElementById('bookDate');
    if(date){ date.min=localISO(); }
    ['bookDate','bookTime','bookAddress','bookNotes'].forEach(id=>{
      const el=document.getElementById(id); if(el && !el.dataset.v11){ el.dataset.v11='1'; el.addEventListener('input',updateBookingSummary); el.addEventListener('change',updateBookingSummary); }
    });
    updateBookingSummary();
  }
  async function updateBookingSummary(){
    const box=document.getElementById('v11BookingSummary'); if(!box)return;
    const item=serviceById(selectedService) || (await ensureCatalog()).find(x=>Number(x.id)===Number(selectedService));
    const sitter=sitters.find(x=>Number(x.id)===Number(selectedSitter));
    const date=document.getElementById('bookDate')?.value||'';
    const time=document.getElementById('bookTime')?.value||'';
    const address=(document.getElementById('bookAddress')?.value||'').trim();
    const valid=date && time && address.length>=5;
    const submit=document.getElementById('bookingSubmit');
    if(submit){ submit.disabled=!valid; submit.classList.toggle('is-disabled',!valid); }
    box.innerHTML=`<div class="v11-summary-row"><span>Исполнитель</span><b>${safeText(sitter?.name||'Будет подобран')}</b></div>
      <div class="v11-summary-row"><span>Дата и время</span><b>${date?fmtShort(date):'Выберите дату'}${time?` · ${safeText(time)}`:''}</b></div>
      <div class="v11-summary-row"><span>Питомец</span><b>${safeText(bookingPet||'Не выбран')}</b></div>
      <div class="v11-summary-row"><span>Стоимость</span><b class="gold">от ${Number(item?.price||0).toLocaleString('ru-RU')} ₽</b></div>
      <small class="v11-summary-note"><i class="fa-solid fa-circle-info"></i> Финальная стоимость зависит от длительности и дополнительных пожеланий.</small>`;
  }

  window.openBooking=async function(serviceId,sitterId){ await old.openBooking(serviceId,sitterId); injectBooking(); };
  window.selectDuration=function(btn){ old.selectDuration(btn); updateBookingSummary(); };
  window.submitBooking=function(){
    const date=document.getElementById('bookDate')?.value;
    const time=document.getElementById('bookTime')?.value;
    const address=(document.getElementById('bookAddress')?.value||'').trim();
    if(!date||!time)return toast('Выберите дату и время');
    const dt=parseLocal(date,time);
    if(!dt || dt.getTime()<Date.now()+10*60000)return toast('Выберите время хотя бы на 10 минут позже');
    if(address.length<5)return toast('Укажите адрес');
    const item=serviceById(selectedService);
    const sitter=sitters.find(x=>Number(x.id)===Number(selectedSitter));
    sheet('Проверьте заказ',
      `<div class="v11-confirm-service"><i class="fa-solid ${icon(selectedService)}"></i><div><b>${safeText(item?.name||'Услуга')}</b><small>${safeText(sitter?.name||'Исполнитель')} · ${safeText(bookingPet||'Питомец')}</small></div></div>
       <div class="v11-confirm-grid"><div><span>Когда</span><b>${fmtDay(date)} · ${safeText(time)}</b></div><div><span>Длительность</span><b>${bookingDuration} мин</b></div><div class="wide"><span>Адрес</span><b>${safeText(address)}</b></div></div>`,
      `<button class="btn btn-dark" onclick="document.getElementById('v11Sheet')?.remove()">Изменить</button><button class="btn btn-gold" onclick="confirmBookingV11()">Подтвердить</button>`);
  };
  window.confirmBookingV11=async function(){
    removeSheet();
    await old.submitBooking();
  };

  function renderOrderCard(o){
    const sitter=currentSitterForOrder(o);
    const steps=['open','accepted','in_progress','done'];
    const idx=Math.max(0,steps.indexOf(o.status));
    return `<article class="v11-order-card ${statusClass(o.status)}">
      <div class="v11-order-top"><div class="v11-order-icon"><i class="fa-solid ${icon(o.item_id)}"></i></div><div><small>${fmtShort(o.scheduled_date)} · ${safeText(o.scheduled_time||'')}</small><h3>${safeText(o.item_name)}</h3></div><span class="v11-status ${statusClass(o.status)}">${statusText(o.status)}</span></div>
      <div class="v11-order-info"><span><i class="fa-solid fa-paw"></i>${safeText(o.pet_name||'Питомец')}</span><span><i class="fa-regular fa-clock"></i>${o.duration_min||60} мин</span>${sitter?`<span><i class="fa-regular fa-user"></i>${safeText(sitter.name)}</span>`:''}</div>
      ${!['cancelled'].includes(o.status)?`<div class="v11-progress">${steps.map((s,i)=>`<i class="${i<=idx?'on':''}"></i>`).join('')}</div>`:''}
      <div class="v11-order-actions"><button onclick="openOrderDetailsV11(${o.id})">Подробнее</button>${o.status==='done'?`<button onclick="showView('report')">Фотоотчёт</button>`:`<button onclick="showView('chat')">Чат</button>`}${!['done','cancelled','in_progress'].includes(o.status)?`<button class="danger" onclick="cancelOrder(${o.id})">Отменить</button>`:''}</div>
    </article>`;
  }
  window.loadOrders=async function(){
    const all=await api('/api/orders'); orderCacheV11=all;
    const rows=orderTab==='current'?all.filter(o=>!['done','cancelled'].includes(o.status)):orderTab==='history'?all.filter(o=>o.status==='done'):all.filter(o=>o.status==='cancelled');
    const el=document.getElementById('ordersList'); if(!el)return;
    el.innerHTML=rows.length?rows.map(renderOrderCard).join(''):`<div class="v11-empty"><i class="fa-regular fa-calendar-check"></i><b>Здесь пока пусто</b><span>${orderTab==='current'?'Выберите услугу и создайте первый заказ.':'История появится после завершённых услуг.'}</span>${orderTab==='current'?'<button class="btn btn-gold" onclick="showView(\'services\')">Выбрать услугу</button>':''}</div>`;
  };
  window.openOrderDetailsV11=function(id){
    const o=orderCacheV11.find(x=>Number(x.id)===Number(id)); if(!o)return;
    const sitter=currentSitterForOrder(o);
    sheet(`Заказ №${o.id}`,
      `<div class="v11-detail-hero"><div class="v11-order-icon"><i class="fa-solid ${icon(o.item_id)}"></i></div><div><b>${safeText(o.item_name)}</b><span class="v11-status ${statusClass(o.status)}">${statusText(o.status)}</span></div></div>
       <div class="v11-detail-list"><div><span>Дата</span><b>${fmtDay(o.scheduled_date)} · ${safeText(o.scheduled_time||'')}</b></div><div><span>Питомец</span><b>${safeText(o.pet_name||'')}</b></div><div><span>Длительность</span><b>${o.duration_min||60} минут</b></div><div><span>Адрес</span><b>${safeText(o.address||'')}</b></div>${sitter?`<div><span>Исполнитель</span><b>${safeText(sitter.name)} · ${sitter.rating}</b></div>`:''}${o.notes?`<div><span>Комментарий</span><b>${safeText(o.notes)}</b></div>`:''}</div>`,
      `<button class="btn btn-dark" onclick="document.getElementById('v11Sheet')?.remove();showView('chat')">Написать</button><button class="btn btn-gold" onclick="document.getElementById('v11Sheet')?.remove()">Готово</button>`);
  };
  window.cancelOrder=function(id){
    sheet('Отменить заказ?','<p class="v11-sheet-text">Исполнитель получит уведомление. Если услуга уже скоро, оператор может связаться с вами для уточнения.</p>',
      `<button class="btn btn-dark" onclick="document.getElementById('v11Sheet')?.remove()">Оставить</button><button class="btn btn-danger" onclick="cancelOrderNowV11(${Number(id)})">Отменить заказ</button>`);
  };
  window.cancelOrderNowV11=async function(id){ removeSheet(); await old.cancelOrder(id); };

  function execMatches(o){
    if(execFilter==='today')return o.scheduled_date===localISO();
    if(execFilter==='tomorrow'){ const d=new Date();d.setDate(d.getDate()+1);return o.scheduled_date===localISO(d); }
    if(execFilter==='walk')return Number(o.item_id)===1;
    if(execFilter==='care')return [2,3,7].includes(Number(o.item_id));
    return true;
  }
  function injectExecFilters(){
    const list=document.getElementById('executorList'); if(!list)return;
    let box=document.getElementById('v11ExecFilters');
    if(!box){box=document.createElement('div');box.id='v11ExecFilters';box.className='v11-filter-row';list.insertAdjacentElement('beforebegin',box);}
    const options=[['all','Все'],['today','Сегодня'],['tomorrow','Завтра'],['walk','Выгул'],['care','Уход']];
    box.innerHTML=options.map(([k,l])=>`<button class="${execFilter===k?'active':''}" onclick="setExecFilterV11('${k}')">${l}</button>`).join('');
  }
  window.setExecFilterV11=function(v){ execFilter=v; loadExecutor(); };
  window.loadExecutor=async function(){
    injectExecFilters();
    const rows=await api('/api/executor/orders');
    let f=executorTab==='available'?rows.filter(o=>o.status==='open'):rows.filter(o=>o.status!=='open');
    f=f.filter(execMatches).sort((a,b)=>String(a.scheduled_date+a.scheduled_time).localeCompare(String(b.scheduled_date+b.scheduled_time)));
    const el=document.getElementById('executorList'); if(!el)return;
    if(!f.length){ el.innerHTML='<div class="v11-empty"><i class="fa-solid fa-briefcase"></i><b>Подходящих заявок нет</b><span>Попробуйте другой фильтр или зайдите позже.</span></div>';return; }
    let last='';
    el.innerHTML=f.map(o=>{
      const group=relativeDay(o.scheduled_date); const head=group!==last?`<div class="v11-date-group">${safeText(group)}</div>`:''; last=group;
      return `${head}<article class="v11-request">
        <div class="v11-request-top"><div class="v11-request-title"><div class="v11-request-icon"><i class="fa-solid ${icon(o.item_id)}"></i></div><div><h3>${safeText(o.item_name)}</h3><div class="v11-request-time">${safeText(o.scheduled_time||'—')} · ${o.duration_min||60} мин</div></div></div><div class="v11-price">${o.price} ₽</div></div>
        <div class="v11-request-meta"><div><span>Питомец</span><b>${safeText(o.pet_name||'Питомец')}</b></div><div><span>Район</span><b>${safeText((o.address||'Москва').replace(/Москва|Арбат|Арбат/gi,'Москва'))}</b></div></div>
        ${o.notes?`<div class="v11-request-note"><i class="fa-regular fa-note-sticky"></i>${safeText(o.notes)}</div>`:''}
        <div class="v11-request-actions">${o.status==='open'?`<button class="btn btn-gold" onclick="confirmAcceptV11(${o.id})">Взять заявку</button>`:o.status==='accepted'?`<button class="btn btn-gold" onclick="setOrderStatus(${o.id},'in_progress')">Начать услугу</button>`:o.status==='in_progress'?`<button class="btn btn-gold" onclick="setOrderStatus(${o.id},'done')">Завершить</button>`:`<span class="v11-status done">Завершён</span>`}</div>
      </article>`;
    }).join('');
  };
  window.confirmAcceptV11=function(id){
    sheet('Взять заявку?','<p class="v11-sheet-text">Система проверит ваше расписание. После подтверждения заказ появится во вкладке «Мои» и в расписании.</p>',
      `<button class="btn btn-dark" onclick="document.getElementById('v11Sheet')?.remove()">Не сейчас</button><button class="btn btn-gold" onclick="acceptOrderV11(${Number(id)})">Взять</button>`);
  };
  window.acceptOrderV11=async function(id){ removeSheet(); await acceptOrder(id); };

  window.showCalendarDay=function(iso){
    selectedCalendarDay=iso;
    document.querySelectorAll('.calendar-day').forEach(b=>b.classList.toggle('selected',b.dataset.iso===iso));
    const rows=(calendarRows||[]).filter(o=>o.scheduled_date===iso);
    if(!rows.length){ toast('На этот день услуг нет');return; }
    sheet(fmtDay(iso),rows.map(o=>`<div class="v11-day-event"><div class="v11-order-icon"><i class="fa-solid ${icon(o.item_id)}"></i></div><div><b>${safeText(o.scheduled_time)} · ${safeText(o.item_name)}</b><small>${safeText(o.pet_name||'Питомец')} · ${o.duration_min||60} мин</small></div><span class="v11-status ${statusClass(o.status)}">${statusText(o.status)}</span></div>`).join(''));
  };
  const oldRenderCalendar=window.renderCalendar;
  window.renderCalendar=function(){
    const y=calendarDate.getFullYear(),m=calendarDate.getMonth(),first=new Date(y,m,1),days=new Date(y,m+1,0).getDate(),offset=(first.getDay()+6)%7,today=localISO();
    const title=document.getElementById('calendarMonth'); if(title)title.textContent=new Intl.DateTimeFormat('ru-RU',{month:'long',year:'numeric'}).format(calendarDate);
    const grid=document.getElementById('calendarGrid'); if(!grid)return oldRenderCalendar?.();
    let h='';
    for(let i=0;i<offset;i++)h+='<button class="calendar-day empty" disabled></button>';
    for(let d=1;d<=days;d++){
      const iso=`${y}-${pad(m+1)}-${pad(d)}`;
      const count=(calendarRows||[]).filter(o=>o.scheduled_date===iso).length;
      h+=`<button data-iso="${iso}" class="calendar-day ${count?'has-order':''} ${today===iso?'today':''} ${selectedCalendarDay===iso?'selected':''}" onclick="showCalendarDay('${iso}')"><span>${d}</span>${count?`<small>${count}</small>`:''}</button>`;
    }
    grid.innerHTML=h;
  };

  window.loadLeaderboard=async function(){
    const data=await api('/api/leaderboard'),rows=rankTab==='clients'?data.clients:data.executors;
    const opt=document.getElementById('ratingOpt');
    if(opt) opt.innerHTML=rankTab==='clients'?`<label class="v11-rating-opt"><span><b>Участвовать в рейтинге</b><small>Ваше место видят другие заказчики</small></span><input type="checkbox" ${data.rating_opt_in?'checked':''} onchange="toggleRatingOpt(this.checked)"></label>`:`<div class="v11-rating-info"><i class="fa-solid fa-circle-info"></i><span>Рейтинг исполнителей считается по выполненным заявкам и оценкам клиентов.</span></div>`;
    const el=document.getElementById('leaderboardList');if(!el)return;
    el.innerHTML=rows.map((r,i)=>`<div class="v11-leader ${r.me?'me':''}"><div class="v11-place ${i<3?'top':''}">${i+1}</div><div class="v11-avatar">${safeText((r.name||'?').slice(0,1).toUpperCase())}</div><div class="v11-leader-main"><b>${safeText(r.name)}${r.me?' · Вы':''}</b><span><i class="fa-solid fa-star"></i> ${r.rating}</span></div><div class="v11-score"><strong>${r.score}</strong><small>${rankTab==='clients'?'заказов':'выполнено'}</small></div></div>`).join('');
  };

  window.openSettings=function(){
    closeV9Sheet?.(); removeSheet();
    const c=city(),n=localStorage.getItem('dh_notify_v9')!=='0',p=localStorage.getItem('dh_privacy_v9')!=='0',rem=localStorage.getItem('dh_reminders_v11')!=='0';
    sheet('Настройки',`<div class="v11-settings">
      <label class="v11-setting"><span><i class="fa-solid fa-location-dot"></i><span><b>Город</b><small>Исполнители и заявки рядом с вами</small></span></span><select id="v11City">${RUS_CITIES.map(x=>`<option ${x===c?'selected':''}>${x}</option>`).join('')}</select></label>
      <div class="v11-setting"><span><i class="fa-regular fa-bell"></i><span><b>Уведомления</b><small>Изменения заказа и сообщения</small></span></span><button class="v11-switch ${n?'on':''}" onclick="toggleV11Setting('notify',this)"><i></i></button></div>
      <div class="v11-setting"><span><i class="fa-regular fa-clock"></i><span><b>Напоминание за 2 часа</b><small>Перед предстоящей услугой</small></span></span><button class="v11-switch ${rem?'on':''}" onclick="toggleV11Setting('reminders',this)"><i></i></button></div>
      <div class="v11-setting"><span><i class="fa-solid fa-lock"></i><span><b>Приватность</b><small>Контакты скрыты до назначения</small></span></span><button class="v11-switch ${p?'on':''}" onclick="toggleV11Setting('privacy',this)"><i></i></button></div>
      <button class="v11-settings-action" onclick="document.getElementById('v11Sheet')?.remove();changeRole()"><i class="fa-solid fa-repeat"></i><span><b>Сменить роль</b><small>Клиент или исполнитель</small></span><i class="fa-solid fa-chevron-right"></i></button>
      <button class="v11-settings-action" onclick="resetIntroV11()"><i class="fa-regular fa-circle-play"></i><span><b>Показать приветствие</b><small>Открыть стартовый экран заново</small></span><i class="fa-solid fa-chevron-right"></i></button>
    </div>`);
    setTimeout(()=>document.getElementById('v11City')?.addEventListener('change',e=>{
      localStorage.setItem('dh_city_v9',e.target.value); const l=document.getElementById('cityLabel');if(l)l.textContent=e.target.value; toast('Город сохранён');
    }),0);
  };
  window.toggleV11Setting=function(key,btn){
    btn.classList.toggle('on');
    const val=btn.classList.contains('on')?'1':'0';
    localStorage.setItem(key==='notify'?'dh_notify_v9':key==='privacy'?'dh_privacy_v9':'dh_reminders_v11',val);
    haptic?.();
  };
  window.resetIntroV11=function(){ localStorage.removeItem('dh_intro_v9');removeSheet();showView('intro'); };

  const originalShow=window.showView;
  window.showView=async function(v){
    await originalShow(v);
    injectGlobal();
    if(v==='client-home') await renderNextOrder();
    if(v==='booking') injectBooking();
    if(v==='executor-orders') injectExecFilters();
  };
  window.loadClientHome=async function(){ await old.loadClientHome(); injectGlobal(); await renderNextOrder(); };

  function wire(){
    injectGlobal();
    document.addEventListener('keydown',e=>{ if(e.key==='Escape')removeSheet(); });
    const bookingPet=document.getElementById('bookingPetName');
    if(bookingPet){
      const obs=new MutationObserver(()=>updateBookingSummary());
      obs.observe(bookingPet,{childList:true,subtree:true,characterData:true});
    }
    setTimeout(()=>{ if(currentView==='client-home')renderNextOrder(); if(currentView==='booking')injectBooking(); },250);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',wire);else wire();
})();
