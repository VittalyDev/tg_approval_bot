const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();
try { tg?.setHeaderColor('#050505'); tg?.setBackgroundColor('#050505'); } catch (_) {}

const initData = tg?.initData || '';
const PHOTO = {
  woman: 'https://images.unsplash.com/photo-1668421763548-2941326cbf68?auto=format&fit=crop&w=900&q=82',
  dog: 'https://images.unsplash.com/photo-1558788353-f76d92427f16?auto=format&fit=crop&w=900&q=82',
  cat: 'https://images.unsplash.com/photo-1652130559817-ae377e23628b?auto=format&fit=crop&w=900&q=82',
};
const servicePhotos={1:PHOTO.dog,2:PHOTO.cat,3:PHOTO.dog,4:PHOTO.dog,5:PHOTO.cat,6:PHOTO.dog};
const sitters = [
  {id:1,name:'Алина',rating:5.0,reviews:124,exp:'3 года',area:'Центр',distance:1.2,price:700,free:true,image:PHOTO.woman,walks:'280+',about:'Люблю собак и умею находить к ним подход. Всегда на связи и после каждой услуги отправляю подробный отчёт.',pets:[PHOTO.dog,PHOTO.cat,PHOTO.dog,PHOTO.cat]},
  {id:2,name:'Екатерина',rating:4.9,reviews:98,exp:'4 года',area:'Прозивка',distance:2.1,price:800,free:false,image:PHOTO.woman,walks:'320+',about:'Работаю с активными собаками, люблю длинные маршруты и спокойную коммуникацию с хозяином.',pets:[PHOTO.cat,PHOTO.dog,PHOTO.dog,PHOTO.cat]},
  {id:3,name:'Мария',rating:5.0,reviews:76,exp:'5 лет',area:'Mali Bajmok',distance:2.8,price:900,free:true,image:PHOTO.woman,walks:'410+',about:'Домашняя передержка и спокойный уход без клеток. Подходит для тревожных питомцев.',pets:[PHOTO.dog,PHOTO.cat,PHOTO.dog,PHOTO.cat]},
];
const reviews = [
  {name:'Мария',date:'12 сентября 2026',text:'Очень внимательная работа. После прогулки сразу получила подробный отчёт и фотографии.',image:PHOTO.woman},
  {name:'Иван',date:'5 сентября 2026',text:'Питомец вернулся спокойный и довольный. Удобный сервис, понятный статус заказа и хороший отчёт.',image:PHOTO.woman},
];
const serviceCategories = {1:'pet',2:'home',3:'home',4:'pet',5:'home',6:'extra'};
let selectedService = 1;
let selectedSitterId = 1;
let sitterSort = 'near';
let orderTab = 'current';
let executorTab = 'available';
let petsReturnView = 'profile';
let simpleReturnView = 'profile';

async function api(path, options = {}) {
  options.headers = {...(options.headers || {}), 'Content-Type':'application/json', 'X-Telegram-Init-Data':initData};
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'Ошибка');
  return data;
}
function mainView(view){return ['home','services','orders','profile'].includes(view)}
function updateNav(view){document.querySelectorAll('#bottomNav button').forEach(btn=>btn.classList.toggle('active',btn.dataset.view===view))}
function showView(view){
  document.querySelectorAll('.view').forEach(node=>node.classList.add('hidden'));
  const target=document.getElementById('view-'+view); if(!target) return;
  target.classList.remove('hidden');
  document.getElementById('bottomNav').classList.toggle('hidden',!mainView(view));
  if(mainView(view)) updateNav(view);
  if(view==='services') renderServices();
  if(view==='sitters') renderSitters();
  if(view==='profile') loadProfile();
  if(view==='pets') loadPets();
  if(view==='orders') loadOrders();
  if(view==='reviews') renderReviews();
  if(view==='chat') renderMessages();
  if(view==='executor') loadExecutor();
  window.scrollTo({top:0,behavior:'instant'});
}
function completeOnboarding(){localStorage.setItem('dh_onboarded_v6','1');showView('home')}
function hydratePhotos(){
  const onboarding=document.querySelector('.onboarding>img'); if(onboarding) onboarding.src=PHOTO.woman;
  const hero=document.querySelector('.hero-photo'); if(hero) hero.src=PHOTO.woman;
  const tile=document.querySelector('.tile.wide img'); if(tile) tile.src=PHOTO.dog;
  const pet=document.querySelector('.pet-pick img'); if(pet) pet.src=PHOTO.dog;
  const chat=document.querySelector('.chat-head img'); if(chat) chat.src=PHOTO.woman;
  const report=document.querySelectorAll('.report-photos img'); report.forEach((img,i)=>img.src=i===1?PHOTO.cat:PHOTO.dog);
}
async function boot(){
  hydratePhotos();
  const me=await api('/api/me');
  document.getElementById('profileName').textContent=me.first_name||me.username||'Пользователь';
  const savedCity=localStorage.getItem('dh_city'); if(savedCity) document.getElementById('cityLabel').textContent=savedCity;
  if(localStorage.getItem('dh_onboarded_v6')) showView('home'); else showView('onboarding');
}

async function renderServices(filter='all'){
  const items=await api('/api/catalog');
  const rows=filter==='all'?items:items.filter(x=>serviceCategories[x.id]===filter);
  const target=document.getElementById('serviceList');
  target.innerHTML=rows.map(x=>`<div class="service" onclick="openBooking(${x.id})"><img class="service-thumb" src="${servicePhotos[x.id]||PHOTO.dog}" alt="${x.name}"><div><div class="service-name">${x.name}</div><div class="service-desc">${x.desc}</div></div><div class="service-go"><div><div class="service-price">От ${x.price} ₽</div></div><i class="fa-solid fa-chevron-right"></i></div></div>`).join('') || '<div class="notice">В этой категории пока нет услуг</div>';
}
function filterServices(filter,el){document.querySelectorAll('#serviceFilters .pill').forEach(x=>x.classList.remove('active'));el.classList.add('active');renderServices(filter)}

function renderSitters(){
  const q=(document.getElementById('sitterSearch')?.value||'').toLowerCase().trim();
  let rows=sitters.filter(s=>`${s.name} ${s.area}`.toLowerCase().includes(q));
  if(sitterSort==='rating') rows.sort((a,b)=>b.rating-a.rating);
  if(sitterSort==='price') rows.sort((a,b)=>a.price-b.price);
  if(sitterSort==='near') rows.sort((a,b)=>a.distance-b.distance);
  if(sitterSort==='free') rows=rows.filter(s=>s.free);
  document.getElementById('sitterList').innerHTML=rows.map(s=>`<div class="sitter" onclick="openSitter(${s.id})"><div class="sitter-top"><img class="sitter-avatar" src="${s.image}"><div><div class="sitter-name">${s.name}</div><div class="rating"><i class="fa-solid fa-star"></i><span>${s.rating.toFixed(1)} (${s.reviews})</span></div><div class="sitter-meta">Выгул · Передержка</div><div class="sitter-meta">Суботица, ${s.area}</div></div><div><i class="${isFavorite(s.id)?'fa-solid':'fa-regular'} fa-heart heart" onclick="event.stopPropagation();toggleFavorite(${s.id});renderSitters()"></i><div class="sitter-meta" style="margin-top:17px">${s.distance} км</div></div></div><div class="sitter-gallery">${s.pets.map(p=>`<img src="${p}">`).join('')}</div></div>`).join('') || '<div class="notice">Ничего не найдено</div>';
}
function sortSitters(sort,el){sitterSort=sort;document.querySelectorAll('#sitterFilters .pill').forEach(x=>x.classList.remove('active'));el.classList.add('active');renderSitters()}
function openSitter(id){
  selectedSitterId=id; const s=sitters.find(x=>x.id===id);
  document.getElementById('sitterFavoriteIcon').className=`${isFavorite(id)?'fa-solid':'fa-regular'} fa-heart`;
  document.getElementById('sitterProfile').innerHTML=`<div class="sitter-cover"><img src="${s.image}"><div class="sitter-cover-copy"><div class="sitter-cover-name">${s.name}</div><div class="rating"><i class="fa-solid fa-star"></i><span>${s.rating.toFixed(1)} (${s.reviews} отзывов)</span></div><div class="sitter-stats"><span>Опыт: ${s.exp}</span><span>Выгулено собак: ${s.walks}</span></div></div></div><div class="about"><h3>Обо мне</h3><p>${s.about}</p></div><div class="mini-features"><div class="mini-feature"><i class="fa-solid fa-camera"></i><span>Фотоотчёт</span></div><div class="mini-feature"><i class="fa-regular fa-clock"></i><span>30 / 60 / 90 мин</span></div><div class="mini-feature"><i class="fa-solid fa-location-dot"></i><span>${s.area}</span></div></div><button class="btn btn-gold btn-wide" style="margin-top:9px" onclick="openBooking(1)">Забронировать прогулку</button><button class="btn btn-dark btn-wide" style="margin-top:7px" onclick="showView('reviews')">Отзывы</button>`;
  showView('sitter');
}
function favorites(){try{return JSON.parse(localStorage.getItem('dh_favorites')||'[]')}catch(_){return[]}}
function isFavorite(id){return favorites().includes(id)}
function toggleFavorite(id){const list=favorites();const next=list.includes(id)?list.filter(x=>x!==id):[...list,id];localStorage.setItem('dh_favorites',JSON.stringify(next));showToast(next.includes(id)?'Добавлено в избранное':'Удалено из избранного')}
function toggleFavoriteSelected(){toggleFavorite(selectedSitterId);document.getElementById('sitterFavoriteIcon').className=`${isFavorite(selectedSitterId)?'fa-solid':'fa-regular'} fa-heart`}
function showFavorites(){showView('sitters');setTimeout(()=>{const fav=favorites();document.getElementById('sitterList').innerHTML=sitters.filter(s=>fav.includes(s.id)).map(s=>`<div class="sitter" onclick="openSitter(${s.id})"><div class="sitter-top"><img class="sitter-avatar" src="${s.image}"><div><div class="sitter-name">${s.name}</div><div class="rating"><i class="fa-solid fa-star"></i><span>${s.rating.toFixed(1)} (${s.reviews})</span></div><div class="sitter-meta">Суботица, ${s.area}</div></div><i class="fa-solid fa-heart heart"></i></div></div>`).join('')||'<div class="notice">Вы ещё никого не добавили в избранное</div>'},0)}

function openBooking(id){selectedService=id;showView('booking');document.querySelectorAll('#bookingTypes .booking-type').forEach(x=>x.classList.toggle('active',Number(x.dataset.id)===Math.min(id,3)))}
function selectBookingType(id,el){selectedService=id;document.querySelectorAll('#bookingTypes .booking-type').forEach(x=>x.classList.remove('active'));el.classList.add('active')}
function selectChoice(el){el.parentElement.querySelectorAll('.choice').forEach(x=>x.classList.remove('active'));el.classList.add('active')}
async function submitBooking(){await api('/api/orders',{method:'POST',body:JSON.stringify({item_id:selectedService})});tg?.HapticFeedback?.notificationOccurred('success');showToast('Заказ создан');showView('orders')}

async function loadProfile(){const [pets,orders]=await Promise.all([api('/api/pets'),api('/api/orders')]);document.getElementById('statPets').textContent=pets.length;document.getElementById('statOrders').textContent=orders.length}
async function loadPets(){
  const pets=await api('/api/pets'); const target=document.getElementById('petsList');
  if(!pets.length){target.innerHTML='<div class="notice">Питомцы пока не добавлены</div>';return}
  const pics=[PHOTO.dog,PHOTO.cat,PHOTO.dog];
  target.innerHTML=pets.map((p,i)=>`<button class="pet-card" onclick="showToast('Выбран питомец: ${escapeHtml(p.name)}')"><img src="${pics[i%3]}"><span><b>${escapeHtml(p.name)}</b><small>${escapeHtml(p.breed||'Порода не указана')}</small></span><i class="fa-solid fa-chevron-right"></i></button>`).join('');
}
function openPetsFromBooking(){petsReturnView='booking';showView('pets')}
function goBackFromPets(){showView(petsReturnView||'profile');petsReturnView='profile'}
function openPetSheet(){document.getElementById('petSheet').classList.remove('hidden')}
function closePetSheet(e){if(!e||e.target===document.getElementById('petSheet'))document.getElementById('petSheet').classList.add('hidden')}
async function savePet(){const name=document.getElementById('petName').value.trim(),breed=document.getElementById('petBreed').value.trim();if(!name){showToast('Введите имя питомца');return}await api('/api/pets',{method:'POST',body:JSON.stringify({name,breed})});document.getElementById('petName').value='';document.getElementById('petBreed').value='';closePetSheet();showToast('Питомец добавлен');loadPets()}

function setOrderTab(tab){orderTab=tab;document.getElementById('segCurrent').classList.toggle('active',tab==='current');document.getElementById('segHistory').classList.toggle('active',tab==='history');document.getElementById('segCancelled').classList.toggle('active',tab==='cancelled');loadOrders()}
async function loadOrders(){
  const orders=await api('/api/orders');
  const rows=orderTab==='current'?orders.filter(o=>o.status!=='done'&&o.status!=='cancelled'):orderTab==='history'?orders.filter(o=>o.status==='done'):orders.filter(o=>o.status==='cancelled');
  const target=document.getElementById('ordersList');
  if(!rows.length){target.innerHTML='<div class="notice">В этом разделе пока пусто</div>';return}
  target.innerHTML=rows.map((o,i)=>`<div class="order"><div class="order-head"><div><h3>${escapeHtml(o.item_name)}</h3><div class="order-meta">Сегодня, 15:00 · 1 час<br>Ул. Корзо, 12 · Бублик</div></div><div class="status ${o.status==='done'?'green':''}">${o.status==='done'?'Подтверждён':o.status==='in_progress'?'В процессе':o.status==='accepted'?'Назначен':'Ищем ситтера'}</div></div><div class="order-actions"><button class="btn btn-dark btn-small" onclick="showView('chat')">Чат</button><button class="btn btn-dark btn-small" onclick="showView('${i===0?'report':'booking'}')">Детали</button></div></div>`).join('');
}
function renderMessages(){document.getElementById('messages').innerHTML='<div class="msg left">Здравствуйте. Я уже рядом, через пять минут буду у вас.<time>13:32</time></div><div class="msg right">Отлично, спасибо. Бублик уже ждёт.<time>13:33</time></div>'}
function sendMessage(){const input=document.getElementById('chatInput'),text=input.value.trim();if(!text)return;document.getElementById('messages').insertAdjacentHTML('beforeend',`<div class="msg right">${escapeHtml(text)}<time>сейчас</time></div>`);input.value='';tg?.HapticFeedback?.impactOccurred('light')}
function toggleVoice(el){const icon=el.querySelector('i');icon.classList.toggle('fa-play');icon.classList.toggle('fa-pause');showToast(icon.classList.contains('fa-pause')?'Воспроизведение':'Пауза')}
function renderReviews(){document.getElementById('reviewList').innerHTML=reviews.map(r=>`<div class="review"><div class="review-person"><img src="${r.image}"><div><b>${r.name}</b><small>${r.date}</small><div class="review-stars"><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i></div></div></div><div class="review-text">${r.text}</div><div class="review-gallery"><img src="${PHOTO.dog}"><img src="${PHOTO.cat}"><img src="${PHOTO.dog}"></div></div>`).join('')}

function setExecutorTab(tab){executorTab=tab;document.getElementById('execAvailable').classList.toggle('active',tab==='available');document.getElementById('execMine').classList.toggle('active',tab==='mine');loadExecutor()}
async function loadExecutor(){
  const rows=await api('/api/executor/orders'); const filtered=executorTab==='available'?rows.filter(o=>o.status==='open'):rows.filter(o=>o.status!=='open'); const target=document.getElementById('executorList');
  if(!filtered.length){target.innerHTML='<div class="notice">Заявок пока нет</div>';return}
  target.innerHTML=filtered.map(o=>`<div class="executor"><div class="executor-top"><div><b>${escapeHtml(o.item_name)}</b><div class="executor-meta">${escapeHtml(o.customer_name||'Клиент')}<br>${escapeHtml(o.customer_contact||'Контакт скрыт')}</div></div><div class="executor-price">${o.price} ₽</div></div>${o.status==='open'?`<button class="btn btn-gold" onclick="acceptOrder(${o.id})">Взять заявку</button>`:o.status==='accepted'?`<button class="btn btn-gold" onclick="updateStatus(${o.id},'in_progress')">Начать</button>`:o.status==='in_progress'?`<button class="btn btn-gold" onclick="updateStatus(${o.id},'done')">Завершить</button>`:'<div class="status green" style="margin-top:9px;width:max-content">Завершён</div>'}</div>`).join('');
}
async function acceptOrder(id){await api(`/api/executor/orders/${id}/accept`,{method:'POST'});showToast('Заявка принята');setExecutorTab('mine')}
async function updateStatus(id,status){await api(`/api/executor/orders/${id}/status`,{method:'POST',body:JSON.stringify({status})});showToast(status==='done'?'Заказ завершён':'Заказ начат');loadExecutor()}

function openSimple(type){
  simpleReturnView=document.getElementById('view-home').classList.contains('hidden')?'profile':'home';
  const title=document.getElementById('simpleTitle'),content=document.getElementById('simpleContent');
  const templates={
    location:['Город',`<div class="simple-list"><button class="simple-row location-option ${city()==='Суботица'?'active':''}" onclick="setCity('Суботица',this)"><i class="fa-solid fa-location-dot"></i><span class="grow"><b>Суботица</b><small>Основная зона работы</small></span><i class="fa-solid fa-chevron-right"></i></button><button class="simple-row location-option ${city()==='Баймок'?'active':''}" onclick="setCity('Баймок',this)"><i class="fa-solid fa-location-dot"></i><span class="grow"><b>Баймок</b><small>Выезд по записи</small></span><i class="fa-solid fa-chevron-right"></i></button></div>`],
    notifications:['Уведомления',toggleTemplate('Новые заказы','order_notif','fa-rectangle-list')+toggleTemplate('Сообщения ситтера','chat_notif','fa-comment')+toggleTemplate('Фотоотчёты','report_notif','fa-camera')],
    settings:['Настройки',toggleTemplate('Тактильный отклик','haptics','fa-wave-square')+toggleTemplate('Автооткрытие главной','auto_home','fa-house')+`<button class="simple-row" onclick="resetOnboarding()"><i class="fa-solid fa-rotate-left"></i><span class="grow"><b>Показать приветственный экран снова</b><small>Сбросить только onboarding</small></span><i class="fa-solid fa-chevron-right"></i></button>`],
    payments:['Способы оплаты',`<div class="simple-list"><button class="simple-row ${payment()==='telegram'?'payment-selected':''}" onclick="setPayment('telegram')"><i class="fa-brands fa-telegram"></i><span class="grow"><b>Telegram</b><small>Оплата внутри приложения</small></span><i class="fa-solid fa-check"></i></button><button class="simple-row ${payment()==='card'?'payment-selected':''}" onclick="setPayment('card')"><i class="fa-regular fa-credit-card"></i><span class="grow"><b>Банковская карта</b><small>Тестовый способ оплаты</small></span><i class="fa-solid fa-check"></i></button><button class="simple-row" onclick="showToast('В тестовой версии реальные карты не сохраняются')"><i class="fa-solid fa-plus"></i><span class="grow"><b>Добавить карту</b><small>Доступно после подключения боевого эквайринга</small></span><i class="fa-solid fa-chevron-right"></i></button></div>`],
    help:['Помощь',faqTemplate('Как оформить заказ?','Откройте услуги, выберите нужную услугу, дату, время и питомца, затем нажмите «Найти догситтера».')+faqTemplate('Как связаться с ситтером?','После назначения исполнителя в карточке заказа появляется кнопка «Чат».')+faqTemplate('Где смотреть фотоотчёт?','В текущем или завершённом заказе откройте «Детали».')],
    about:['О приложении',`<div class="simple-card"><h3>Dog's Happiness</h3><p>Тестовая Telegram Mini App для выгула, передержки и ухода за питомцами. Версия premium UI 2026.</p></div><div class="simple-card"><h3>Статус</h3><p>Работает отдельным тестовым стендом и не затрагивает боевого бота.</p></div>`],
    referral:['Пригласить друга',`<div class="simple-card"><h3>Получите 500 ₽</h3><p>Отправьте код другу. В тестовой версии награда отображается как демонстрация механики.</p><div class="referral-code"><input id="refCode" value="DOGS500" readonly><button onclick="copyReferral()">Копировать</button></div></div><button class="simple-row" onclick="shareReferral()"><i class="fa-solid fa-share-nodes"></i><span class="grow"><b>Поделиться</b><small>Открыть системное меню отправки</small></span><i class="fa-solid fa-chevron-right"></i></button>`],
    safety:['Безопасность',`<div class="simple-card"><h3>Проверка исполнителей</h3><p>Анкета исполнителя проходит модерацию перед доступом к заявкам.</p></div><div class="simple-card"><h3>Контроль заказа</h3><p>Статусы «назначен», «в процессе» и «завершён» видны в приложении.</p></div><div class="simple-card"><h3>Отчёты</h3><p>После услуги пользователь получает фотографии и детали прогулки.</p></div>`],
    care:['Наш подход',`<div class="simple-card"><h3>Индивидуально</h3><p>Вы выбираете услугу, питомца, продолжительность и дополнительные условия.</p></div><button class="btn btn-gold btn-wide" onclick="showView('services')">Выбрать услугу</button>`],
    premium:['Premium сервис',`<div class="simple-card"><h3>Приоритетный подбор</h3><p>Проверенные исполнители, удобный чат, история заказов и фотоотчёты в одном интерфейсе.</p></div><button class="btn btn-gold btn-wide" onclick="showView('services')">Перейти к услугам</button>`]
  };
  const tpl=templates[type]||['Раздел','<div class="notice">Раздел готовится</div>'];title.textContent=tpl[0];content.innerHTML=tpl[1];showView('simple');
}
function simpleBack(){showView(simpleReturnView||'profile')}
function toggleTemplate(label,key,icon){const on=localStorage.getItem('dh_'+key)!=='0';return `<button class="simple-row" onclick="toggleSetting('${key}',this)"><i class="fa-solid ${icon}"></i><span class="grow"><b>${label}</b><small>${on?'Включено':'Выключено'}</small></span><span class="switch ${on?'on':''}"></span></button>`}
function toggleSetting(key,row){const current=localStorage.getItem('dh_'+key)!=='0';localStorage.setItem('dh_'+key,current?'0':'1');const sw=row.querySelector('.switch'),small=row.querySelector('small');sw.classList.toggle('on',!current);small.textContent=!current?'Включено':'Выключено';if(key==='haptics'&&!current)tg?.HapticFeedback?.impactOccurred('light')}
function faqTemplate(q,a){return `<div class="simple-card"><button class="simple-row" style="border:0;padding:0;min-height:36px" onclick="this.parentElement.querySelector('.faq-answer').classList.toggle('hidden')"><i class="fa-regular fa-circle-question"></i><span class="grow"><b>${q}</b></span><i class="fa-solid fa-chevron-down"></i></button><div class="faq-answer hidden">${a}</div></div>`}
function city(){return localStorage.getItem('dh_city')||'Суботица'}
function setCity(name,el){localStorage.setItem('dh_city',name);document.getElementById('cityLabel').textContent=name;document.querySelectorAll('.location-option').forEach(x=>x.classList.remove('active'));el.classList.add('active');showToast('Город изменён')}
function payment(){return localStorage.getItem('dh_payment')||'telegram'}
function setPayment(value){localStorage.setItem('dh_payment',value);openSimple('payments');showToast('Способ оплаты выбран')}
function resetOnboarding(){localStorage.removeItem('dh_onboarded_v6');showView('onboarding')}
async function copyReferral(){const code=document.getElementById('refCode').value;await navigator.clipboard?.writeText(code);showToast('Код скопирован')}
async function shareReferral(){const text="Dog's Happiness, код DOGS500";if(navigator.share){await navigator.share({text})}else{await navigator.clipboard?.writeText(text);showToast('Текст скопирован')}}
function openPhoto(src){document.getElementById('photoViewerImage').src=src;document.getElementById('photoViewer').classList.remove('hidden')}
function closePhoto(){document.getElementById('photoViewer').classList.add('hidden')}
let toastTimer;function showToast(text){const el=document.getElementById('toast');el.textContent=text;el.classList.remove('hidden');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.add('hidden'),1800)}
function escapeHtml(value){return String(value??'').replace(/[&<>'\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}

boot().catch(err=>document.body.insertAdjacentHTML('afterbegin',`<div class="notice" style="margin:12px">${escapeHtml(err.message)}</div>`));