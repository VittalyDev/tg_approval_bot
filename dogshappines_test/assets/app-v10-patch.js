/* Dog's Happiness v10 polish patch */
(() => {
  const RUS_CITIES=['Москва','Санкт-Петербург','Казань','Екатеринбург','Новосибирск','Сочи','Нижний Новгород','Краснодар'];
  const HD={
    hero:'https://images.unsplash.com/photo-1690978725637-d216c192c032?auto=format&fit=crop&w=1600&q=86',
    alina:'https://images.unsplash.com/photo-1598262088246-2b1a35324c83?auto=format&fit=crop&w=1200&q=86',
    ekaterina:'https://images.unsplash.com/flagged/photo-1580198702040-6e391d4d46f7?auto=format&fit=crop&w=1200&q=86',
    maria:'https://images.unsplash.com/photo-1621263573762-4d0157542ddc?auto=format&fit=crop&w=1200&q=86',
    marko:'https://images.unsplash.com/photo-1690978725637-d216c192c032?auto=format&fit=crop&w=1200&q=84'
  };
  const oldShowView=window.showView;
  const oldLoadClientHome=window.loadClientHome;
  const oldOpenSitter=window.openSitter;

  function imgSrc(v){return /^https?:\/\//.test(String(v||''))?v:`/assets/${v}`}
  function cleanCity(v){return RUS_CITIES.includes(v)?v:'Москва'}
  function ruAddress(v){
    const s=String(v||'').trim();
    const map={'Центр, Москва':'ЦАО, Москва','Хамовники, Москва':'Хамовники, Москва','Арбат':'Пресненский район, Москва','Ул. Корзо, 12':'ул. Тверская, 12','Ул. Корзо,12':'ул. Тверская, 12','Москва':'Москва','Арбат':'Москва','Санкт-Петербург':'Санкт-Петербург','Казань':'Москва'};
    if(map[s])return map[s];
    return s.replace(/Москва/gi,'Москва').replace(/Арбат/gi,'Москва').replace(/Арбат/gi,'Москва').replace(/Хамовники/gi,'Хамовники').replace(/Корзо/gi,'Тверская');
  }
  function serviceIcon(id){return({1:'fa-person-walking',2:'fa-house',3:'fa-user',4:'fa-dog',5:'fa-stethoscope',6:'fa-scissors',7:'fa-house-circle-check',8:'fa-car-side'})[Number(id)]||'fa-paw'}
  function fmtDate(iso){if(!iso)return '';const d=new Date(`${iso}T12:00:00`);return Number.isNaN(d.getTime())?iso:new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'short'}).format(d).replace('.','')}
  function monthShort(iso){if(!iso)return '';const d=new Date(`${iso}T12:00:00`);return Number.isNaN(d.getTime())?'':new Intl.DateTimeFormat('ru-RU',{month:'short'}).format(d).replace('.','')}

  function migrateRussia(){
    const old=localStorage.getItem('dh_city_v9');
    if(!RUS_CITIES.includes(old||''))localStorage.setItem('dh_city_v9','Москва');
    const city=document.getElementById('cityLabel'); if(city)city.textContent=cleanCity(localStorage.getItem('dh_city_v9'));
    const addr=document.getElementById('bookAddress'); if(addr && (!addr.value || /Корзо|Суботиц|Арбат/i.test(addr.value)))addr.value='ул. Тверская, 12';
  }

  function enhancePeople(){
    try{
      const updates=[
        {area:'ЦАО, Москва',image:HD.alina},
        {area:'Хамовники, Москва',image:HD.ekaterina},
        {area:'Пресненский район, Москва',image:HD.maria},
        {area:'Петроградский район, Санкт-Петербург',image:HD.marko}
      ];
      sitters.forEach((s,i)=>Object.assign(s,updates[i]||{}));
    }catch(_){}
    document.querySelectorAll('#view-intro .intro>img,#view-role .role-screen>img,#view-client-home .hero-photo').forEach(i=>{i.src=HD.hero;i.removeAttribute('srcset')});
    const feat=document.querySelector('#view-client-home .feature-card.wide img'); if(feat)feat.src=HD.alina;
    const exHero=document.querySelector('#view-executor-home .executor-hero>img');if(exHero)exHero.src=HD.alina;
    const exProfile=document.querySelector('#view-executor-profile .executor-profile-cover>img');if(exProfile)exProfile.src=HD.alina;
    document.querySelectorAll('#view-chat .chat-head img').forEach(i=>i.src=HD.alina);
  }

  window.renderHomeSliders=function(items,plans){
    const sub=document.getElementById('subscriptionCard');if(!sub)return;
    let services=document.getElementById('v9-home-services'),tariffs=document.getElementById('v9-home-tariffs');
    if(!services){services=document.createElement('div');services.id='v9-home-services';sub.insertAdjacentElement('afterend',services)}
    services.innerHTML=`<div class="v9-section-title"><b>Услуги</b><button onclick="showView('services')">Смотреть все</button></div><div class="v9-scroll">${items.slice(0,6).map(s=>`<button class="v9-service-card" onclick="openServiceExecutors(${s.id})"><img src="/assets/${s.image}" loading="lazy"><div><b>${esc(s.name)}</b><small>${esc(s.desc)}</small><em>от ${s.price} ₽</em></div></button>`).join('')}</div>`;
    if(!tariffs){tariffs=document.createElement('div');tariffs.id='v9-home-tariffs';services.insertAdjacentElement('afterend',tariffs)}
    tariffs.innerHTML=`<div class="v9-section-title"><b>Абонементы</b><button onclick="showView('tariffs')">Все тарифы</button></div><div class="v10-tariffs-grid">${plans.slice(0,2).map(p=>`<div class="v10-tariff-card ${p.badge?'featured':''}">${p.badge?`<span class="badge">${esc(p.badge)}</span>`:''}<b>${esc(p.name)}</b><strong>${Number(p.price).toLocaleString('ru-RU')} ₽</strong><small>${p.walks} прогулок · месяц</small><button onclick="showView('tariffs')">Подробнее</button></div>`).join('')}</div>`;
  };

  window.loadClientHome=async function(){await oldLoadClientHome();migrateRussia();enhancePeople()};

  window.openSettings=function(){
    closeV9Sheet();
    const city=cleanCity(localStorage.getItem('dh_city_v9')||'Москва'),n=localStorage.getItem('dh_notify_v9')!=='0',p=localStorage.getItem('dh_privacy_v9')!=='0';
    const d=document.createElement('div');d.id='v9Sheet';d.className='v9-sheet-backdrop';d.onclick=e=>{if(e.target===d)closeV9Sheet()};
    d.innerHTML=`<div class="v9-sheet"><div class="v9-handle"></div><h2>Настройки</h2>
      <div class="v9-setting"><span><b>Город</b><small>Для подбора исполнителей рядом</small></span><select id="v9City" onchange="saveLocalSettings()">${RUS_CITIES.map(c=>`<option ${c===city?'selected':''}>${c}</option>`).join('')}</select></div>
      <div class="v9-setting"><span><b>Уведомления</b><small>Статусы заказов, напоминания и сообщения</small></span><button id="v9Notify" class="v9-toggle ${n?'on':''}" onclick="toggleLocal('notify',this)"></button></div>
      <div class="v9-setting"><span><b>Приватность</b><small>Контакты скрыты до назначения исполнителя</small></span><button id="v9Privacy" class="v9-toggle ${p?'on':''}" onclick="toggleLocal('privacy',this)"></button></div>
      <button class="btn btn-dark btn-wide" onclick="closeV9Sheet();changeRole()"><i class="fa-solid fa-repeat"></i> Сменить роль</button>
      <button class="btn btn-ghost btn-wide" onclick="localStorage.removeItem('dh_intro_v9');closeV9Sheet();showView('intro')">Показать приветствие заново</button></div>`;
    document.body.append(d);
  };
  window.saveLocalSettings=function(){const c=cleanCity(document.getElementById('v9City')?.value||'Москва');localStorage.setItem('dh_city_v9',c);const l=document.getElementById('cityLabel');if(l)l.textContent=c;toast('Город сохранён')};

  window.renderServiceExecutors=function(){
    let rows=sitters.filter(s=>s.services.includes(selectedService));
    if(serviceSitterSort==='rating')rows.sort((a,b)=>b.rating-a.rating||b.walks-a.walks);else if(serviceSitterSort==='price')rows.sort((a,b)=>a.price-b.price);else rows.sort((a,b)=>(Number(b.sponsored)-Number(a.sponsored))||b.rating-a.rating||b.walks-a.walks);
    const top=Math.max(...rows.map(x=>x.walks),0),target=document.getElementById('v9ExecList'); if(!target)return;
    target.innerHTML=rows.map(s=>`<button class="v9-exec ${s.sponsored?'sponsored':''}" onclick="openBooking(${selectedService},${s.id})"><img src="${imgSrc(s.image)}" loading="lazy"><span><span class="v9-badges">${s.sponsored?'<span class="v9-badge ad">Продвижение</span>':''}${s.walks===top?'<span class="v9-badge">Топ рейтинга</span>':''}${s.free?'<span class="v9-badge">Свободен</span>':''}</span><b>${esc(s.name)}</b><span class="stars"><i class="fa-solid fa-star"></i> ${s.rating} · ${s.reviews} отзывов</span><small>${esc(s.area)} · ${s.distance} км · ${s.walks}+ услуг</small></span><span class="v9-exec-price">от ${s.price} ₽<span class="v9-arrow"><i class="fa-solid fa-chevron-right"></i></span></span></button>`).join('')||'<div class="notice">Исполнители скоро появятся</div>';
  };

  window.renderSitters=function(){
    let rows=[...sitters];const q=(document.getElementById('sitterSearch')?.value||'').trim().toLowerCase();if(q)rows=rows.filter(s=>`${s.name} ${s.area} ${s.about}`.toLowerCase().includes(q));if(sitterSort==='rating')rows.sort((a,b)=>b.rating-a.rating);else if(sitterSort==='price')rows.sort((a,b)=>a.price-b.price);else if(sitterSort==='free')rows=rows.filter(s=>s.free);else rows.sort((a,b)=>a.distance-b.distance);const f=favs(),target=document.getElementById('sitterList');if(!target)return;
    target.innerHTML=rows.map(s=>`<div class="sitter"><button class="sitter-main" onclick="openSitter(${s.id})"><span class="sitter-top"><img class="sitter-avatar" src="${imgSrc(s.image)}" loading="lazy"><span><span class="sitter-name">${esc(s.name)}</span><span class="rating"><i class="fa-solid fa-star"></i>${s.rating} (${s.reviews})</span><span class="sitter-meta">${esc(s.area)} · ${s.distance} км</span></span><span></span></span><span class="sitter-gallery"><img src="/assets/service-walk.webp"><img src="/assets/service-board.webp"><img src="/assets/service-home.webp"><img src="/assets/service-groom.webp"></span></button><button class="heart-button" style="position:absolute;right:16px;top:14px" onclick="toggleFavorite(${s.id},event)"><i class="${f.has(s.id)?'fa-solid':'fa-regular'} fa-heart"></i></button></div>`).join('')||'<div class="notice">Ничего не найдено</div>';
  };

  window.openSitter=function(id){
    selectedSitter=Number(id);const s=sitters.find(x=>x.id===selectedSitter);const target=document.getElementById('sitterProfile');if(!target)return oldOpenSitter(id);
    target.innerHTML=`<div class="sitter-cover"><img src="${imgSrc(s.image)}"><div class="sitter-cover-copy"><div class="sitter-cover-name">${esc(s.name)}</div><div class="rating"><i class="fa-solid fa-star"></i>${s.rating} · ${s.reviews} отзывов</div><div class="sitter-meta">${s.walks}+ выполненных услуг · ${esc(s.area)}</div></div></div><div class="about"><h3>ОБО МНЕ</h3><p>${esc(s.about)}</p></div><button class="btn btn-gold btn-wide" style="margin-top:9px" onclick="openBooking(1,${s.id})">Забронировать прогулку</button><button class="btn btn-dark btn-wide" style="margin-top:7px" onclick="showView('reviews')">Отзывы</button>`;showView('sitter');syncSelectedHeart();
  };

  window.loadExecutor=async function(){
    const rows=await api('/api/executor/orders');const f=executorTab==='available'?rows.filter(o=>o.status==='open'):rows.filter(o=>o.status!=='open');const el=document.getElementById('executorList');if(!el)return;
    el.innerHTML=f.length?f.map(o=>`<article class="v10-request"><div class="v10-request-top"><div class="v10-request-title"><div class="v10-request-icon"><i class="fa-solid ${serviceIcon(o.item_id)}"></i></div><div><h3>${esc(o.item_name)}</h3><div class="v10-request-time">${fmtDate(o.scheduled_date)} · ${esc(o.scheduled_time||'—')} · ${o.duration_min||60} мин</div></div></div><div class="v10-price">${o.price} ₽</div></div><div class="v10-request-meta"><div class="v10-meta"><span>Питомец</span><b>${esc(o.pet_name||'Питомец')}</b></div><div class="v10-meta"><span>Адрес</span><b>${esc(ruAddress(o.address||'Москва'))}</b></div></div><div class="v10-request-actions">${o.status==='open'?`<button class="btn btn-gold" onclick="acceptOrder(${o.id})">Взять заявку</button>`:o.status==='accepted'?`<button class="btn btn-gold" onclick="setOrderStatus(${o.id},'in_progress')">Начать</button>`:o.status==='in_progress'?`<button class="btn btn-gold" onclick="setOrderStatus(${o.id},'done')">Завершить</button>`:`<span class="v10-status"><i class="fa-solid fa-check" style="margin-right:6px"></i>Завершён</span>`}</div></article>`).join(''):'<div class="notice">Заявок пока нет</div>';
  };

  window.loadOrders=async function(){
    const all=await api('/api/orders');const rows=orderTab==='current'?all.filter(o=>!['done','cancelled'].includes(o.status)):orderTab==='history'?all.filter(o=>o.status==='done'):all.filter(o=>o.status==='cancelled');const om=JSON.parse(localStorage.getItem('dh_order_sitters_v9')||'{}'),el=document.getElementById('ordersList');if(!el)return;
    el.innerHTML=rows.length?rows.map(o=>{const sid=om[o.id],s=sitters.find(x=>x.id===Number(sid));return `<div class="order"><div class="order-head"><span><h3>${esc(o.item_name)}</h3>${s?`<div class="v9-order-sitter"><i class="fa-solid fa-user-check"></i> ${esc(s.name)} · ${s.rating}</div>`:''}<span class="order-meta">${fmtDate(o.scheduled_date)} · ${esc(o.scheduled_time||'')} · ${o.duration_min||60} мин<br>${esc(ruAddress(o.address||'Москва'))} · ${esc(o.pet_name||'Питомец')}</span></span><span class="status ${o.status==='done'?'green':''}">${statusText(o.status)}</span></div><div class="order-actions"><button class="btn btn-dark btn-small" onclick="showView('chat')">Чат</button><button class="btn btn-dark btn-small" onclick="${o.status==='done'?"showView('report')":`openBooking(${o.item_id},${sid||101})`}">${o.status==='done'?'Отчёт':'Повторить'}</button>${!['done','cancelled'].includes(o.status)?`<button class="btn btn-dark btn-small" onclick="cancelOrder(${o.id})">Отменить</button>`:'<span></span>'}</div></div>`}).join(''):'<div class="notice">В этом разделе пока пусто</div>';
  };

  let selectedCalendarIso='';
  window.loadCalendar=async function(role='client'){
    calendarRows=await api(`/api/calendar?role=${role}`);renderCalendar();
    const host=document.getElementById('calendarOrders');if(!host)return;
    host.className='v10-history';
    host.innerHTML=calendarRows.length?calendarRows.slice().reverse().map(o=>`<div class="v10-history-card"><div class="v10-history-date">${new Date(`${o.scheduled_date}T12:00:00`).getDate()}<small>${monthShort(o.scheduled_date)}</small></div><div><b>${esc(o.item_name)} · ${esc(o.pet_name||'Питомец')}</b><p>${esc(o.scheduled_time||'')} · ${o.duration_min||60} мин · ${esc(ruAddress(o.address||'Москва'))}</p></div><span class="status ${o.status==='done'?'green':''}">${statusText(o.status)}</span></div>`).join(''):'<div class="notice">История пока пустая</div>';
    let panel=document.getElementById('v10DayPanel');if(!panel){panel=document.createElement('div');panel.id='v10DayPanel';panel.className='v10-day-panel';document.querySelector('#view-calendar .section-title')?.insertAdjacentElement('beforebegin',panel)}
    const today=new Date(),iso=`${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`;showCalendarDay(selectedCalendarIso||iso);
  };
  window.renderCalendar=function(){
    const y=calendarDate.getFullYear(),m=calendarDate.getMonth(),first=new Date(y,m,1),days=new Date(y,m+1,0).getDate(),offset=(first.getDay()+6)%7,today=new Date();const month=document.getElementById('calendarMonth');if(month)month.textContent=new Intl.DateTimeFormat('ru-RU',{month:'long',year:'numeric'}).format(calendarDate);let h='';for(let i=0;i<offset;i++)h+='<button class="calendar-day empty" tabindex="-1"></button>';for(let d=1;d<=days;d++){const iso=`${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`,has=calendarRows.some(o=>o.scheduled_date===iso),now=today.getFullYear()===y&&today.getMonth()===m&&today.getDate()===d,sel=selectedCalendarIso===iso;h+=`<button class="calendar-day ${has?'has-order':''} ${now?'today':''} ${sel?'selected':''}" onclick="showCalendarDay('${iso}')">${d}</button>`}const grid=document.getElementById('calendarGrid');if(grid)grid.innerHTML=h;
  };
  window.showCalendarDay=function(iso){
    selectedCalendarIso=iso;renderCalendar();const rows=calendarRows.filter(o=>o.scheduled_date===iso),panel=document.getElementById('v10DayPanel');if(!panel)return;const label=new Intl.DateTimeFormat('ru-RU',{weekday:'long',day:'numeric',month:'long'}).format(new Date(`${iso}T12:00:00`));panel.innerHTML=`<div class="v10-day-head"><b>${label.charAt(0).toUpperCase()+label.slice(1)}</b><span>${rows.length?`${rows.length} ${rows.length===1?'запись':'записи'}`:'свободно'}</span></div>${rows.length?rows.map(o=>`<div class="v10-day-item"><div class="v10-day-time">${esc(o.scheduled_time||'—')}</div><div><b>${esc(o.item_name)}</b><small>${esc(o.pet_name||'Питомец')} · ${o.duration_min||60} мин</small></div><span class="status ${o.status==='done'?'green':''}">${statusText(o.status)}</span></div>`).join(''):'<div class="notice" style="padding:10px">На этот день заказов нет</div>'}`;
  };

  window.loadLeaderboard=async function(){
    const data=await api('/api/leaderboard'),rows=rankTab==='clients'?data.clients:data.executors,opt=document.getElementById('ratingOpt'),list=document.getElementById('leaderboardList');
    opt.innerHTML=rankTab==='clients'?`<label><span><b>Участвовать в рейтинге заказчиков</b><small style="display:block;margin-top:3px;color:var(--v10-muted)">Можно отключить в любой момент</small></span><input type="checkbox" ${data.rating_opt_in?'checked':''} onchange="toggleRatingOpt(this.checked)"></label>`:'<i class="fa-solid fa-circle-info" style="color:var(--v10-gold2);margin-right:7px"></i>Рейтинг исполнителей считается по количеству завершённых заявок.';
    list.innerHTML=rows.map((r,i)=>`<div class="leader-row"><div class="leader-pos">${i+1}</div><div><b>${esc(r.name)}</b><small><i class="fa-solid fa-star" style="color:var(--v10-gold2);margin-right:4px"></i>${r.rating} · ${rankTab==='clients'?'заказов':'выполнено'}</small></div><div class="leader-score">${r.score}</div></div>`).join('');
  };

  window.loadExecutorSchedule=async function(){const rows=await api('/api/calendar?role=executor'),el=document.getElementById('executorSchedule');if(!el)return;el.innerHTML=rows.length?rows.map(o=>`<div class="history-row"><b>${fmtDate(o.scheduled_date)} · ${esc(o.scheduled_time||'—')}</b><small>${esc(o.item_name)} · ${o.duration_min||60} мин<br>${esc(o.pet_name||'Питомец')} · ${esc(ruAddress(o.address||'Москва'))}</small><span class="status ${o.status==='done'?'green':''}">${statusText(o.status)}</span></div>`).join(''):'<div class="notice">Расписание пока пустое</div>'};

  window.showView=async function(v){await oldShowView(v);enhancePeople();migrateRussia();if(v==='executor-orders')await window.loadExecutor();if(v==='orders')await window.loadOrders();if(v==='calendar')await window.loadCalendar('client');if(v==='leaderboard')await window.loadLeaderboard();if(v==='executor-schedule')await window.loadExecutorSchedule();if(v==='sitters')window.renderSitters();if(v==='client-home'){const city=document.getElementById('cityLabel');if(city)city.textContent=cleanCity(localStorage.getItem('dh_city_v9')||'Москва')}};

  function init(){migrateRussia();enhancePeople();const address=document.getElementById('bookAddress');if(address)address.value='ул. Тверская, 12';const city=document.getElementById('cityLabel');if(city)city.textContent='Москва';if(currentView==='client-home')window.loadClientHome().catch(()=>{});if(currentView==='executor-orders')window.loadExecutor().catch(()=>{});if(currentView==='calendar')window.loadCalendar('client').catch(()=>{});if(currentView==='leaderboard')window.loadLeaderboard().catch(()=>{})}
  setTimeout(init,0);
})();
