import { animate, createTimeline, svg } from 'animejs';
const tl=createTimeline({autoplay:false,loop:false,defaults:{ease:'inOutSine'}});
tl.add('#vapor',{opacity:[0,1],translateY:[75,-65],duration:2300},250)
  .add('#cloud',{opacity:[0.35,1],translateX:[-110,50],duration:3000},1000)
  .add('#rain',{opacity:[0,1],translateY:[-65,75],duration:1700},3600)
  .add('#river',{strokeDasharray:['5 1800','100 14'],strokeDashoffset:[350,0],duration:2200},4900)
  .add('#s1',{opacity:[0,1],duration:500},200)
  .add('#s2',{opacity:[0,1],duration:500},1850)
  .add('#s3',{opacity:[0,1],duration:500},3800)
  .add('#s4',{opacity:[0,1],duration:500},5700);
const seek=document.querySelector('#seek'),time=document.querySelector('#time'),toggle=document.querySelector('#toggle');
let playing=false;let raf=0;let prev=0;const dur=8000;
function render(t){t=Math.max(0,Math.min(dur,t));tl.seek(t);seek.value=t;time.textContent=`${(t/1000).toFixed(1)} / 8.0 秒`}
function tick(now){if(!playing)return;if(!prev)prev=now;const t=Math.min(dur,Number(seek.value)+now-prev);prev=now;render(t);if(t>=dur){playing=false;toggle.textContent='重播';return}raf=requestAnimationFrame(tick)}
function play(){if(Number(seek.value)>=dur)render(0);playing=true;prev=0;toggle.textContent='暂停';raf=requestAnimationFrame(tick)}
function pause(){playing=false;cancelAnimationFrame(raf);toggle.textContent='播放';prev=0}
toggle.addEventListener('click',()=>playing?pause():play());seek.addEventListener('input',()=>{pause();render(Number(seek.value))});render(0);
window.waterCycleLab={seek:render,pause,play,getCurrentTime:()=>Number(seek.value),duration:dur};
