/* Dog's Happiness v12 */
(() => {
  'use strict';
  const SITTER_PHOTO='https://images.unsplash.com/photo-1598262088246-2b1a35324c83?auto=format&fit=crop&w=1200&q=86';

  function visibleView(){
    return document.querySelector('.view:not(.hidden)')?.id?.replace('view-','') || '';
  }
  function applyScreenLock(v=visibleView()){
    document.body.classList.toggle('v12-screen-lock', v==='intro' || v==='role');
    if(v==='role'){
      requestAnimationFrame(()=>window.scrollTo({top:0,left:0,behavior:'instant'}));
    }
  }
  function restoreSitterPhoto(){
    const img=document.querySelector('#view-client-home .feature-card.wide img');
    if(img && img.src!==SITTER_PHOTO){
      img.src=SITTER_PHOTO;
      img.removeAttribute('srcset');
      img.loading='eager';
      img.decoding='async';
    }
  }

  const oldShow=window.showView;
  if(typeof oldShow==='function'){
    window.showView=async function(v){
      const result=await oldShow(v);
      applyScreenLock(v);
      restoreSitterPhoto();
      return result;
    };
  }

  const oldClientHome=window.loadClientHome;
  if(typeof oldClientHome==='function'){
    window.loadClientHome=async function(){
      const result=await oldClientHome();
      restoreSitterPhoto();
      return result;
    };
  }

  function sync(){
    applyScreenLock();
    restoreSitterPhoto();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',sync,{once:true});
  else sync();
  window.addEventListener('resize',()=>applyScreenLock(),{passive:true});
})();
