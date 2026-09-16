const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();
try { tg?.setHeaderColor('#050505'); tg?.setBackgroundColor('#050505'); } catch (_) {}

const initData = tg?.initData || '';
const sitters = [
  {id:1,name:'Алина',rating:'5.0',reviews:124,exp:'3 года',area:'Центр',distance:'1.2 км',image:'asset-1.webp',walks:'280+',about:'Люблю собак и умею находить к ним подход. Всегда на связи и после каждой услуги отправляю подробный отчёт.'},
  {id:2,name:'Екатерина',rating:'4.9',reviews:98,exp:'4 года',area:'Прозивка',distance:'2.1 км',image:'asset-2.webp',walks:'320+',about:'Работаю с активными собаками, люблю длинные маршруты и спокойную коммуникацию с хозяином.'},
  {id:3,name:'Мария',rating:'5.0',reviews:76,exp:'5 лет',area:'Mali Bajmok',distance:'2.8 км',image:'asset-3.webp',walks:'410+',about:'Домашняя передержка, визиты и спокойный уход без клеток. Подходит для тревожных питомцев.'},
];
const reviews = [
  {name:'Мария',date:'12 сентября 2026',text:'Очень внимательная работа. После прогулки сразу получила подробный отчёт и фотографии.',image:'asset-1.webp'},
  {name:'Иван',date:'5 сентября 2026',text:'Питомец вернулся спокойный и довольный. Удобный сервис, понятный статус заказа и хороший отчёт.',image:'asset-2.webp'},
];
let selectedService = 1;
let orderTab = 'current';
let executorTab = 'available';

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
  document.getElementById('view-'+view).classList.remove('hidden');
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
function completeOnboarding(){localStorage.setItem('dh_onboarded_v4','1');showView('home')}
async function boot(){
  const me=await api('/api/me');
  document.getElementById('profileName').textContent=me.first_name||me.username||'Пользователь';
  if(localStorage.getItem('dh_onboarded_v4')) showView('home'); else showView('onboarding');
}
async function renderServices(){
  const items=await api('/api/catalog');
  document.getElementById('serviceList').innerHTML=items.map(x=>`<div class="service" onclick="openBooking(${x.id})"><img class="service-thumb" src="/assets/${x.image}"><div><div class="service-name">${x.name}</div><div class="service-desc">${x.desc}</div></div><div class="service-go"><div><div class="service-price">От ${x.price} ₽</div></div><i class="fa-solid fa-chevron-right"></i></div></div>`).join('');
}
function renderSitters(){
  document.getElementById('sitterList').innerHTML=sitters.map(s=>`<div class="sitter" onclick="openSitter(${s.id})"><div class="sitter-top"><img class="sitter-avatar" src="/assets/${s.image}"><div><div class="sitter-name">${s.name}</div><div class="rating"><i class="fa-solid fa-star"></i><span>${s.rating} (${s.reviews})</span></div><div class="sitter-meta">Выгул · Передержка</div><div class="sitter-meta">Суботица, ${s.area}</div></div><div><i class="fa-regular fa-heart heart"></i><div class="sitter-meta" style="margin-top:17px">${s.distance}</div></div></div><div class="sitter-gallery"><img src="/assets/asset-4.webp"><img src="/assets/asset-5.webp"><img src="/assets/pet-premium.webp"><img src="/assets/hero-dog.webp"></div></div>`).join('');
}
function openSitter(id){
  const s=sitters.find(x=>x.id===id);
  document.getElementById('sitterProfile').innerHTML=`<div class="sitter-cover"><img src="/assets/${s.image}"><div class="sitter-cover-copy"><div class="sitter-cover-name">${s.name}</div><div class="rating"><i class="fa-solid fa-star"></i><span>${s.rating} (${s.reviews} отзывов)</span></div><div class="sitter-stats"><span>Опыт: ${s.exp}</span><span>Выгулено собак: ${s.walks}</span></div></div></div><div class="about"><h3>Обо мне</h3><p>${s.about}</p></div><div class="mini-features"><div class="mini-feature"><i class="fa-solid fa-camera"></i><span>Фотоотчёт</span></div><div class="mini-feature"><i class="fa-regular fa-clock"></i><span>30 / 60 / 90 мин</span></div><div class="mini-feature"><i class="fa-solid fa-location-dot"></i><span>${s.area}</span></div></div><button class="btn btn-gold btn-wide" style="margin-top:9px" onclick="openBooking(1)">Забронировать прогулку</button><button class="btn btn-dark btn-wide" style="margin-top:7px" onclick="showView('reviews')">Отзывы</button>`;
  showView('sitter');
}
function openBooking(id){selectedService=id;showView('booking')}
async function submitBooking(){await api('/api/orders',{method:'POST',body:JSON.stringify({item_id:selectedService})});tg?.HapticFeedback?.notificationOccurred('success');showView('orders')}
async function loadProfile(){const [pets,orders]=await Promise.all([api('/api/pets'),api('/api/orders')]);document.getElementById('statPets').textContent=pets.length;document.getElementById('statOrders').textContent=orders.length}
async function loadPets(){
  const pets=await api('/api/pets'); const target=document.getElementById('petsList');
  if(!pets.length){target.innerHTML='<div class="notice">Питомцы пока не добавлены</div>';return}
  const pics=['asset-4.webp','asset-5.webp','pet-premium.webp'];
  target.innerHTML=pets.map((p,i)=>`<div class="pet-card"><img src="/assets/${pics[i%3]}"><div><b>${p.name}</b><small>${p.breed||'Порода не указана'}</small></div><i class="fa-solid fa-chevron-right"></i></div>`).join('');
}
function openPetSheet(){document.getElementById('petSheet').classList.remove('hidden')}
function closePetSheet(e){if(!e||e.target===document.getElementById('petSheet'))document.getElementById('petSheet').classList.add('hidden')}
async function savePet(){const name=document.getElementById('petName').value.trim(),breed=document.getElementById('petBreed').value.trim();if(!name)return;await api('/api/pets',{method:'POST',body:JSON.stringify({name,breed})});document.getElementById('petName').value='';document.getElementById('petBreed').value='';closePetSheet();loadPets()}
function setOrderTab(tab){orderTab=tab;document.getElementById('segCurrent').classList.toggle('active',tab==='current');document.getElementById('segHistory').classList.toggle('active',tab==='history');document.getElementById('segCancelled').classList.toggle('active',tab==='cancelled');loadOrders()}
async function loadOrders(){
  const orders=await api('/api/orders');
  const rows=orderTab==='current'?orders.filter(o=>o.status!=='done'&&o.status!=='cancelled'):orderTab==='history'?orders.filter(o=>o.status==='done'):orders.filter(o=>o.status==='cancelled');
  const target=document.getElementById('ordersList');
  if(!rows.length){target.innerHTML='<div class="notice">В этом разделе пока пусто</div>';return}
  target.innerHTML=rows.map((o,i)=>`<div class="order"><div class="order-head"><div><h3>${o.item_name}</h3><div class="order-meta">Сегодня, 15:00 · 1 час<br>Ул. Корзо, 12 · Бублик</div></div><div class="status ${o.status==='done'?'green':''}">${o.status==='done'?'Подтверждён':o.status==='in_progress'?'В процессе':o.status==='accepted'?'Назначен':'Ищем ситтера'}</div></div><div class="order-actions"><button class="btn btn-dark btn-small" onclick="showView('chat')">Чат</button><button class="btn btn-dark btn-small" onclick="showView('${i===0?'report':'booking'}')">Детали</button></div></div>`).join('');
}
function renderMessages(){document.getElementById('messages').innerHTML='<div class="msg left">Здравствуйте. Я уже рядом, через пять минут буду у вас.<time>13:32</time></div><div class="msg right">Отлично, спасибо. Бублик уже ждёт.<time>13:33</time></div>'}
function sendMessage(){const input=document.getElementById('chatInput'),text=input.value.trim();if(!text)return;document.getElementById('messages').insertAdjacentHTML('beforeend',`<div class="msg right">${text}<time>сейчас</time></div>`);input.value=''}
function renderReviews(){document.getElementById('reviewList').innerHTML=reviews.map(r=>`<div class="review"><div class="review-person"><img src="/assets/${r.image}"><div><b>${r.name}</b><small>${r.date}</small><div class="review-stars"><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i></div></div></div><div class="review-text">${r.text}</div><div class="review-gallery"><img src="/assets/asset-4.webp"><img src="/assets/asset-5.webp"><img src="/assets/pet-premium.webp"></div></div>`).join('')}
function setExecutorTab(tab){executorTab=tab;document.getElementById('execAvailable').classList.toggle('active',tab==='available');document.getElementById('execMine').classList.toggle('active',tab==='mine');loadExecutor()}
async function loadExecutor(){
  const rows=await api('/api/executor/orders'); const filtered=executorTab==='available'?rows.filter(o=>o.status==='open'):rows.filter(o=>o.status!=='open'); const target=document.getElementById('executorList');
  if(!filtered.length){target.innerHTML='<div class="notice">Заявок пока нет</div>';return}
  target.innerHTML=filtered.map(o=>`<div class="executor"><div class="executor-top"><div><b>${o.item_name}</b><div class="executor-meta">${o.customer_name||'Клиент'}<br>${o.customer_contact||'Контакт скрыт'}</div></div><div class="executor-price">${o.price} ₽</div></div>${o.status==='open'?`<button class="btn btn-gold" onclick="acceptOrder(${o.id})">Взять заявку</button>`:o.status==='accepted'?`<button class="btn btn-gold" onclick="updateStatus(${o.id},'in_progress')">Начать</button>`:o.status==='in_progress'?`<button class="btn btn-gold" onclick="updateStatus(${o.id},'done')">Завершить</button>`:'<div class="status green" style="margin-top:9px;width:max-content">Завершён</div>'}</div>`).join('');
}
async function acceptOrder(id){await api(`/api/executor/orders/${id}/accept`,{method:'POST'});setExecutorTab('mine')}
async function updateStatus(id,status){await api(`/api/executor/orders/${id}/status`,{method:'POST',body:JSON.stringify({status})});loadExecutor()}
boot().catch(err=>document.body.insertAdjacentHTML('afterbegin',`<div class="notice" style="margin:12px">${err.message}</div>`));
