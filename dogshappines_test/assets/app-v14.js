(() => {
  'use strict';

  const wait = (fn, tries = 160) => {
    if (window.V13 && window.openOrderChatV13 && window.api && window.showView) return fn();
    if (tries <= 0) return console.error('v14: v13 runtime not ready');
    setTimeout(() => wait(fn, tries - 1), 50);
  };

  wait(() => {
    const q = id => document.getElementById(id);
    const safe = v => window.esc ? esc(v ?? '') : String(v ?? '');
    const note = t => window.toast ? toast(t) : alert(t);
    const originalShow = window.showView;
    const originalOpenSimple = window.openSimple;
    const originalOpenBooking = window.openBooking;
    const originalLoadClientProfile = window.loadClientProfile;
    const originalLoadExecutorProfile = window.loadExecutorProfile;
    const originalLoadClientHome = window.loadClientHome;
    const originalRenderTariffs = window.renderTariffs;

    window.V14 = {
      me: null,
      orders: [],
      execOrders: [],
      calendar: { orders: [], blocks: [] },
      calendarMonth: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
      calendarDay: iso(new Date()),
      bookingPetId: null,
      chatOrderId: null,
      chatTimer: null,
      reportFiles: [],
      rankTab: 'clients'
    };

    const STATUS = {
      open: 'Ожидает подтверждения',
      accepted: 'Подтверждён',
      in_progress: 'В процессе',
      done: 'Завершён',
      cancelled: 'Отменён',
      declined: 'Отклонён'
    };
    const STATUS_ICON = {
      open: 'fa-clock',
      accepted: 'fa-circle-check',
      in_progress: 'fa-person-walking',
      done: 'fa-check-double',
      cancelled: 'fa-ban',
      declined: 'fa-circle-xmark'
    };
    const DURATION_OPTIONS = {
      1: [[30,'30 мин'],[60,'1 час'],[90,'1,5 часа']],
      2: [[720,'12 часов'],[1440,'1 сутки'],[2880,'2 суток']],
      3: [[30,'30 мин'],[60,'1 час'],[120,'2 часа']],
      4: [[60,'1 час'],[90,'1,5 часа']],
      5: [[30,'30 мин'],[60,'1 час']],
      6: [[60,'1 час'],[120,'2 часа']],
      7: [[30,'30 мин'],[60,'1 час']],
      8: [[30,'30 мин'],[60,'1 час'],[120,'2 часа']]
    };
    const PRICE_FACTORS = {
      1:{30:.65,60:1,90:1.35},2:{720:.65,1440:1,2880:1.85},3:{30:.7,60:1,120:1.75},
      4:{60:1,90:1.35},5:{30:1,60:1.65},6:{60:1,120:1.65},7:{30:.75,60:1},8:{30:.75,60:1,120:1.75}
    };

    function pad(n){ return String(n).padStart(2,'0'); }
    function iso(d){ return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`; }
    function parseDate(date, time='12:00'){ const d=new Date(`${date}T${time}:00`); return Number.isNaN(d.getTime())?null:d; }
    function fmtDate(s){
      const d=parseDate(s); return d ? new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'short'}).format(d).replace('.','') : s;
    }
    function fmtFullDate(s){
      const d=parseDate(s); return d ? new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'long',year:'numeric'}).format(d) : s;
    }
    function fmtDuration(min){
      min=Number(min||0);
      if(min===1440)return '1 сутки';
      if(min===2880)return '2 суток';
      if(min>=1440)return `${Math.round(min/1440)} сут.`;
      if(min===90)return '1 ч 30 мин';
      if(min>=60 && min%60===0)return `${min/60} ч`;
      return `${min} мин`;
    }
    function money(v){ return `${Number(v||0).toLocaleString('ru-RU')} ₽`; }
    function statusText(s){ return STATUS[s] || s; }
    function statusClass(s){ return `v14-status-${s||'open'}`; }
    function avatar(src){ return /^https?:|^\/uploads\//i.test(src||'') ? src : `/assets/${src||'sitter-v8.webp'}`; }
    function todayPlus(minutes){
      const d=new Date(Date.now()+minutes*60000);
      return {date:iso(d),time:`${pad(d.getHours())}:${pad(d.getMinutes())}`};
    }
    function estimatePrice(service,duration){
      const item=(catalogCache||[]).find(x=>Number(x.id)===Number(service));
      const exec=(V13.executors||[]).find(x=>Number(x.id)===Number(selectedSitter));
      const base=Math.max(Number(item?.price||0),Number(exec?.price||0)), factor=PRICE_FACTORS[Number(service)]?.[Number(duration)] || Math.max(.65,Number(duration)/(Number(service)===2?1440:60));
      return Math.round((base*factor)/50)*50;
    }
    async function refreshMe(){ V14.me=await api('/api/me'); return V14.me; }

    function removeSheet(){
      q('v14SheetBackdrop')?.remove();
    }
    function sheet(title, body, actions=''){
      removeSheet();
      const d=document.createElement('div');
      d.id='v14SheetBackdrop'; d.className='v14-sheet-backdrop';
      d.onclick=e=>{ if(e.target===d)removeSheet(); };
      d.innerHTML=`<div class="v14-sheet" onclick="event.stopPropagation()">
        <div class="v14-sheet-handle"></div>
        <div class="v14-sheet-head"><h2>${safe(title)}</h2><button onclick="document.getElementById('v14SheetBackdrop')?.remove()"><i class="fa-solid fa-xmark"></i></button></div>
        <div class="v14-sheet-body">${body}</div>
        ${actions?`<div class="v14-sheet-actions">${actions}</div>`:''}
      </div>`;
      document.body.append(d);
    }

    async function ensurePetsForBooking(){
      const pets=await api('/api/pets');
      const pet=pets.find(x=>Number(x.id)===Number(V14.bookingPetId)) || pets[0];
      const label=q('bookingPetName');
      const pick=document.querySelector('#view-booking .pet-pick');
      if(pet){
        V14.bookingPetId=Number(pet.id);
        bookingPet=pet.name;
        if(label)label.textContent=pet.name;
        const img=pick?.querySelector('img');
        if(img)img.src=pet.photo_url||'/assets/service-walk.webp';
      } else {
        V14.bookingPetId=null;
        bookingPet='';
        if(label)label.textContent='Добавьте питомца';
      }
      const b=q('bookingSubmit');
      if(b)b.disabled=!pet;
      return pets;
    }

    function configureDurations(serviceId){
      const host=q('durationChoices');
      const opts=DURATION_OPTIONS[Number(serviceId)]||DURATION_OPTIONS[1];
      if(!host)return;
      const preferred=opts.some(x=>x[0]===Number(bookingDuration))?Number(bookingDuration):opts[0][0];
      bookingDuration=preferred;
      host.innerHTML=opts.map(([min,label],i)=>`<button class="choice ${min===preferred?'active':''}" data-min="${min}" onclick="selectDuration(this);updateBookingPriceV14()">${safe(label)}</button>`).join('');
    }
    window.updateBookingPriceV14=()=>{
      let box=q('v14BookingPrice');
      const submit=q('bookingSubmit');
      if(!submit)return;
      if(!box){box=document.createElement('div');box.id='v14BookingPrice';box.className='v14-booking-price';submit.insertAdjacentElement('beforebegin',box);}
      const exec=(V13.executors||[]).find(x=>Number(x.id)===Number(selectedSitter));
      const est=estimatePrice(selectedService,bookingDuration);
      box.innerHTML=`<span>Итого</span><b>${money(est)}</b><small>${exec?`Исполнитель: ${safe(exec.name)} · `:''}${fmtDuration(bookingDuration)}</small>`;
    };

    window.openBooking=async(serviceId,sitterId)=>{
      await originalOpenBooking(serviceId,sitterId);
      configureDurations(serviceId);
      const n=todayPlus(30);
      const date=q('bookDate'),time=q('bookTime');
      if(date){date.min=iso(new Date()); if(!date.value)date.value=n.date;}
      if(time && (!time.value || (date?.value===iso(new Date()) && parseDate(date.value,time.value)<new Date())))time.value=n.time;
      await ensurePetsForBooking();
      updateBookingPriceV14();
    };

    window.submitBooking=async()=>{
      const b=q('bookingSubmit');
      const date=q('bookDate')?.value,time=q('bookTime')?.value,address=(q('bookAddress')?.value||'').trim();
      if(!V14.bookingPetId)return note('Сначала добавьте и выберите питомца');
      if(!date||!time)return note('Выберите дату и время');
      const dt=parseDate(date,time);
      if(!dt || dt<new Date(Date.now()-60000))return note('Выбранное время уже прошло');
      const item=(catalogCache||[]).find(x=>Number(x.id)===Number(selectedService));
      if(Number(selectedService)!==5 && address.length<5)return note('Укажите адрес');
      b.disabled=true; const old=b.textContent; b.textContent='Отправляем заявку…';
      try{
        const r=await api('/api/orders',{method:'POST',body:JSON.stringify({
          item_id:Number(selectedService),executor_id:Number(selectedSitter)||null,
          scheduled_date:date,scheduled_time:time,duration_min:Number(bookingDuration),
          address,pet_id:V14.bookingPetId,notes:q('bookNotes')?.value||''
        })});
        note(`Заявка создана · ${money(r.price)}`);
        await originalShow('orders');
        await loadOrders();
      }catch(e){note(e.message)}
      finally{b.disabled=false;b.textContent=old||'Создать заказ'}
    };

    function clientOrderCard(o){
      const closed=['done','cancelled','declined'].includes(o.status);
      return `<article class="v14-order-card ${statusClass(o.status)}">
        <div class="v14-order-head">
          <span class="v14-order-icon"><i class="fa-solid ${STATUS_ICON[o.status]||'fa-paw'}"></i></span>
          <div><small>${fmtDate(o.scheduled_date)} · ${safe(o.scheduled_time)} · ${fmtDuration(o.duration_min)}</small><b>${safe(o.item_name)}</b><em>${safe(o.executor_name||'Исполнитель выбирается')}</em></div>
          <span class="v14-status">${statusText(o.status)}</span>
        </div>
        <div class="v14-order-data">
          <span><i class="fa-solid fa-paw"></i>${safe(o.pet_name||'Питомец')}</span>
          ${o.address?`<span><i class="fa-solid fa-location-dot"></i>${safe(o.address)}</span>`:''}
          <span><i class="fa-solid fa-wallet"></i>${money(o.price)}</span>
        </div>
        <div class="v14-order-actions">
          <button onclick="openOrderDetailsV14(${o.id})">Детали</button>
          ${!['cancelled','declined'].includes(o.status)?`<button onclick="openOrderChatV14(${o.id})"><i class="fa-regular fa-message"></i> Чат</button>`:''}
          ${o.status==='done'&&o.report_ready?`<button onclick="openReportV14(${o.id})"><i class="fa-regular fa-images"></i> Отчёт</button>`:''}
          ${o.status==='done'&&!o.reviewed?`<button class="gold" onclick="openReviewV14(${o.id})"><i class="fa-solid fa-star"></i> Оценить</button>`:''}
          ${['open','accepted'].includes(o.status)?`<button class="danger" onclick="cancelOrder(${o.id})">Отменить</button>`:''}
        </div>
      </article>`;
    }

    window.loadOrders=async()=>{
      V14.orders=await api('/api/orders');
      const tab=orderTab||'current';
      const rows=tab==='current'
        ?V14.orders.filter(o=>!['done','cancelled','declined'].includes(o.status))
        :tab==='history'?V14.orders.filter(o=>o.status==='done')
        :V14.orders.filter(o=>['cancelled','declined'].includes(o.status));
      const h=q('ordersList'); if(!h)return;
      h.innerHTML=rows.length?rows.map(clientOrderCard).join(''):`<div class="v14-empty"><i class="fa-regular fa-calendar"></i><b>${tab==='current'?'Активных заказов нет':'Здесь пока пусто'}</b><span>${tab==='current'?'Выберите услугу и исполнителя, чтобы создать заявку.':'История появится после заказов.'}</span>${tab==='current'?'<button class="btn btn-gold" onclick="showView(\'services\')">Выбрать услугу</button>':''}</div>`;
    };

    window.cancelOrder=async id=>{
      if(!confirm('Отменить этот заказ?'))return;
      try{await api(`/api/orders/${id}/cancel`,{method:'POST',body:'{}'});note('Заказ отменён');await loadOrders();}catch(e){note(e.message)}
    };

    window.openOrderDetailsV14=async id=>{
      try{
        const o=await api(`/api/orders/${id}`);
        const events=o.events||[];
        sheet(`Заказ №${id}`,`
          <div class="v14-detail-status ${statusClass(o.status)}"><i class="fa-solid ${STATUS_ICON[o.status]||'fa-paw'}"></i><div><small>СТАТУС</small><b>${statusText(o.status)}</b></div></div>
          <div class="v14-detail-grid">
            <div><span>Услуга</span><b>${safe(o.item_name)}</b></div><div><span>Стоимость</span><b>${money(o.price)}</b></div>
            <div><span>Дата</span><b>${fmtFullDate(o.scheduled_date)}</b></div><div><span>Время</span><b>${safe(o.scheduled_time)} · ${fmtDuration(o.duration_min)}</b></div>
            <div class="wide"><span>Питомец</span><b>${safe(o.pet_name||'—')}</b></div>
            ${o.executor_name?`<div class="wide"><span>Исполнитель</span><b>${safe(o.executor_name)}</b></div>`:''}
            ${o.address?`<div class="wide"><span>Адрес</span><b>${safe(o.address)}</b></div>`:''}
            ${o.notes?`<div class="wide"><span>Комментарий</span><b>${safe(o.notes)}</b></div>`:''}
          </div>
          <div class="v14-timeline">${events.length?events.map(e=>`<div><i></i><span><b>${safe(e.text)}</b><small>${new Date(e.created_at).toLocaleString('ru-RU',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}</small></span></div>`).join(''):'<div class="v14-muted">Событий пока нет</div>'}</div>
        `,`<button class="btn btn-dark" onclick="document.getElementById('v14SheetBackdrop')?.remove();openOrderChatV14(${id})">Открыть чат</button>${o.report_ready?`<button class="btn btn-gold" onclick="document.getElementById('v14SheetBackdrop')?.remove();openReportV14(${id})">Фотоотчёт</button>`:''}`);
      }catch(e){note(e.message)}
    };

    function executorOrderCard(o){
      const targeted=Number(o.target_executor_id)===Number(V14.me?.id);
      return `<article class="v14-request-card ${targeted?'targeted':''} ${statusClass(o.status)}">
        <div class="v14-request-head"><div><small>${fmtDate(o.scheduled_date)} · ${safe(o.scheduled_time)} · ${fmtDuration(o.duration_min)}</small><b>${safe(o.item_name)}</b>${targeted&&o.status==='open'?'<em>Адресно вам</em>':''}</div><strong>${money(o.price)}</strong></div>
        <div class="v14-request-data"><span><i class="fa-solid fa-paw"></i>${safe(o.pet_name||'Питомец')}</span>${o.address?`<span><i class="fa-solid fa-location-dot"></i>${safe(o.address)}</span>`:''}${o.notes?`<span class="wide"><i class="fa-regular fa-note-sticky"></i>${safe(o.notes)}</span>`:''}</div>
        <div class="v14-request-actions">
          ${o.status==='open'?`<button class="btn btn-gold" onclick="acceptOrder(${o.id})">Принять</button>${targeted?`<button class="btn btn-dark" onclick="rejectOrderV14(${o.id})">Отклонить</button><button onclick="openOrderChatV14(${o.id})">Чат</button>`:''}`:''}
          ${o.status==='accepted'?`<button onclick="openOrderChatV14(${o.id})">Чат</button><button class="btn btn-gold" onclick="setOrderStatus(${o.id},'in_progress')">Начать услугу</button>`:''}
          ${o.status==='in_progress'?`<button onclick="openOrderChatV14(${o.id})">Чат</button><button class="btn btn-gold" onclick="setOrderStatus(${o.id},'done')">Завершить и отправить отчёт</button>`:''}
          ${o.status==='done'?`<button onclick="openOrderChatV14(${o.id})">Чат</button>${o.report_ready?`<button onclick="openReportV14(${o.id})">Отчёт</button>`:''}`:''}
        </div>
      </article>`;
    }

    window.loadExecutor=async()=>{
      if(!V14.me)await refreshMe();
      V14.execOrders=await api('/api/executor/orders');
      const tab=executorTab||'available';
      const rows=tab==='available'?V14.execOrders.filter(o=>o.status==='open'):V14.execOrders.filter(o=>o.status!=='open');
      const h=q('executorList'); if(!h)return;
      h.innerHTML=rows.length?rows.map(executorOrderCard).join(''):`<div class="v14-empty"><i class="fa-solid fa-briefcase"></i><b>${tab==='available'?'Новых заявок нет':'У вас пока нет заказов'}</b><span>${tab==='available'?'Новые адресные и свободные заявки появятся здесь.':'Принятые заказы появятся в расписании.'}</span></div>`;
    };
    window.acceptOrder=async id=>{
      try{await api(`/api/executor/orders/${id}/accept`,{method:'POST',body:'{}'});note('Заявка подтверждена');await loadExecutor();await loadExecutorHome();}catch(e){note(e.message)}
    };
    window.rejectOrderV14=async id=>{
      if(!confirm('Отклонить адресную заявку?'))return;
      try{await api(`/api/executor/orders/${id}/reject`,{method:'POST',body:'{}'});note('Заявка отклонена');await loadExecutor();}catch(e){note(e.message)}
    };
    window.setOrderStatus=async(id,status)=>{
      if(status==='done')return openReportSubmitV14(id);
      try{await api(`/api/executor/orders/${id}/status`,{method:'POST',body:JSON.stringify({status})});note('Услуга начата');await loadExecutor();await loadExecutorHome();}catch(e){note(e.message)}
    };

    window.openReportSubmitV14=async id=>{
      V14.reportFiles=[];
      sheet('Завершение услуги',`
        <div class="v14-report-form">
          <label>Как всё прошло<textarea id="v14ReportSummary" class="field textarea" placeholder="Короткий итог для хозяина"></textarea></label>
          <label>Пройдено, км <input id="v14ReportDistance" class="field" inputmode="decimal" placeholder="Например, 1.8"></label>
          <label>Фотоотчёт <input id="v14ReportFiles" type="file" accept="image/*" multiple onchange="previewReportFilesV14(this)"></label>
          <div id="v14ReportPreview" class="v14-report-preview"><span>Можно добавить до 3 фотографий</span></div>
        </div>`,
        `<button class="btn btn-dark" onclick="document.getElementById('v14SheetBackdrop')?.remove()">Назад</button><button id="v14CompleteBtn" class="btn btn-gold" onclick="completeOrderV14(${id})">Отправить отчёт и завершить</button>`
      );
    };
    window.previewReportFilesV14=async input=>{
      const files=[...(input.files||[])].slice(0,3);
      V14.reportFiles=[];
      for(const f of files){
        try{V14.reportFiles.push(await compressImage(f));}catch(_){}
      }
      const h=q('v14ReportPreview');
      if(h)h.innerHTML=V14.reportFiles.length?V14.reportFiles.map(x=>`<img src="${x}">`).join(''):'<span>Фото не выбраны</span>';
    };
    window.completeOrderV14=async id=>{
      const summary=(q('v14ReportSummary')?.value||'').trim();
      if(summary.length<8)return note('Напишите короткий итог услуги');
      const b=q('v14CompleteBtn'); if(b)b.disabled=true;
      try{
        await api(`/api/orders/${id}/report`,{method:'POST',body:JSON.stringify({summary,distance_km:q('v14ReportDistance')?.value||'',images:V14.reportFiles})});
        await api(`/api/executor/orders/${id}/status`,{method:'POST',body:JSON.stringify({status:'done'})});
        removeSheet();note('Заказ завершён, отчёт отправлен');await loadExecutor();await loadExecutorHome();
      }catch(e){note(e.message)}finally{if(b)b.disabled=false}
    };

    window.openReportV14=async id=>{
      try{
        const [o,r]=await Promise.all([api(`/api/orders/${id}`),api(`/api/orders/${id}/report`)]);
        if(!r)return note('Отчёт ещё не добавлен');
        const v=q('view-report');
        if(v){
          const head=v.querySelector('.screen-head');
          v.innerHTML='';
          v.append(head||document.createElement('div'));
          if(head)head.querySelector('.back')?.setAttribute('onclick',`showView('${currentRole==='executor'?'executor-orders':'orders'}')`);
          v.insertAdjacentHTML('beforeend',`<div class="v14-report-card">
            <div class="v14-report-head"><span><i class="fa-solid fa-check"></i></span><div><small>ОТЧЁТ ПО ЗАКАЗУ №${id}</small><b>${safe(o.item_name)}</b><em>${fmtFullDate(o.scheduled_date)} · ${safe(o.scheduled_time)}</em></div></div>
            ${r.attachments?.length?`<div class="v14-report-gallery">${r.attachments.map(x=>`<img src="${safe(x)}" onclick="openPhoto(this.src)">`).join('')}</div>`:''}
            <p>${safe(r.summary)}</p>
            <div class="v14-report-meta"><span><i class="fa-regular fa-clock"></i>${fmtDuration(o.duration_min)}</span>${r.distance_km?`<span><i class="fa-solid fa-route"></i>${safe(r.distance_km)} км</span>`:''}</div>
          </div>`);
        }
        await originalShow('report');
      }catch(e){note(e.message)}
    };

    window.openReviewV14=id=>{
      sheet('Оценить исполнителя',`
        <div class="v14-review-form">
          <div id="v14Stars" class="v14-stars">${[1,2,3,4,5].map(n=>`<button onclick="selectReviewStarV14(${n})"><i class="fa-regular fa-star"></i></button>`).join('')}</div>
          <textarea id="v14ReviewText" class="field textarea" placeholder="Что понравилось или что можно улучшить"></textarea>
        </div>`,
        `<button class="btn btn-gold btn-wide" onclick="submitReviewV14(${id})">Отправить отзыв</button>`);
      V14.reviewRating=5; selectReviewStarV14(5);
    };
    window.selectReviewStarV14=n=>{
      V14.reviewRating=n;
      q('v14Stars')?.querySelectorAll('button').forEach((b,i)=>b.innerHTML=`<i class="${i<n?'fa-solid':'fa-regular'} fa-star"></i>`);
    };
    window.submitReviewV14=async id=>{
      try{await api(`/api/orders/${id}/review`,{method:'POST',body:JSON.stringify({rating:V14.reviewRating||5,text:q('v14ReviewText')?.value||''})});removeSheet();note('Спасибо за отзыв');await loadOrders();}catch(e){note(e.message)}
    };

    function clearChatTimer(){if(V14.chatTimer){clearInterval(V14.chatTimer);V14.chatTimer=null}}
    async function renderChat(){
      if(!V14.chatOrderId)return;
      const msgs=await api(`/api/orders/${V14.chatOrderId}/messages`);
      const h=q('v14ChatMessages');if(!h)return;
      h.innerHTML=msgs.length?msgs.map(m=>{
        if(m.type==='system'||Number(m.sender_id)===0)return `<div class="v14-system-msg"><span>${safe(m.text)}</span><small>${new Date(m.created_at).toLocaleString('ru-RU',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}</small></div>`;
        return `<div class="v14-chat-msg ${Number(m.sender_id)===Number(V14.me?.id)?'mine':'theirs'}"><span>${safe(m.text)}</span><small>${new Date(m.created_at).toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'})}</small></div>`;
      }).join(''):`<div class="v14-chat-empty"><i class="fa-regular fa-comments"></i><b>Чат по заказу</b><span>Здесь можно уточнить детали услуги.</span></div>`;
      h.scrollTop=h.scrollHeight;
    }
    window.openOrderChatV14=async id=>{
      if(!V14.me)await refreshMe();
      clearChatTimer();
      V14.chatOrderId=Number(id);
      let o;try{o=await api(`/api/orders/${id}`)}catch(e){return note(e.message)}
      await originalShow('chat');
      const v=q('view-chat'); if(!v)return;
      const partner=currentRole==='executor'?o.customer_name:(o.executor_name||'Исполнитель');
      v.innerHTML=`<div class="v14-chat-shell">
        <div class="v14-chat-head"><button onclick="showView('${currentRole==='executor'?'executor-orders':'orders'}')"><i class="fa-solid fa-chevron-left"></i></button><div><small>${safe(o.item_name)} · заказ №${id}</small><b>${safe(partner||'Чат')}</b></div><span class="v14-chat-state ${statusClass(o.status)}">${statusText(o.status)}</span></div>
        <div id="v14ChatMessages" class="v14-chat-messages"></div>
        <form class="v14-chat-input" onsubmit="sendChatV14(event)"><input id="v14ChatText" maxlength="1500" autocomplete="off" placeholder="${['cancelled','declined'].includes(o.status)?'Чат закрыт':'Сообщение'}" ${['cancelled','declined'].includes(o.status)?'disabled':''}><button type="submit" ${['cancelled','declined'].includes(o.status)?'disabled':''}><i class="fa-solid fa-arrow-up"></i></button></form>
      </div>`;
      await renderChat();
      V14.chatTimer=setInterval(()=>{if(!q('view-chat')?.classList.contains('hidden'))renderChat().catch(()=>{});else clearChatTimer()},2500);
    };
    window.sendChatV14=async e=>{
      e.preventDefault();const i=q('v14ChatText'),text=(i?.value||'').trim();if(!text)return;
      i.disabled=true;
      try{await api(`/api/orders/${V14.chatOrderId}/messages`,{method:'POST',body:JSON.stringify({text})});i.value='';await renderChat();}catch(err){note(err.message)}finally{i.disabled=false;i.focus()}
    };
    window.openOrderChatV13=window.openOrderChatV14;

    function calendarMarkerClass(status){
      return status==='done'?'done':status==='in_progress'?'progress':status==='accepted'?'accepted':status==='cancelled'||status==='declined'?'cancelled':'open';
    }
    function renderCalendarV14(){
      const m=V14.calendarMonth, year=m.getFullYear(),month=m.getMonth();
      const first=new Date(year,month,1), start=(first.getDay()+6)%7, days=new Date(year,month+1,0).getDate();
      const title=q('calendarMonth');
      if(title)title.textContent=new Intl.DateTimeFormat('ru-RU',{month:'long',year:'numeric'}).format(first);
      const byDay={};
      (V14.calendar.orders||[]).forEach(o=>(byDay[o.scheduled_date]??=[]).push(o));
      const cells=[];
      for(let i=0;i<start;i++)cells.push('<span class="v14-cal-empty"></span>');
      for(let d=1;d<=days;d++){
        const key=`${year}-${pad(month+1)}-${pad(d)}`,rows=byDay[key]||[];
        cells.push(`<button class="v14-cal-day ${key===iso(new Date())?'today':''} ${key===V14.calendarDay?'selected':''} ${rows.length?'has':''}" onclick="selectCalendarDayV14('${key}')"><span>${d}</span><em>${rows.slice(0,3).map(o=>`<i class="${calendarMarkerClass(o.status)}"></i>`).join('')}</em></button>`);
      }
      const grid=q('calendarGrid');if(grid)grid.innerHTML=cells.join('');
      renderCalendarDayOrdersV14();
    }
    window.selectCalendarDayV14=key=>{V14.calendarDay=key;renderCalendarV14()};
    function renderCalendarDayOrdersV14(){
      const h=q('calendarOrders');if(!h)return;
      const rows=(V14.calendar.orders||[]).filter(o=>o.scheduled_date===V14.calendarDay).sort((a,b)=>(a.scheduled_time||'').localeCompare(b.scheduled_time||''));
      const section=h.previousElementSibling?.querySelector('span');if(section)section.textContent=`${fmtFullDate(V14.calendarDay)}`;
      h.innerHTML=rows.length?rows.map(o=>`<button class="v14-day-order" onclick="openOrderDetailsV14(${o.id})"><time>${safe(o.scheduled_time)}</time><span><b>${safe(o.item_name)}</b><small>${safe(o.pet_name||'Питомец')} · ${fmtDuration(o.duration_min)} · ${safe(o.executor_name||'')}</small></span><em class="${calendarMarkerClass(o.status)}">${statusText(o.status)}</em></button>`).join(''):'<div class="v14-empty compact"><i class="fa-regular fa-calendar-check"></i><b>На этот день заказов нет</b></div>';
    }
    window.loadCalendar=async(role='client')=>{
      V14.calendar=await api(`/api/calendar?role=${role}`);
      const firstOrder=(V14.calendar.orders||[]).find(o=>!['done','cancelled','declined'].includes(o.status));
      if(firstOrder)V14.calendarDay=firstOrder.scheduled_date;
      renderCalendarV14();
    };
    window.shiftMonth=delta=>{V14.calendarMonth=new Date(V14.calendarMonth.getFullYear(),V14.calendarMonth.getMonth()+delta,1);renderCalendarV14()};

    function fmtBlockDate(s){const d=new Date(s);return new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}).format(d)}
    window.loadExecutorSchedule=async()=>{
      const data=await api('/api/calendar?role=executor');
      const h=q('executorSchedule');if(!h)return;
      const items=[];
      (data.orders||[]).forEach(o=>items.push({kind:'order',date:o.scheduled_date,time:o.scheduled_time,ts:parseDate(o.scheduled_date,o.scheduled_time)?.getTime()||0,o}));
      (data.blocks||[]).forEach(b=>items.push({kind:'block',ts:new Date(b.start_at).getTime(),date:String(b.start_at).slice(0,10),b}));
      items.sort((a,b)=>a.ts-b.ts);
      const scheduleRows=items.length?items.map(x=>{
        if(x.kind==='order')return `<article class="v14-schedule-item ${statusClass(x.o.status)}"><time>${safe(x.o.scheduled_time)}</time><span><b>${safe(x.o.item_name)}</b><small>${fmtFullDate(x.o.scheduled_date)} · ${safe(x.o.pet_name||'Питомец')} · ${fmtDuration(x.o.duration_min)}</small></span><em>${statusText(x.o.status)}</em></article>`;
        const noteText=x.b.note?` · ${safe(x.b.note)}`:'';
        return `<article class="v14-schedule-item block"><time><i class="fa-solid fa-lock"></i></time><span><b>Недоступно</b><small>${fmtBlockDate(x.b.start_at)} → ${fmtBlockDate(x.b.end_at)}${noteText}</small></span><button onclick="deleteAvailabilityV14(${x.b.id})"><i class="fa-solid fa-xmark"></i></button></article>`;
      }).join(''):'<div class="v14-empty"><i class="fa-regular fa-calendar"></i><b>Расписание свободно</b><span>Принятые заявки и заблокированное время будут отображаться здесь.</span></div>';
      h.innerHTML=`<div class="v14-schedule-toolbar"><div><small>МОЁ РАСПИСАНИЕ</small><b>Заказы и недоступное время</b></div><button class="btn btn-gold" onclick="openAvailabilitySheetV14()"><i class="fa-solid fa-plus"></i> Заблокировать время</button></div>${scheduleRows}`;
    };
    window.openAvailabilitySheetV14=()=>{
      const n=todayPlus(60),e=todayPlus(120);
      sheet('Недоступное время',`<div class="v14-report-form"><label>Начало<input id="v14BlockStart" class="field" type="datetime-local" value="${n.date}T${n.time}"></label><label>Окончание<input id="v14BlockEnd" class="field" type="datetime-local" value="${e.date}T${e.time}"></label><label>Комментарий<input id="v14BlockNote" class="field" placeholder="Например, личные дела"></label></div>`,`<button class="btn btn-gold btn-wide" onclick="saveAvailabilityV14()">Сохранить</button>`);
    };
    window.saveAvailabilityV14=async()=>{
      try{await api('/api/executor/availability',{method:'POST',body:JSON.stringify({start_at:q('v14BlockStart')?.value,end_at:q('v14BlockEnd')?.value,note:q('v14BlockNote')?.value||''})});removeSheet();note('Время заблокировано');await loadExecutorSchedule();}catch(e){note(e.message)}
    };
    window.deleteAvailabilityV14=async id=>{
      try{await api('/api/executor/availability/delete',{method:'POST',body:JSON.stringify({id})});note('Интервал удалён');await loadExecutorSchedule();}catch(e){note(e.message)}
    };

    window.loadExecutorHome=async()=>{
      const [s,data]=await Promise.all([api('/api/executor/stats'),api('/api/calendar?role=executor')]);
      const stats=q('executorStats');
      if(stats)stats.innerHTML=[['Завершено',s.completed],['Активно',s.active],['Доход',money(s.income)]].map(([a,b])=>`<div class="metric"><strong>${b}</strong><small>${a}</small></div>`).join('');
      const rank=q('executorRankText');if(rank)rank.textContent=`Ваше место: ${s.rank} · рейтинг ${Number(s.rating||5).toFixed(1)}`;
      const rows=(data.orders||[]).filter(o=>!['done','cancelled','declined'].includes(o.status)).slice(0,3);
      const prev=q('executorPreview');if(prev)prev.innerHTML=rows.length?rows.map(o=>`<div class="timeline-line"><time>${safe(o.scheduled_time||'—')}</time><div><b>${safe(o.item_name)}</b><small>${safe(o.pet_name||'Питомец')} · ${fmtDate(o.scheduled_date)}</small></div><span>${statusText(o.status)}</span></div>`).join(''):'<div class="notice">На ближайшее время заказов нет</div>';
    };

    window.loadPets=async()=>{
      const pets=await api('/api/pets'),h=q('petsList');if(!h)return;
      h.innerHTML=pets.length?pets.map(p=>`<div class="v14-pet-card"><img src="${safe(p.photo_url||'/assets/service-walk.webp')}"><span><b>${safe(p.name)}</b><small>${safe(p.breed||'Порода не указана')}</small></span><div><button onclick="selectPetV14(${p.id},'${safe(p.name).replace(/'/g,'&#39;')}')">Выбрать</button><button onclick="chooseExistingPetPhoto(${p.id})"><i class="fa-solid fa-camera"></i></button></div></div>`).join(''):'<div class="v14-empty"><i class="fa-solid fa-paw"></i><b>Добавьте питомца</b><span>Питомец нужен, чтобы создавать заявки и хранить историю услуг.</span><button class="btn btn-gold" onclick="openPetSheet()">Добавить питомца</button></div>';
    };
    window.selectPetV14=(id,name)=>{
      V14.bookingPetId=Number(id);bookingPet=name;const x=q('bookingPetName');if(x)x.textContent=name;
      if(returnFromPets==='booking')showView('booking');else note('Питомец выбран');
    };
    window.savePet=async()=>{
      const name=(q('petName')?.value||'').trim(),breed=(q('petBreed')?.value||'').trim();
      if(!name)return note('Введите имя');
      try{
        const r=await api('/api/pets',{method:'POST',body:JSON.stringify({name,breed})});
        if(newPetPhotoData)await api(`/api/pets/${r.id}/photo`,{method:'POST',body:JSON.stringify({data_url:newPetPhotoData})});
        q('petSheet')?.classList.add('hidden');newPetPhotoData='';q('petName').value='';q('petBreed').value='';
        V14.bookingPetId=r.id;bookingPet=name;note('Питомец добавлен');await loadPets();
      }catch(e){note(e.message)}
    };
    window.uploadExistingPetPhoto=async input=>{
      if(!input.files?.[0]||!existingPetPhotoId)return;
      try{const data=await compressImage(input.files[0]);await api(`/api/pets/${existingPetPhotoId}/photo`,{method:'POST',body:JSON.stringify({data_url:data})});note('Фото обновлено');await loadPets();}catch(e){note(e.message)}
    };

    window.openSettingsV14=async()=>{
      let s;try{s=await api('/api/settings')}catch(e){return note(e.message)}
      const cities=(s.cities||[]).map(c=>`<option value="${safe(c)}" ${c===s.city?'selected':''}>${safe(c)}</option>`).join('');
      sheet('Настройки',`
        <div class="v14-settings">
          <label><span><b>Город</b><small>Исполнители и заявки рядом с вами</small></span><select id="v14City">${cities}</select></label>
          <label><span><b>Уведомления</b><small>Статусы заказов, сообщения и новые заявки</small></span><button id="v14Notif" class="v14-toggle ${s.notifications_enabled?'on':''}" onclick="toggleSettingV14(this,'notifications_enabled')"><i></i></button></label>
          <label><span><b>Приватность</b><small>Не показывать контакт до подтверждения заказа</small></span><button id="v14Privacy" class="v14-toggle ${s.privacy_hide_contacts?'on':''}" onclick="toggleSettingV14(this,'privacy_hide_contacts')"><i></i></button></label>
          ${s.has_executor_profile?`<label><span><b>Профиль исполнителя</b><small>Показывать вас клиентам в каталоге</small></span><button id="v14ExecVisible" class="v14-toggle ${s.executor_profile_active?'on':''}" onclick="toggleSettingV14(this,'executor_profile_active')"><i></i></button></label>`:''}
          <div class="v14-role-switch"><b>Режим приложения</b><div><button class="${currentRole==='client'?'active':''}" onclick="switchRoleV14('client')"><i class="fa-solid fa-paw"></i> Хозяин</button><button class="${currentRole==='executor'?'active':''}" onclick="switchRoleV14('executor')"><i class="fa-solid fa-briefcase"></i> Исполнитель</button></div></div>
          ${s.has_executor_profile?`<button class="v14-settings-link" onclick="openExecutorProfileSettingsV14()"><i class="fa-regular fa-id-card"></i><span><b>Профиль исполнителя</b><small>Услуги, район, цена и описание</small></span><i class="fa-solid fa-chevron-right"></i></button>`:''}
        </div>`,
        `<button class="btn btn-gold btn-wide" onclick="saveSettingsV14()">Сохранить</button>`);
    };
    window.toggleSettingV14=(b,key)=>{
      b.classList.toggle('on');b.dataset.key=key;
    };
    window.saveSettingsV14=async()=>{
      const payload={
        city:q('v14City')?.value,
        notifications_enabled:q('v14Notif')?.classList.contains('on'),
        privacy_hide_contacts:q('v14Privacy')?.classList.contains('on')
      };
      if(q('v14ExecVisible'))payload.executor_profile_active=q('v14ExecVisible').classList.contains('on');
      try{await api('/api/settings',{method:'POST',body:JSON.stringify(payload)});localStorage.setItem('dh_city_v9',payload.city);const lab=q('cityLabel');if(lab)lab.textContent=payload.city;removeSheet();note('Настройки сохранены');}catch(e){note(e.message)}
    };
    window.switchRoleV14=async role=>{
      try{await api('/api/me/role',{method:'POST',body:JSON.stringify({role})});currentRole=role;removeSheet();await refreshMe();await showView(role==='executor'?'executor-home':'client-home');note(role==='executor'?'Режим исполнителя включён':'Режим хозяина включён');}catch(e){note(e.message)}
    };
    window.openExecutorProfileSettingsV14=async()=>{
      let p=await api('/api/executor/profile');if(!p)return note('Сначала включите режим исполнителя');
      const serviceNames=(catalogCache||await api('/api/catalog'));
      sheet('Профиль исполнителя',`
        <div class="v14-settings">
          <label class="stack"><span><b>Район</b><small>Где вам удобно работать</small></span><input id="v14ExecArea" class="field" value="${safe(p.area||'Центр')}"></label>
          <label class="stack"><span><b>Цена от, ₽</b><small>Базовая стоимость часа</small></span><input id="v14ExecPrice" class="field" type="number" min="300" max="10000" value="${Number(p.price||700)}"></label>
          <label class="stack"><span><b>О себе</b><small>Опыт, подход и особенности работы</small></span><textarea id="v14ExecBio" class="field textarea">${safe(p.bio||'')}</textarea></label>
          <div class="v14-service-checks"><b>Услуги</b>${serviceNames.map(s=>`<label><input type="checkbox" value="${s.id}" ${p.services?.includes(Number(s.id))?'checked':''}><span>${safe(s.name)}</span></label>`).join('')}</div>
        </div>`,
        `<button class="btn btn-gold btn-wide" onclick="saveExecutorProfileV14()">Сохранить профиль</button>`);
    };
    window.saveExecutorProfileV14=async()=>{
      const services=[...document.querySelectorAll('.v14-service-checks input:checked')].map(x=>Number(x.value));
      try{await api('/api/executor/profile',{method:'POST',body:JSON.stringify({area:q('v14ExecArea')?.value,bio:q('v14ExecBio')?.value,price:Number(q('v14ExecPrice')?.value||700),services})});removeSheet();note('Профиль обновлён');}catch(e){note(e.message)}
    };
    window.openSimple=(type,...args)=>{
      if(type==='settings'||type==='location'||type==='notifications')return openSettingsV14();
      return originalOpenSimple?.(type,...args);
    };
    window.openSettings=window.openSettingsV14;

    window.loadLeaderboard=async()=>{
      const d=await api('/api/leaderboard'),tab=V14.rankTab||'clients',rows=d[tab]||[];
      const opt=q('ratingOpt');
      if(opt)opt.innerHTML=tab==='clients'?`<button class="v14-rank-opt ${d.rating_opt_in?'on':''}" onclick="toggleRatingOptV14(${!d.rating_opt_in})"><i class="fa-solid ${d.rating_opt_in?'fa-eye':'fa-eye-slash'}"></i><span><b>${d.rating_opt_in?'Вы участвуете в рейтинге':'Вы скрыты из рейтинга'}</b><small>Для заказчиков участие добровольное</small></span></button>`:'<div class="v14-rank-note"><i class="fa-solid fa-circle-info"></i> Рейтинг исполнителей считается по завершённым заказам и отзывам.</div>';
      const h=q('leaderboardList');if(h)h.innerHTML=rows.length?rows.map((r,i)=>`<div class="v14-rank-row ${r.me?'me':''}"><strong>${i+1}</strong><span><b>${safe(r.name)}</b><small>${tab==='executors'?`Рейтинг ${Number(r.rating||5).toFixed(1)} · `:''}${Number(r.score||0)} завершённых заказов</small></span>${i<3?`<i class="fa-solid fa-medal"></i>`:''}</div>`).join(''):'<div class="v14-empty compact"><b>Рейтинг пока пуст</b></div>';
    };
    window.setRankTab=tab=>{V14.rankTab=tab;q('rankClients')?.classList.toggle('active',tab==='clients');q('rankExecutors')?.classList.toggle('active',tab==='executors');loadLeaderboard()};
    window.toggleRatingOptV14=async enabled=>{try{await api('/api/settings',{method:'POST',body:JSON.stringify({rating_opt_in:enabled})});await loadLeaderboard()}catch(e){note(e.message)}};

    window.loadClientProfile=async()=>{
      if(originalLoadClientProfile)await originalLoadClientProfile();
      const s=await api('/api/client/stats');
      const h=q('clientProfileStats');if(h)h.innerHTML=`<div><strong>${s.pets}</strong><span>Питомцев</span></div><div><strong>${s.orders}</strong><span>Заказов</span></div><div><strong>${s.done}</strong><span>Завершено</span></div>`;
    };
    window.loadExecutorProfile=async()=>{
      if(originalLoadExecutorProfile)await originalLoadExecutorProfile();
      const [s,p]=await Promise.all([api('/api/executor/stats'),api('/api/executor/profile')]);
      const h=q('executorProfileStats');if(h)h.innerHTML=`<div><strong>${s.completed}</strong><span>Завершено</span></div><div><strong>${Number(s.rating||5).toFixed(1)}</strong><span>Рейтинг</span></div><div><strong>${s.rank}</strong><span>Место</span></div>`;
      const cover=q('view-executor-profile')?.querySelector('.executor-profile-cover img');if(cover&&p?.image)cover.src=avatar(p.image);
      const menu=q('view-executor-profile')?.querySelector('.menu');
      if(menu&&!q('v14EditExecProfile')){
        const b=document.createElement('button');b.id='v14EditExecProfile';b.onclick=openExecutorProfileSettingsV14;b.innerHTML='<i class="fa-regular fa-id-card"></i><span>Редактировать профиль</span><i class="fa-solid fa-chevron-right"></i>';menu.prepend(b);
      }
    };

    window.loadClientHome=async()=>{
      if(originalLoadClientHome)await originalLoadClientHome();
      const me=await refreshMe();const lab=q('cityLabel');if(lab)lab.textContent=me.city||'Москва';
    };

    window.showView=async v=>{
      if(v!=='chat')clearChatTimer();
      const r=await originalShow(v);
      if(v==='orders')await loadOrders();
      if(v==='executor-orders')await loadExecutor();
      if(v==='calendar')await loadCalendar('client');
      if(v==='executor-schedule')await loadExecutorSchedule();
      if(v==='leaderboard')await loadLeaderboard();
      if(v==='client-profile')await loadClientProfile();
      if(v==='executor-profile')await loadExecutorProfile();
      if(v==='executor-home')await loadExecutorHome();
      if(v==='pets')await loadPets();
      return r;
    };

    refreshMe().then(me=>{
      const lab=q('cityLabel');if(lab)lab.textContent=me.city||'Москва';
    }).catch(()=>{});
  });
})();
