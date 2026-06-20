/** Shared voice state rendering — consumes voice_ui from GET /api/health. */

const VOICE_ORB_ICONS = {
  offline: '⚠️',
  unhealthy: '⚠️',
  sleeping: '🌙',
  standby: '👂',
  awaiting: '🟢',
  conversation: '💬',
  busy: '💭',
  speaking: '🔊',
};

function voiceOrbClass(state) {
  const base = 'voice-orb';
  if (!state || state === 'offline' || state === 'unhealthy') return base;
  return `${base} ${state}`;
}

function escapeVoiceHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function applyVoiceOrbStyle(orbEl, voiceUi) {
  if (!orbEl || !voiceUi) return;
  orbEl.className = voiceOrbClass(voiceUi.state);
  orbEl.textContent = VOICE_ORB_ICONS[voiceUi.state] || '🎙';
  if (voiceUi.color) {
    orbEl.style.borderColor = voiceUi.color + '88';
    orbEl.style.background = voiceUi.color + '18';
  }
  orbEl.classList.toggle('animate', voiceUi.animate === true);
}

/**
 * Render voice_ui into panel-style elements or a single container.
 * @param {HTMLElement|object} target - container el or { orb, label, detail, banner, meta }
 * @param {object} voiceUi - { state, label, detail, color, animate }
 * @param {object} [opts] - { helper, onLiveChange }
 */
function renderVoiceState(target, voiceUi, opts = {}) {
  if (!voiceUi) return;

  const helper = opts.helper || null;
  const listening = voiceUi.state === 'awaiting' || voiceUi.state === 'conversation';
  if (typeof opts.onLiveChange === 'function') {
    opts.onLiveChange(listening);
  }

  if (target && target.nodeType === 1 && !target.dataset?.voicePart) {
    target.innerHTML = `
      <div class="voice-state-banner" style="color:${voiceUi.color}">${escapeVoiceHtml(voiceUi.label)}</div>
      <div class="${voiceOrbClass(voiceUi.state)}">${VOICE_ORB_ICONS[voiceUi.state] || '🎙'}</div>
      <div class="voice-label">${escapeVoiceHtml(voiceUi.label)}</div>
      <div class="voice-detail">${escapeVoiceHtml(voiceUi.detail)}</div>
    `;
    const orb = target.querySelector('.voice-orb');
    applyVoiceOrbStyle(orb, voiceUi);
    return;
  }

  const els = target.orb ? target : {
    orb: document.getElementById('voice-orb'),
    label: document.getElementById('voice-label'),
    detail: document.getElementById('voice-detail'),
    banner: document.getElementById('voice-banner'),
    meta: document.getElementById('voice-meta'),
  };

  if (els.banner) {
    els.banner.textContent = voiceUi.label;
    els.banner.style.color = voiceUi.color;
    els.banner.className = 'voice-state-banner state-' + voiceUi.state;
  }
  applyVoiceOrbStyle(els.orb, voiceUi);
  if (els.label) els.label.textContent = voiceUi.label;
  if (els.detail) {
    let detail = voiceUi.detail;
    if (helper?.last_heard && (voiceUi.state === 'awaiting' || voiceUi.state === 'conversation')) {
      detail = `Heard: "${String(helper.last_heard).slice(0, 60)}"`;
    } else if (helper?.last_action && voiceUi.state === 'busy') {
      detail = helper.last_action;
    }
    els.detail.textContent = detail;
  }
  if (els.meta && helper) {
    const bits = [];
    if (helper.conversation_mode) bits.push('conversation');
    if (helper.voice_muted) bits.push('muted');
    if (helper.last_action) bits.push(helper.last_action);
    els.meta.textContent = bits.join(' · ');
  }
}

function applyChatVoiceStatus(voiceUi) {
  const dot = document.getElementById('dot-voice');
  const label = document.getElementById('st-voice');
  if (!dot || !label || !voiceUi) return;
  const live = ['awaiting', 'conversation', 'busy', 'speaking'].includes(voiceUi.state);
  dot.className = 'dot ' + (live ? 'live' : (['standby', 'sleeping'].includes(voiceUi.state) ? 'ok' : ''));
  if (voiceUi.color) dot.style.background = voiceUi.color;
  label.textContent = voiceUi.label + (voiceUi.detail ? ' — ' + voiceUi.detail : '');
}

if (typeof window !== 'undefined') {
  window.renderVoiceState = renderVoiceState;
  window.applyChatVoiceStatus = applyChatVoiceStatus;
}
