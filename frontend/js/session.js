const IDLE_MS=5*60*1000, WARNING_MS=30*1000;
let idleTimer, resetTimer;
let resetIdle;
export function startSession(onWarn,onReset,onActivity){
  const activity=()=>{clearTimeout(idleTimer);clearTimeout(resetTimer);onActivity?.();idleTimer=setTimeout(()=>{onWarn();resetTimer=setTimeout(onReset,WARNING_MS)},IDLE_MS-WARNING_MS)};
  resetIdle=activity;
  ['pointerdown','pointermove','keydown','touchstart'].forEach(type=>window.addEventListener(type,activity,{passive:true}));
  activity();return ()=>{clearTimeout(idleTimer);clearTimeout(resetTimer)};
}
export function registerActivity(){resetIdle?.()}
