const PENDING_RETURN_TO = 'bookourshow:auth-return-to';

export function safeReturnTo(value, fallback = '/') {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || value.startsWith('/\\')) return fallback;
  try {
    const target = new URL(value, window.location.origin);
    if (target.origin !== window.location.origin) return fallback;
    return `${target.pathname}${target.search}${target.hash}`;
  } catch {
    return fallback;
  }
}

export function returnToFromLocation(from, fallback = '/') {
  if (!from || typeof from !== 'object') return fallback;
  const value = `${from.pathname || ''}${from.search || ''}${from.hash || ''}`;
  return safeReturnTo(value, fallback);
}

export function savePendingReturnTo(value) {
  try { sessionStorage.setItem(PENDING_RETURN_TO, safeReturnTo(value)); } catch { /* Router state remains available as a fallback. */ }
}

export function takePendingReturnTo() {
  try {
    const value = sessionStorage.getItem(PENDING_RETURN_TO);
    sessionStorage.removeItem(PENDING_RETURN_TO);
    return value ? safeReturnTo(value) : null;
  } catch { return null; }
}

export function clearPendingReturnTo() {
  try { sessionStorage.removeItem(PENDING_RETURN_TO); } catch { /* Storage may be unavailable. */ }
}
