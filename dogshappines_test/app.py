import json, hmac, hashlib, os, sqlite3, threading, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.getenv('PORT','3000'))
BOT_TOKEN = os.getenv('BOT_TOKEN','').strip()
MINI_APP_URL = os.getenv('MINI_APP_URL','').strip()
TEST_MODE = os.getenv('TEST_MODE','true').lower() == 'true'
DB = '/tmp/dogshappines_v2.sqlite3'
ASSET_DIR = Path(__file__).resolve().parent / 'assets'

CATALOG = [
    {'id':1,'name':'Выгул собак','price':700,'desc':'Индивидуальная прогулка, игры и отчёт','icon':'fa-dog','image':'icon-walk.webp'},
    {'id':2,'name':'Передержка','price':1200,'desc':'Домашняя передержка с заботой и связью','icon':'fa-house','image':'asset-5.webp'},
    {'id':3,'name':'Зооняня','price':800,'desc':'Визит на дом, кормление и уход','icon':'fa-hand-holding-heart','image':'asset-6.webp'},
    {'id':4,'name':'Кинолог','price':1500,'desc':'Индивидуальное занятие с питомцем','icon':'fa-graduation-cap','image':'asset-4.webp'},
]

SITTERS = [
    {'id':1,'name':'Алина','rating':'4.9','reviews':124,'exp':'3 года','area':'Центр','image':'asset-1.webp'},
    {'id':2,'name':'Екатерина','rating':'5.0','reviews':86,'exp':'4 года','area':'Петроградский','image':'asset-2.webp'},
    {'id':3,'name':'Мария','rating':'4.8','reviews':92,'exp':'2 года','area':'Василеостровский','image':'asset-3.webp'},
]

REVIEWS = [
    {'name':'Мария','rating':'5.0','text':'Очень аккуратно и спокойно. Собака быстро привыкла, после прогулки прислали фото и короткий отчёт.'},
    {'name':'Иван','rating':'5.0','text':'Удобно бронировать, ситтер пришёл вовремя. Для нас главное, что питомец был расслаблен.'},
    {'name':'Анна','rating':'4.9','text':'Понравилась связь в процессе и то, что все статусы видны в приложении.'},
]

HTML = r'''<!doctype html><html lang="ru"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no">
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
<title>Dog's Happiness</title>
<style>
:root{--bg:#050505;--surface:#0d0c0b;--surface2:#14110e;--surface3:#1b1712;--gold:#c99a55;--gold2:#efcd8f;--text:#f4ecdf;--muted:#a99880;--line:rgba(213,170,99,.2);--line2:rgba(213,170,99,.42);--shadow:0 20px 50px rgba(0,0,0,.5)}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}html,body{margin:0;background:radial-gradient(circle at 65% -10%,rgba(145,93,28,.19),transparent 29%),#050505;color:var(--text);font-family:Manrope,system-ui,sans-serif}body{min-height:100vh}button,input,textarea,select{font:inherit}button{cursor:pointer}#app{max-width:430px;margin:auto;padding:10px 12px calc(108px + env(safe-area-inset-bottom))}.hidden{display:none!important}
.top{height:62px;display:flex;align-items:center;justify-content:space-between}.brand{display:flex;align-items:center;gap:11px}.brand-logo{width:46px;height:46px;object-fit:cover;border-radius:15px;border:1px solid var(--line2);box-shadow:0 10px 28px #0009}.brand-name{font-family:'Cormorant Garamond',serif;font-weight:700;font-size:21px;line-height:1}.brand-sub{margin-top:4px;color:var(--muted);font-size:10px}.test-tag{height:28px;padding:0 10px;border-radius:999px;border:1px solid var(--line);display:flex;align-items:center;color:var(--gold2);font-size:9px;font-weight:800;letter-spacing:.18em;text-transform:uppercase}
.hero{position:relative;min-height:360px;overflow:hidden;border:1px solid var(--line);border-radius:30px;background:linear-gradient(120deg,#100d09 0%,#090909 52%,#070706 100%);box-shadow:var(--shadow)}.hero:before{content:'';position:absolute;inset:0;background:radial-gradient(circle at 78% 24%,rgba(216,169,93,.23),transparent 28%),linear-gradient(90deg,rgba(0,0,0,.02),rgba(0,0,0,.17));pointer-events:none}.hero-copy{position:relative;z-index:3;width:60%;padding:27px 0 24px 22px}.eyebrow{color:var(--gold2);font-size:10px;font-weight:800;letter-spacing:.2em;text-transform:uppercase}.hero-title{font-family:'Cormorant Garamond',serif;font-size:47px;line-height:.88;font-weight:600;letter-spacing:-.04em;margin:12px 0 12px}.hero-text{color:#cbbda7;font-size:11px;line-height:1.52;margin:0 0 18px}.hero-actions{display:flex;flex-direction:column;gap:8px;width:150px}.btn{border:0;border-radius:15px;min-height:44px;padding:0 14px;font-size:11px;font-weight:800}.btn-gold{background:linear-gradient(145deg,#b57e38,#e2b76a);color:#171108;box-shadow:0 12px 24px rgba(181,126,56,.18)}.btn-dark{background:rgba(255,255,255,.025);color:var(--text);border:1px solid var(--line)}.hero-dog{position:absolute;z-index:2;right:-26px;bottom:-4px;width:61%;height:93%;object-fit:cover;object-position:51% 48%;-webkit-mask-image:linear-gradient(to left,#000 80%,transparent 100%);mask-image:linear-gradient(to left,#000 80%,transparent 100%)}.hero-seal{position:absolute;right:15px;top:15px;z-index:4;width:38px;height:38px;border-radius:50%;border:1px solid var(--line);display:grid;place-items:center;color:var(--gold2);background:#080706bb}.hero-seal i{font-size:15px}
.story-nav{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:14px 0 15px}.story{text-align:center}.story button{width:100%;border:0;background:transparent;color:inherit;padding:0}.story-ring{aspect-ratio:1;border:1px solid var(--line2);border-radius:50%;display:grid;place-items:center;background:radial-gradient(circle at top,rgba(208,164,91,.16),rgba(255,255,255,.01));box-shadow:0 12px 22px #0008}.story-ring i{color:var(--gold2);font-size:18px}.story-label{margin-top:5px;color:#c6b69d;font-size:8px;white-space:nowrap}
.section-head{display:flex;align-items:end;justify-content:space-between;margin:18px 2px 10px}.section-title{font-family:'Cormorant Garamond',serif;font-size:30px;line-height:1;margin:0}.section-note{color:var(--gold2);font-size:8px;text-transform:uppercase;letter-spacing:.12em}.mosaic{display:grid;grid-template-columns:1fr 1fr;gap:8px}.tile{position:relative;min-height:164px;overflow:hidden;border:1px solid var(--line);border-radius:3px;background:linear-gradient(145deg,#0f0c09,#080706);box-shadow:var(--shadow)}.tile.wide{grid-column:1/-1;min-height:190px}.tile-img{position:absolute;right:0;bottom:0;width:58%;height:100%;object-fit:cover}.tile-img.fade{-webkit-mask-image:linear-gradient(to left,#000 72%,transparent 100%);mask-image:linear-gradient(to left,#000 72%,transparent 100%)}.tile-copy{position:absolute;z-index:3;left:14px;top:14px;right:14px;max-width:65%}.tile-kicker{font-family:'Cormorant Garamond',serif;color:var(--gold2);font-size:17px;line-height:.95;text-transform:uppercase}.tile-text{margin-top:7px;color:#a99880;font-size:9px;line-height:1.35}.tile-symbol{position:absolute;right:13px;bottom:13px;width:54px;height:54px;border-radius:50%;border:1px solid var(--line2);display:grid;place-items:center;background:#090807dd}.tile-symbol i{color:var(--gold2);font-size:22px}.quote-box{position:absolute;inset:50% auto auto 50%;transform:translate(-50%,-50%);width:76%;padding:18px 12px;border:1px solid var(--line2);background:#090807dc;text-align:center;font-family:'Cormorant Garamond',serif;color:var(--gold2);font-size:20px;line-height:1.05}
.trust-strip{display:grid;grid-template-columns:repeat(4,1fr);margin-top:8px;border:1px solid var(--line);background:#0b0a09}.trust-item{padding:12px 6px;text-align:center;border-right:1px solid var(--line)}.trust-item:last-child{border-right:0}.trust-item i{display:block;color:var(--gold2);font-size:18px;margin-bottom:7px}.trust-item span{color:#bdad94;font-size:8px;line-height:1.25}
.page-head{display:flex;align-items:center;gap:12px;margin:4px 0 14px}.back{width:40px;height:40px;border-radius:14px;border:1px solid var(--line);background:#0e0c0a;color:var(--gold2)}.page-title{font-family:'Cormorant Garamond',serif;font-size:30px;margin:0;line-height:1}.page-sub{color:var(--muted);font-size:10px;margin-top:4px}.cards{display:grid;gap:9px}.service{display:grid;grid-template-columns:68px minmax(0,1fr) auto;align-items:center;gap:11px;padding:10px;border:1px solid var(--line);border-radius:20px;background:#0e0d0c;box-shadow:0 13px 28px #0006}.service-thumb{width:68px;height:68px;border-radius:17px;overflow:hidden;border:1px solid var(--line)}.service-thumb img{width:100%;height:100%;object-fit:cover}.service-name{font-family:'Cormorant Garamond',serif;font-size:20px;font-weight:700;line-height:1}.service-desc{color:var(--muted);font-size:9px;line-height:1.35;margin-top:5px}.service-price{color:var(--gold2);font-size:12px;font-weight:800;text-align:right;margin-bottom:6px}.service-btn{height:36px;padding:0 12px;border:0;border-radius:12px;background:linear-gradient(145deg,#b57e38,#e2b76a);color:#171108;font-size:10px;font-weight:800}
.sitter{overflow:hidden;border:1px solid var(--line);border-radius:22px;background:#0d0c0b;box-shadow:var(--shadow)}.sitter-cover{height:196px;position:relative;overflow:hidden}.sitter-cover img{width:100%;height:100%;object-fit:cover}.sitter-cover:after{content:'';position:absolute;inset:auto 0 0;height:60%;background:linear-gradient(transparent,#0d0c0b)}.sitter-body{position:relative;margin-top:-40px;z-index:2;padding:0 14px 14px}.sitter-name{font-family:'Cormorant Garamond',serif;font-size:29px;font-weight:700}.sitter-meta{color:var(--gold2);font-size:10px;margin-top:4px}.sitter-text{color:var(--muted);font-size:10px;line-height:1.5;margin:10px 0 12px}.sitter-tags{display:flex;gap:6px;flex-wrap:wrap}.sitter-tag{height:28px;padding:0 9px;border-radius:999px;border:1px solid var(--line);display:flex;align-items:center;color:#c8b79e;font-size:9px}.sitter-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.mode{display:flex;gap:5px;padding:4px;border:1px solid var(--line);border-radius:17px;background:#0d0c0b;margin-bottom:10px}.mode button{flex:1;height:38px;border:0;border-radius:13px;background:transparent;color:var(--muted);font-size:10px;font-weight:800}.mode button.active{background:linear-gradient(145deg,#b57e38,#e2b76a);color:#171108}.order{padding:14px;border:1px solid var(--line);border-radius:20px;background:#0d0c0b;box-shadow:0 13px 28px #0006}.order-top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.order-name{font-family:'Cormorant Garamond',serif;font-size:21px;font-weight:700}.order-meta{margin-top:5px;color:var(--muted);font-size:9px}.status{display:inline-flex;height:28px;align-items:center;padding:0 9px;border-radius:999px;border:1px solid var(--line);color:var(--gold2);font-size:9px;font-weight:800}.order .btn{margin-top:10px;width:100%}.empty{padding:22px;border:1px dashed var(--line);border-radius:18px;color:var(--muted);text-align:center;font-size:11px}
.profile-main{padding:14px;border:1px solid var(--line);border-radius:22px;background:#0d0c0b;box-shadow:var(--shadow)}.profile-row{display:flex;align-items:center;gap:13px}.profile-avatar{width:88px;height:88px;border-radius:22px;border:1px solid var(--line2);overflow:hidden}.profile-avatar img{width:100%;height:100%;object-fit:cover}.profile-name{font-family:'Cormorant Garamond',serif;font-size:28px;font-weight:700;line-height:1}.profile-sub{color:var(--muted);font-size:10px;margin-top:5px}.stats{display:grid;grid-template-columns:repeat(3,1fr);margin-top:12px;border-top:1px solid var(--line);padding-top:12px}.stat{text-align:center}.stat b{display:block;color:var(--gold2);font-size:18px}.stat span{color:var(--muted);font-size:8px}.profile-block{margin-top:10px;padding:14px;border:1px solid var(--line);border-radius:22px;background:#0d0c0b}.profile-block h3{font-family:'Cormorant Garamond',serif;font-size:23px;margin:0 0 9px}.fields{display:grid;gap:7px}.field{height:46px;border-radius:14px;border:1px solid var(--line);background:#15120f;color:var(--text);padding:0 13px;font-size:11px;outline:none}.textarea{min-height:92px;padding:12px;resize:none}.pet-list{display:grid;gap:8px;margin-top:10px}.pet{display:flex;align-items:center;gap:10px;padding:9px;border:1px solid var(--line);background:#12100e;border-radius:16px}.pet-photo{width:50px;height:50px;border-radius:14px;overflow:hidden;border:1px solid var(--line)}.pet-photo img{width:100%;height:100%;object-fit:cover}.pet-name{font-weight:800;font-size:12px}.pet-breed{color:var(--muted);font-size:9px;margin-top:3px}
.booking-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.choice{min-height:70px;padding:10px;border:1px solid var(--line);border-radius:17px;background:#0e0d0c;color:var(--text);text-align:left}.choice.active{border-color:var(--gold);background:rgba(201,154,85,.09)}.choice i{display:block;color:var(--gold2);font-size:16px;margin-bottom:8px}.choice b{font-size:11px}.choice span{display:block;color:var(--muted);font-size:8px;margin-top:3px}.form-card{padding:14px;border:1px solid var(--line);border-radius:20px;background:#0d0c0b;margin-top:10px}.form-card label{display:block;color:#c3b197;font-size:9px;margin:10px 0 5px}.form-card label:first-child{margin-top:0}.submit{width:100%;margin-top:12px;min-height:48px;border:0;border-radius:16px;background:linear-gradient(145deg,#b57e38,#e2b76a);color:#171108;font-weight:800}
.review-summary{padding:20px;border:1px solid var(--line);border-radius:22px;background:#0d0c0b;text-align:center}.review-score{font-family:'Cormorant Garamond',serif;color:var(--gold2);font-size:58px;line-height:1}.review-stars{display:flex;justify-content:center;gap:4px;color:var(--gold2);font-size:14px;margin:6px 0}.review{padding:14px;border:1px solid var(--line);border-radius:20px;background:#0d0c0b}.review-top{display:flex;justify-content:space-between;gap:10px}.review-name{font-weight:800;font-size:12px}.review-rating{color:var(--gold2);font-size:11px}.review-text{color:#c5b59d;font-size:10px;line-height:1.55;margin-top:10px}.review-photos{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:10px}.review-photos img{width:100%;aspect-ratio:1;border-radius:10px;object-fit:cover;border:1px solid var(--line)}
.report-gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.report-gallery img{width:100%;aspect-ratio:1;border-radius:13px;object-fit:cover;border:1px solid var(--line)}.report-map{height:160px;margin-top:10px;border-radius:18px;border:1px solid var(--line);background:linear-gradient(145deg,#131313,#090909);position:relative;overflow:hidden}.report-map:before{content:'';position:absolute;inset:0;background:linear-gradient(24deg,transparent 48%,rgba(201,154,85,.35) 49%,rgba(201,154,85,.35) 51%,transparent 52%),linear-gradient(145deg,transparent 42%,rgba(95,137,98,.16) 43%,rgba(95,137,98,.16) 57%,transparent 58%)}.route-line{position:absolute;left:24px;right:36px;top:78px;height:2px;background:linear-gradient(90deg,#6ed38c,#c99a55);transform:rotate(-13deg)}.route-line:before,.route-line:after{content:'';position:absolute;top:-5px;width:12px;height:12px;border-radius:50%;background:var(--gold2)}.route-line:before{left:0;background:#6ed38c}.route-line:after{right:0}.report-stats{display:grid;grid-template-columns:repeat(3,1fr);margin-top:10px}.report-stat{text-align:center}.report-stat b{display:block;color:var(--gold2);font-size:14px}.report-stat span{color:var(--muted);font-size:8px}
.bottomnav{position:fixed;left:50%;transform:translateX(-50%);bottom:max(10px,env(safe-area-inset-bottom));width:calc(100% - 20px);max-width:430px;display:grid;grid-template-columns:repeat(4,1fr);gap:4px;padding:5px;border-radius:27px;border:1px solid var(--line);background:rgba(7,7,7,.95);backdrop-filter:blur(20px);box-shadow:0 18px 42px #000b}.bottomnav button{min-height:62px;border:0;border-radius:19px;background:transparent;color:#87755a;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px}.bottomnav button i{font-size:18px}.bottomnav button span{font-size:9px}.bottomnav button.active{background:rgba(201,154,85,.14);color:var(--gold2)}
@media(max-width:370px){.hero-title{font-size:42px}.hero-dog{width:65%}.story-label{font-size:7px}.service{grid-template-columns:58px minmax(0,1fr)}.service>div:last-child{grid-column:1/-1;display:flex;align-items:center;justify-content:space-between}.service-price{margin:0}.service-thumb{width:58px;height:58px}}
</style></head><body><div id="app">
<header class="top"><div class="brand"><img class="brand-logo" src="/assets/brand-icon.webp"><div><div id="uname" class="brand-name">Dog's Happiness</div><div class="brand-sub">премиальный pet care</div></div></div><div class="test-tag">test</div></header>
<main>
<section id="view-home" class="view">
<div class="hero"><div class="hero-copy"><div class="eyebrow">premium pet care</div><h1 class="hero-title">Забота,<br>которой<br>можно<br>доверять</h1><p class="hero-text">Выгул, передержка и уход за питомцем в одном приложении.</p><div class="hero-actions"><button class="btn btn-gold" onclick="showView('catalog')">Выбрать услугу</button><button class="btn btn-dark" onclick="showView('orders')">Мои заказы</button></div></div><img class="hero-dog" src="/assets/hero-dog.webp"><div class="hero-seal"><i class="fa-solid fa-paw"></i></div></div>
<div class="story-nav">
<div class="story"><button onclick="showView('reviews')"><div class="story-ring"><i class="fa-regular fa-heart"></i></div><div class="story-label">Отзывы</div></button></div>
<div class="story"><button onclick="showView('catalog')"><div class="story-ring"><i class="fa-solid fa-dog"></i></div><div class="story-label">Услуги</div></button></div>
<div class="story"><button onclick="showView('sitters')"><div class="story-ring"><i class="fa-regular fa-user"></i></div><div class="story-label">Ситтеры</div></button></div>
<div class="story"><button onclick="showView('report')"><div class="story-ring"><i class="fa-solid fa-camera"></i></div><div class="story-label">Отчёт</div></button></div>
<div class="story"><button onclick="showView('profile')"><div class="story-ring"><i class="fa-solid fa-location-dot"></i></div><div class="story-label">Профиль</div></button></div>
</div>
<div class="section-head"><h2 class="section-title">Сервис</h2><span class="section-note">всё в одном месте</span></div>
<div class="mosaic">
<article class="tile wide"><div class="tile-copy"><div class="tile-kicker">индивидуальный<br>подход</div><div class="tile-text">Подбираем специалиста под характер питомца и ваши задачи.</div></div><img class="tile-img fade" src="/assets/asset-2.webp"></article>
<article class="tile"><div class="tile-copy"><div class="tile-kicker">больше,<br>чем прогулка</div><div class="tile-text">Активность, игры и внимание.</div></div><img class="tile-img fade" src="/assets/asset-5.webp"></article>
<article class="tile"><div class="tile-copy"><div class="tile-kicker">безопасность<br>прежде всего</div><div class="tile-text">Статусы и контроль в приложении.</div></div><div class="tile-symbol"><i class="fa-solid fa-shield-dog"></i></div></article>
<article class="tile"><div class="quote-box">Доверьте нам самого дорогого</div></article>
<article class="tile"><div class="tile-copy"><div class="tile-kicker">фото и видео<br>отчёты</div><div class="tile-text">После каждой услуги.</div></div><div class="tile-symbol"><i class="fa-solid fa-camera"></i></div></article>
</div>
<div class="trust-strip"><div class="trust-item"><i class="fa-solid fa-user-check"></i><span>Проверенные<br>ситтеры</span></div><div class="trust-item"><i class="fa-solid fa-shield-halved"></i><span>Безопасность<br>и забота</span></div><div class="trust-item"><i class="fa-solid fa-camera-retro"></i><span>Фото и видео<br>отчёты</span></div><div class="trust-item"><i class="fa-solid fa-crown"></i><span>Премиальный<br>сервис</span></div></div>
</section>

<section id="view-catalog" class="view hidden"><div class="page-head"><button class="back" onclick="showView('home')"><i class="fa-solid fa-chevron-left"></i></button><div><h2 class="page-title">Услуги</h2><div class="page-sub">Выберите формат ухода</div></div></div><div id="catalogList" class="cards"></div></section>
<section id="view-sitters" class="view hidden"><div class="page-head"><button class="back" onclick="showView('home')"><i class="fa-solid fa-chevron-left"></i></button><div><h2 class="page-title">Догситтеры</h2><div class="page-sub">Проверенные исполнители рядом</div></div></div><div id="sittersList" class="cards"></div></section>
<section id="view-booking" class="view hidden"><div class="page-head"><button class="back" onclick="showView('catalog')"><i class="fa-solid fa-chevron-left"></i></button><div><h2 class="page-title">Новый заказ</h2><div id="bookingService" class="page-sub"></div></div></div><div class="booking-grid"><button class="choice active" onclick="setDuration(this,'30 мин')"><i class="fa-regular fa-clock"></i><b>30 минут</b><span>короткая прогулка</span></button><button class="choice" onclick="setDuration(this,'1 час')"><i class="fa-regular fa-clock"></i><b>1 час</b><span>стандартный формат</span></button><button class="choice" onclick="setDuration(this,'2 часа')"><i class="fa-solid fa-stopwatch"></i><b>2 часа</b><span>длительный визит</span></button><button class="choice" onclick="setDuration(this,'Другое')"><i class="fa-solid fa-sliders"></i><b>Другое</b><span>согласуем отдельно</span></button></div><div class="form-card"><label>Дата</label><input id="bookingDate" class="field" type="date"><label>Время</label><input id="bookingTime" class="field" type="time"><label>Адрес</label><input id="bookingAddress" class="field" placeholder="Улица, дом"><label>Комментарий</label><textarea id="bookingNote" class="field textarea" placeholder="Что важно знать о питомце"></textarea><button class="submit" onclick="submitBooking()">Найти догситтера</button></div></section>
<section id="view-orders" class="view hidden"><div class="page-head"><button class="back" onclick="showView('home')"><i class="fa-solid fa-chevron-left"></i></button><div><h2 class="page-title">Заказы</h2><div class="page-sub">Текущие и завершённые</div></div></div><div class="mode"><button id="modeCustomer" class="active" onclick="setMode('customer')">Мои</button><button id="modeExecutor" onclick="setMode('executor')">Исполнитель</button></div><div id="ordersList" class="cards"></div></section>
<section id="view-profile" class="view hidden"><div class="page-head"><button class="back" onclick="showView('home')"><i class="fa-solid fa-chevron-left"></i></button><div><h2 class="page-title">Профиль</h2><div class="page-sub">Питомцы и настройки</div></div></div><div class="profile-main"><div class="profile-row"><div class="profile-avatar"><img src="/assets/asset-1.webp"></div><div><div id="profileName" class="profile-name">Пользователь</div><div id="profileUser" class="profile-sub"></div></div></div><div class="stats"><div class="stat"><b id="petCount">0</b><span>Питомца</span></div><div class="stat"><b id="orderCount">0</b><span>Заказов</span></div><div class="stat"><b>5.0</b><span>Рейтинг</span></div></div></div><div class="profile-block"><h3>Мои питомцы</h3><div class="fields"><input id="petName" class="field" placeholder="Имя питомца"><input id="petBreed" class="field" placeholder="Порода"><button class="btn btn-gold" onclick="addPet()">Добавить питомца</button></div><div id="petsList" class="pet-list"></div></div></section>
<section id="view-reviews" class="view hidden"><div class="page-head"><button class="back" onclick="showView('home')"><i class="fa-solid fa-chevron-left"></i></button><div><h2 class="page-title">Отзывы</h2><div class="page-sub">Что говорят владельцы</div></div></div><div class="review-summary"><div class="review-score">4.9</div><div class="review-stars"><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i></div><div class="page-sub">На основе 124 отзывов</div></div><div id="reviewsList" class="cards" style="margin-top:10px"></div></section>
<section id="view-report" class="view hidden"><div class="page-head"><button class="back" onclick="showView('home')"><i class="fa-solid fa-chevron-left"></i></button><div><h2 class="page-title">Фотоотчёт</h2><div class="page-sub">Последняя прогулка</div></div></div><div class="form-card"><div class="report-gallery"><img src="/assets/asset-5.webp"><img src="/assets/asset-6.webp"><img src="/assets/pet-premium.webp"></div><div class="report-map"><div class="route-line"></div></div><div class="report-stats"><div class="report-stat"><b>1.2 км</b><span>маршрут</span></div><div class="report-stat"><b>58 мин</b><span>время</span></div><div class="report-stat"><b>3 фото</b><span>отчёт</span></div></div></div></section>
</main></div>
<nav class="bottomnav"><button data-view="home" class="active" onclick="showView('home')"><i class="fa-regular fa-house"></i><span>Главная</span></button><button data-view="catalog" onclick="showView('catalog')"><i class="fa-solid fa-paw"></i><span>Услуги</span></button><button data-view="orders" onclick="showView('orders')"><i class="fa-regular fa-rectangle-list"></i><span>Заказы</span></button><button data-view="profile" onclick="showView('profile')"><i class="fa-regular fa-user"></i><span>Профиль</span></button></nav>
<script>
const tg=window.Telegram?.WebApp;tg?.ready();tg?.expand();const initData=tg?.initData||'';let mode='customer';let selectedService=null;let selectedDuration='30 мин';
async function api(path,options={}){options.headers={...(options.headers||{}),'Content-Type':'application/json','X-Telegram-Init-Data':initData};const r=await fetch(path,options);const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.error||'Ошибка');return d}
function showView(view){document.querySelectorAll('.view').forEach(n=>n.classList.add('hidden'));document.getElementById('view-'+view).classList.remove('hidden');document.querySelectorAll('.bottomnav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));if(view==='catalog')loadCatalog();if(view==='sitters')loadSitters();if(view==='orders')loadOrders();if(view==='profile')loadProfile();if(view==='reviews')renderReviews();window.scrollTo({top:0,behavior:'smooth'})}
async function boot(){const me=await api('/api/me');const n=me.first_name||me.username||'Пользователь';uname.textContent=n;profileName.textContent=n;profileUser.textContent=me.username?'@'+me.username:'Telegram ID '+me.id;await loadCatalog()}
async function loadCatalog(){const a=await api('/api/catalog');catalogList.innerHTML=a.map(x=>`<article class="service"><div class="service-thumb"><img src="/assets/${x.image}"></div><div><div class="service-name">${x.name}</div><div class="service-desc">${x.desc}</div></div><div><div class="service-price">от ${x.price} ₽</div><button class="service-btn" onclick="openBooking(${x.id})">Выбрать</button></div></article>`).join('')}
function openBooking(id){selectedService=id;const x=CATALOG_CACHE.find(i=>i.id===id);bookingService.textContent=x?x.name:'';showView('booking')}
let CATALOG_CACHE=[];api('/api/catalog').then(a=>CATALOG_CACHE=a).catch(()=>{});
function setDuration(el,v){selectedDuration=v;document.querySelectorAll('.choice').forEach(b=>b.classList.remove('active'));el.classList.add('active')}
async function submitBooking(){if(!selectedService)return;await api('/api/orders',{method:'POST',body:JSON.stringify({item_id:selectedService,date:bookingDate.value,time:bookingTime.value,duration:selectedDuration,address:bookingAddress.value,note:bookingNote.value})});tg?.HapticFeedback?.notificationOccurred('success');showView('orders')}
async function loadSitters(){const a=await api('/api/sitters');sittersList.innerHTML=a.map(x=>`<article class="sitter"><div class="sitter-cover"><img src="/assets/${x.image}"></div><div class="sitter-body"><div class="sitter-name">${x.name}</div><div class="sitter-meta"><i class="fa-solid fa-star"></i> ${x.rating} · ${x.reviews} отзывов</div><div class="sitter-text">Спокойный подход, опыт с разными породами и обязательная связь во время услуги.</div><div class="sitter-tags"><div class="sitter-tag">Опыт ${x.exp}</div><div class="sitter-tag">${x.area}</div><div class="sitter-tag">Фотоотчёт</div></div><div class="sitter-actions"><button class="btn btn-dark" onclick="showView('reviews')">Отзывы</button><button class="btn btn-gold" onclick="showView('catalog')">Забронировать</button></div></div></article>`).join('')}
function setMode(m){mode=m;modeCustomer.classList.toggle('active',m==='customer');modeExecutor.classList.toggle('active',m==='executor');loadOrders()}
function statusName(s){return s==='open'?'Открыт':s==='accepted'?'Взят':s==='in_progress'?'В работе':s==='done'?'Завершён':s}
async function loadOrders(){const a=await api(mode==='executor'?'/api/executor/orders':'/api/orders');ordersList.innerHTML=a.length?a.map(o=>`<article class="order"><div class="order-top"><div><div class="order-name">${o.item_name}</div><div class="order-meta">#${o.id} · ${o.price} ₽${o.date?' · '+o.date:''}${o.time?' · '+o.time:''}</div></div><span class="status">${statusName(o.status)}</span></div>${o.address?`<div class="order-meta" style="margin-top:8px"><i class="fa-solid fa-location-dot"></i> ${o.address}</div>`:''}${mode==='executor'&&o.status==='open'?`<button class="btn btn-gold" onclick="acceptOrder(${o.id})">Взять заказ</button>`:''}${mode==='executor'&&o.status==='accepted'?`<button class="btn btn-gold" onclick="updateOrder(${o.id},'in_progress')">Начать</button>`:''}${mode==='executor'&&o.status==='in_progress'?`<button class="btn btn-gold" onclick="updateOrder(${o.id},'done')">Завершить</button>`:''}${mode==='customer'&&o.status==='done'?`<button class="btn btn-dark" onclick="showView('report')">Открыть фотоотчёт</button>`:''}</article>`).join(''):'<div class="empty">Пока нет заказов</div>'}
async function acceptOrder(id){await api('/api/executor/orders/'+id+'/accept',{method:'POST'});loadOrders()}async function updateOrder(id,s){await api('/api/executor/orders/'+id+'/status',{method:'POST',body:JSON.stringify({status:s})});loadOrders()}
async function loadProfile(){const pets=await api('/api/pets');const orders=await api('/api/orders');petCount.textContent=pets.length;orderCount.textContent=orders.length;petsList.innerHTML=pets.length?pets.map((p,i)=>`<div class="pet"><div class="pet-photo"><img src="/assets/${i%2?'asset-6.webp':'pet-premium.webp'}"></div><div><div class="pet-name">${p.name}</div><div class="pet-breed">${p.breed||'Порода не указана'}</div></div></div>`).join(''):'<div class="empty">Питомцев пока нет</div>'}
async function addPet(){const name=petName.value.trim(),breed=petBreed.value.trim();if(!name)return;await api('/api/pets',{method:'POST',body:JSON.stringify({name,breed})});petName.value='';petBreed.value='';loadProfile()}
function renderReviews(){api('/api/reviews').then(a=>reviewsList.innerHTML=a.map((r,i)=>`<article class="review"><div class="review-top"><div class="review-name">${r.name}</div><div class="review-rating"><i class="fa-solid fa-star"></i> ${r.rating}</div></div><div class="review-text">${r.text}</div><div class="review-photos"><img src="/assets/asset-${4+(i%3)}.webp"><img src="/assets/pet-premium.webp"><img src="/assets/asset-5.webp"></div></article>`).join(''))}
boot().catch(e=>document.body.insertAdjacentHTML('afterbegin','<div class="empty" style="margin:12px">'+e.message+'</div>'))
</script></body></html>'''

def conn():
    c=sqlite3.connect(DB,check_same_thread=False);c.row_factory=sqlite3.Row;return c

def ensure_col(c,name,sqltype='TEXT'):
    try:c.execute(f'ALTER TABLE orders ADD COLUMN {name} {sqltype}')
    except sqlite3.OperationalError:pass

def init_db():
    c=conn();c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,first_name TEXT,username TEXT);CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,item_id INTEGER,item_name TEXT,price INTEGER,status TEXT DEFAULT 'open',executor_id INTEGER,created_at TEXT);CREATE TABLE IF NOT EXISTS pets(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,breed TEXT);''')
    for x in ('date','time','duration','address','note'):ensure_col(c,x)
    c.commit();c.close()

def validate(raw):
    if TEST_MODE and not raw:return {'id':777000,'first_name':'Тест','username':'tester'}
    try:
        v=dict(urllib.parse.parse_qsl(raw,keep_blank_values=True));received=v.pop('hash');check='\n'.join(f'{k}={v[k]}' for k in sorted(v));secret=hmac.new(b'WebAppData',BOT_TOKEN.encode(),hashlib.sha256).digest();calc=hmac.new(secret,check.encode(),hashlib.sha256).hexdigest();return json.loads(v.get('user','{}')) if hmac.compare_digest(calc,received) else None
    except:return None

def tg(method,payload):
    if not BOT_TOKEN:return False
    try:
        req=urllib.request.Request(f'https://api.telegram.org/bot{BOT_TOKEN}/{method}',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=15) as r:return bool(json.load(r).get('ok'))
    except Exception as e:print(method,'FAIL',e);return False

def configure_bot():
    if not BOT_TOKEN or not MINI_APP_URL:return
    print('setMyCommands',tg('setMyCommands',{'commands':[{'command':'start','description':'Открыть приложение'}]}))
    print('setChatMenuButton',tg('setChatMenuButton',{'menu_button':{'type':'web_app','text':'Открыть приложение','web_app':{'url':MINI_APP_URL}}}))
    print('setWebhook',tg('setWebhook',{'url':MINI_APP_URL.rstrip('/')+'/telegram/webhook','allowed_updates':['message']}))

class H(BaseHTTPRequestHandler):
    def log_message(self,f,*a):print(f%a)
    def j(self,o,code=200):
        b=json.dumps(o,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json;charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def body(self):
        try:return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0') or 0)) or b'{}')
        except:return {}
    def user(self):
        u=validate(self.headers.get('X-Telegram-Init-Data',''))
        if u:
            c=conn();c.execute('INSERT OR REPLACE INTO users(id,first_name,username) VALUES(?,?,?)',(u['id'],u.get('first_name',''),u.get('username','')));c.commit();c.close()
        return u
    def auth(self):
        u=self.user()
        if not u:self.j({'error':'Откройте приложение из Telegram'},401)
        return u
    def asset(self,name):
        p=ASSET_DIR/name
        if not p.exists():return self.j({'error':'asset not found'},404)
        b=p.read_bytes();self.send_response(200);self.send_header('Content-Type','image/webp');self.send_header('Cache-Control','public,max-age=86400');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        p=urllib.parse.urlparse(self.path).path
        if p=='/health':return self.j({'status':'ok','version':'v2'})
        if p.startswith('/assets/'):return self.asset(p.split('/assets/',1)[1])
        if p=='/api/catalog':return self.j(CATALOG)
        if p=='/api/sitters':return self.j(SITTERS)
        if p=='/api/reviews':return self.j(REVIEWS)
        u=self.auth() if p.startswith('/api/') else None
        if p=='/api/me' and u:return self.j(u)
        if p=='/api/orders' and u:
            c=conn();r=c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall();c.close();return self.j([dict(x) for x in r])
        if p=='/api/executor/orders' and u:
            c=conn();r=c.execute("SELECT * FROM orders WHERE status='open' OR executor_id=? ORDER BY id DESC",(u['id'],)).fetchall();c.close();return self.j([dict(x) for x in r])
        if p=='/api/pets' and u:
            c=conn();r=c.execute('SELECT * FROM pets WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall();c.close();return self.j([dict(x) for x in r])
        if p.startswith('/api/'):return
        b=HTML.encode();self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def do_POST(self):
        p=urllib.parse.urlparse(self.path).path
        if p=='/telegram/webhook':
            d=self.body();m=d.get('message') or {};chat=(m.get('chat') or {}).get('id')
            if chat and str(m.get('text','')).startswith('/start') and MINI_APP_URL:tg('sendMessage',{'chat_id':chat,'text':'Dog\'s Happiness\nОткройте тестовое приложение:','reply_markup':{'inline_keyboard':[[{'text':'Открыть приложение','web_app':{'url':MINI_APP_URL}}]]}})
            return self.j({'ok':True})
        u=self.auth();
        if not u:return
        d=self.body()
        if p=='/api/orders':
            item=next((x for x in CATALOG if x['id']==int(d.get('item_id',0))),None)
            if not item:return self.j({'error':'Услуга не найдена'},404)
            c=conn();q=c.execute('INSERT INTO orders(user_id,item_id,item_name,price,status,created_at,date,time,duration,address,note) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(u['id'],item['id'],item['name'],item['price'],'open',datetime.now(timezone.utc).isoformat(),d.get('date',''),d.get('time',''),d.get('duration',''),d.get('address',''),d.get('note','')));c.commit();oid=q.lastrowid;c.close();return self.j({'ok':True,'id':oid},201)
        if p=='/api/pets':
            name=str(d.get('name','')).strip();breed=str(d.get('breed','')).strip()
            if not name:return self.j({'error':'Введите имя'},400)
            c=conn();q=c.execute('INSERT INTO pets(user_id,name,breed) VALUES(?,?,?)',(u['id'],name,breed));c.commit();pid=q.lastrowid;c.close();return self.j({'ok':True,'id':pid},201)
        if p.startswith('/api/executor/orders/'):
            a=p.strip('/').split('/');oid=int(a[3]);act=a[4] if len(a)>4 else '';c=conn()
            if act=='accept':q=c.execute("UPDATE orders SET executor_id=?,status='accepted' WHERE id=? AND status='open'",(u['id'],oid));c.commit();c.close();return self.j({'ok':q.rowcount==1})
            if act=='status':
                st=d.get('status')
                if st not in ('in_progress','done'):c.close();return self.j({'error':'Некорректный статус'},400)
                q=c.execute('UPDATE orders SET status=? WHERE id=? AND executor_id=?',(st,oid,u['id']));c.commit();c.close();return self.j({'ok':q.rowcount==1})
            c.close()
        return self.j({'error':'not found'},404)

if __name__=='__main__':
    init_db();threading.Thread(target=lambda:(time.sleep(2),configure_bot()),daemon=True).start();print('listening',PORT);ThreadingHTTPServer(('0.0.0.0',PORT),H).serve_forever()
