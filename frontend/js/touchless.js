const normalize = value => String(value || '').toLowerCase().replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim();

// Small edit-distance helper so mis-heard drink names (“show me latter”) still match the menu.
const editDistance = (a, b) => {
  const rows = Array.from({ length: a.length + 1 }, (_, i) => [i]);
  for (let j = 1; j <= b.length; j++) rows[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++) rows[i][j] = Math.min(rows[i - 1][j] + 1, rows[i][j - 1] + 1, rows[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return rows[a.length][b.length];
};
const soundsLike = (word, token) => {
  if (word === token) return true;
  const tolerance = token.length >= 7 ? 2 : 1;
  return Math.abs(word.length - token.length) <= tolerance && editDistance(word, token) <= tolerance;
};

export function parseVoiceIntent(transcript, products = []) {
  const text = normalize(transcript);
  if (!text) return null;
  if (/\b(home|go home|take me home|show home|open homepage|homepage|start ordering)\b/.test(text)) return { type: 'GO_HOME' };
  if (/\b(about|our story|about us)\b/.test(text)) return { type: 'OPEN_SECTION', section: 'about' };
  if (/\b(gallery|callery|photo gallery|photos)\b/.test(text)) return { type: 'OPEN_SECTION', section: 'gallery' };
  if (/\b(customer menu|storefront|shop menu)\b/.test(text)) return { type: 'OPEN_CUSTOMER_MENU' };
  if (/\b(previous coffee|previous drink)\b/.test(text)) return { type: 'PREVIOUS_PRODUCT' };
  if (/\b(next coffee|next drink)\b/.test(text)) return { type: 'NEXT_PRODUCT' };
  if (/\b(previous|go back one)\b/.test(text)) return { type: 'PREVIOUS' };
  if (/\b(next)\b/.test(text)) return { type: 'NEXT' };
  if (/\b(add (this|it|that) to (the )?(cart|bag|card)|add to (cart|bag|card))\b/.test(text)) return { type: 'ADD_TO_CART' };
  // Cancel is checked before page-specific commands so “cancel my order” never opens a page.
  if (/\b(go back|back|never mind|stop|cancel|cancel this)\b/.test(text)) return { type: 'CANCEL' };
  // Customization choices run before navigation so “large coffee” customizes the open drink
  // instead of leaving the page, while navigation still needs an explicit browsing verb.
  if (/\b(less sugar|no sugar|regular sugar|extra sugar)\b/.test(text)) return { type: 'CHOOSE_OPTION', group: 'sugar', query: text };
  if (/\b(small|medium|large)\b/.test(text)) return { type: 'CHOOSE_OPTION', group: 'size', query: text };
  // Admin workspace tabs: a bare tab word or “open orders” style phrases. Dispatch decides
  // whether this means an admin tab or, for “contact”, the customer contact page.
  const adminText = text.replace(/\badmin\b/g, '').replace(/\bcustomer records?\b/g, 'users').trim();
  const adminTabWord = (adminText.match(/^(orders?|products?|categories|contact|messages?|users?|menu settings?|settings)$/) || [])[1] || (adminText.match(/\b(?:open|show|go to|switch to|view)\s+(?:the\s+)?(orders?|products?|categories|contact|messages?|users?|menu settings?|settings)\b/) || [])[1];
  if (adminTabWord) {
    const tab = adminTabWord.startsWith('order') ? 'orders' : adminTabWord.startsWith('product') ? 'products' : adminTabWord.startsWith('categor') ? 'categories' : adminTabWord.startsWith('message') ? 'messages' : adminTabWord.startsWith('user') ? 'users' : adminTabWord.startsWith('contact') ? 'contact' : 'settings';
    return { type: 'OPEN_ADMIN_TAB', tab };
  }
  if (/\b(open|show|find|take me to|go to|browse|see|want|get)\b.*\b(menu|coffees?)\b/.test(text) || /^(the )?(coffee )?menu$/.test(text) || /^(the )?coffee$/.test(text)) return { type: 'OPEN_MENU' };
  if (/\b(open|show|take me to|go to|view|see)?\s*(my |the )?(cart|bag|card)\b/.test(text)) return { type: 'OPEN_CART' };
  if (/\b(checkout|check out|proceed to checkout)\b/.test(text)) return { type: 'CHECKOUT' };
  if (/\b(contact|contact page|contact us|message the cafe)\b/.test(text)) return { type: 'OPEN_CONTACT' };
  if (/\b(register|sign up|create an account|create account)\b/.test(text)) return { type: 'OPEN_REGISTER' };
  if (/\b(sign out|log out|logout|log off|sign off)\b/.test(text)) return { type: 'SIGN_OUT' };
  if (/\b(sign in|log in|login|my account|account)\b/.test(text)) return { type: 'OPEN_SIGNIN' };
  if (/\b(help|show help)\b/.test(text)) return { type: 'OPEN_HELP' };
  if (/\b(select this|select this one|choose this|select it)\b/.test(text)) return { type: 'SELECT' };
  if (/\b(confirm order|place order|yes confirm)\b/.test(text)) return { type: 'CONFIRM_ORDER' };
  if (/\b(confirm|yes)\b/.test(text)) return { type: 'CONFIRM' };
  if (/\b(refresh|reload|update (the )?(orders|list))\b/.test(text)) return { type: 'REFRESH' };
  const words = text.split(' ');
  const product = [...products].sort((a, b) => normalize(b.name).length - normalize(a.name).length).find(item => {
    const name = normalize(item.name);
    if (!name) return false;
    if (text.includes(name)) return true;
    const tokens = name.split(' ');
    return tokens.every(token => token.length < 4 ? words.includes(token) : words.some(word => soundsLike(word, token)));
  });
  if (product) return { type: 'SELECT_PRODUCT', productId: product.id, productName: product.name };
  return null;
}

export class TouchlessFeedback {
  constructor() { this.soundEnabled = localStorage.getItem('kioskSound') !== 'off'; this.voiceEnabled = localStorage.getItem('kioskVoice') === 'on'; this.context = null; }
  getAudioContext() {
    const Audio = window.AudioContext || window.webkitAudioContext;
    if (!Audio) return null;
    if (!this.context || this.context.state === 'closed') this.context = new Audio();
    return this.context;
  }
  unlock() {
    try { const context = this.getAudioContext(); if (context?.state !== 'running') context?.resume().catch(() => {}); } catch { /* Audio is optional. */ }
  }
  sound(kind = 'select') {
    if (!this.soundEnabled) return;
    let context;
    try {
      context = this.getAudioContext();
      if (!context) return;
      if (context.state !== 'running') { context.resume().then(() => this.playSound(context, kind)).catch(() => {}); return; }
      this.playSound(context, kind);
    } catch { /* Audio is an optional browser capability. */ }
  }
  playSound(context, kind) {
    if (!this.soundEnabled || context !== this.context || context.state !== 'running') return;
    try {
      const tone = (frequency, duration, delay = 0, peak = .07) => {
        const oscillator = context.createOscillator(), gain = context.createGain();
        const start = context.currentTime + delay;
        oscillator.frequency.value = frequency; oscillator.type = 'sine';
        gain.gain.setValueAtTime(.0001, start);
        gain.gain.exponentialRampToValueAtTime(peak, start + .02);
        gain.gain.exponentialRampToValueAtTime(.0001, start + duration);
        oscillator.connect(gain); gain.connect(context.destination);
        oscillator.start(start); oscillator.stop(start + duration + .02);
      };
      const notes = { focus: [[523, .06]], select: [[659, .09]], success: [[659, .1], [880, .16, .09]], cancel: [[392, .11]], error: [[220, .13]] };
      (notes[kind] || notes.select).forEach(([frequency, duration, delay]) => tone(frequency, duration, delay || 0));
    } catch { /* Audio is an optional browser capability. */ }
  }
  speak(message) {
    if (!this.voiceEnabled || !('speechSynthesis' in window) || !message) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(message); utterance.rate = 1; utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
  }
  setSound(enabled) { this.soundEnabled = enabled; localStorage.setItem('kioskSound', enabled ? 'on' : 'off'); }
  setVoice(enabled) { this.voiceEnabled = enabled; localStorage.setItem('kioskVoice', enabled ? 'on' : 'off'); }
}

export class VoiceControl {
  constructor(onIntent, onStatus) { this.onIntent = onIntent; this.onStatus = onStatus; this.recognition = null; this.listening = false; this.shouldListen = false; this.error = null; this.restartTimer = null; }
  start() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) { this.error = 'Voice control is not supported by this browser. Try a browser with speech recognition.'; this.onStatus(this.error); return false; }
    if (!this.recognition) {
      this.recognition = new Recognition(); this.recognition.lang = 'en-US'; this.recognition.continuous = true; this.recognition.interimResults = false; this.recognition.maxAlternatives = 3;
      this.recognition.onstart = () => { this.listening = true; this.error = null; this.onStatus('Listening'); };
      this.recognition.onresult = event => {
        const start = event.resultIndex ?? event.results.length - 1;
        for (let index = start; index < event.results.length; index++) {
          const result = event.results[index];
          if (!result?.isFinal) continue;
          const candidates = Array.from(result, alternative => ({ transcript: alternative.transcript.trim(), confidence: Number(alternative.confidence) || 0 })).filter(item => item.transcript);
          if (!candidates.length) continue;
          this.onStatus(`Heard: ${candidates[0].transcript}`);
          const best = candidates[0];
          if (best.confidence > 0 && best.confidence < .48 && candidates.slice(1).every(item => item.confidence < .58)) { this.onStatus('Speech was unclear. Please try again.'); continue; }
          if (best.confidence > 0 && best.confidence < .72 && /\b(checkout|check out|confirm|place order)\b/i.test(best.transcript)) { this.onStatus('Please repeat that confirmation clearly.'); continue; }
          this.onIntent(candidates);
        }
      };
      this.recognition.onerror = event => {
        // Silence and intentional stops are normal; onend restarts listening, so ignore them.
        if (event.error === 'no-speech' || event.error === 'aborted') return;
        this.error = ['not-allowed', 'service-not-allowed'].includes(event.error) ? 'Microphone permission denied. Allow microphone access in your browser.' : event.error === 'audio-capture' ? 'No working microphone was found.' : event.error === 'network' ? 'Voice service is unreachable. Check the connection.' : `Voice error: ${event.error}`;
        this.onStatus(this.error);
      };
      this.recognition.onend = () => {
        this.listening = false;
        // Browsers end the session after a pause; restart automatically so the kiosk
        // keeps listening until the user presses Stop voice.
        if (this.shouldListen && !this.error) {
          this.restartTimer = setTimeout(() => { this.restartTimer = null; if (!this.shouldListen || !this.recognition) return; try { this.recognition.start(); } catch { /* already starting */ } }, 300);
          return;
        }
        this.onStatus(this.error || 'Not listening');
      };
    }
    this.shouldListen = true; this.error = null;
    try { this.recognition.start(); return true; } catch { this.onStatus('Voice control is already starting'); return false; }
  }
  stop() { this.shouldListen = false; if (this.restartTimer) { clearTimeout(this.restartTimer); this.restartTimer = null; } if (this.recognition && this.listening) this.recognition.stop(); this.listening = false; this.error = null; this.onStatus('Not listening'); }
}
