import lottie from 'lottie-web';
const control=document.querySelector('#play'), seek=document.querySelector('#seek'), clock=document.querySelector('#time'), step=document.querySelector('#step');
const a=lottie.loadAnimation({container:document.querySelector('#animation'),renderer:'svg',loop:false,autoplay:false,path:'/lottie/water-cycle.json'});
function update(frame){const n=Math.max(0,Math.min(239,Math.round(frame)));seek.value=n;clock.textContent=`${(n/30).toFixed(1)} / 8.0s`;step.textContent=n<63?'01 · 海水蒸发':n<116?'02 · 水汽凝结':n<170?'03 · 云层降雨':'04 · 径流回海';}
a.addEventListener('DOMLoaded',()=>{const start=Number(new URLSearchParams(location.search).get('frame')||0);a.goToAndStop(start,true);update(start)});
a.addEventListener('enterFrame',e=>update(e.currentTime));a.addEventListener('complete',()=>{control.textContent='重播';update(239)});
control.addEventListener('click',()=>{if(a.isPaused){if(a.currentFrame>=238)a.goToAndStop(0,true);a.play();control.textContent='暂停'}else{a.pause();control.textContent='播放'}});
seek.addEventListener('input',()=>{a.goToAndStop(Number(seek.value),true);control.textContent='播放';update(Number(seek.value))});
