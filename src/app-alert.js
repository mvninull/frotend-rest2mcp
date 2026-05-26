function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = String(str ?? '');
  return div.innerHTML;
}

export function showAppAlert(msg) {
  try {
    console.log('[app-alert]', 'showAppAlert:start', { msg });
    const existing = document.getElementById('appAlertOverlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'appAlertOverlay';
    overlay.style.cssText =
      'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:999999;';

    const box = document.createElement('div');
    box.style.cssText =
      'background:white;padding:24px;border-radius:12px;max-width:400px;width:90%;text-align:center;';

    const p = document.createElement('p');
    p.style.cssText =
      'margin:0 0 16px;font-family:sans-serif;font-size:16px;color:#000;line-height:1.45;';
    p.innerHTML = escapeHtml(msg);

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = 'OK';
    btn.style.cssText =
      'background:#1a56ff;color:white;border:none;padding:10px 32px;border-radius:8px;cursor:pointer;font-family:sans-serif;font-size:14px;font-weight:700;';
    btn.onclick = () => overlay.remove();

    box.appendChild(p);
    box.appendChild(btn);
    overlay.appendChild(box);
    overlay.onclick = (e) => {
      if (e.target === e.currentTarget) overlay.remove();
    };

    const mount = document.body || document.documentElement;
    mount.appendChild(overlay);
    console.log('[app-alert]', 'showAppAlert:mounted', {
      hasOverlay: !!document.getElementById('appAlertOverlay'),
    });
    return true;
  } catch (e) {
    console.error('[showAppAlert] ERROR:', e);
    return false;
  }
}

export function notifyAppAlert(msg) {
  if (typeof window === 'undefined') return;
  console.log('[app-alert]', 'notifyAppAlert', { msg });
  const ok = showAppAlert(msg);
  if (!ok) {
    console.warn('[app-alert]', 'notifyAppAlert:fallback-window-alert', { msg });
    window.alert(String(msg ?? ''));
  }
}

export function installAppAlert() {
  if (typeof window === 'undefined') return;
  console.log('[app-alert]', 'installAppAlert');
  window.showAppAlert = notifyAppAlert;
}
