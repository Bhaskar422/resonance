/* Who is signed in, and the account actions: sign in or up (email, GitHub, Google), sign out,
   access tokens for the CLI and the companion app, and approving a CLI login.
   Kept apart from core.js: the workspace only mounts once someone is signed in. */
import { useSyncExternalStore } from 'react';

const listeners = new Set();
let version = 0;
const emit = () => { version++; listeners.forEach(l => l()); };
const subscribe = l => { listeners.add(l); return () => listeners.delete(l); };

export const A = {
  status: 'loading',  // loading | in | out
  me: null, config: { required: true, password: true, providers: {} },
  error: '',
  busy: false, tokens: null, made: null, link: null,
  hash: location.hash,
};

async function req(path, init = {}) {
  const r = await fetch(path, { credentials: 'same-origin', ...init, headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...(init.headers || {}) } });
  let body = null;
  try { body = await r.json(); } catch (e) {}
  if (!r.ok) { const e = new Error((body && body.detail) || `${r.status} ${r.statusText}`); e.status = r.status; throw e; }
  return body;
}
const post = (path, data) => req(path, { method: 'POST', body: JSON.stringify(data || {}) });
const cap = s => s ? s[0].toUpperCase() + s.slice(1) : '';

export function dataMode() { try { return JSON.parse(localStorage.getItem('resonance:dataMode')) || 'live'; } catch (e) { return 'live'; } }
export function exploreSample() { try { localStorage.setItem('resonance:dataMode', JSON.stringify('sample')); } catch (e) {} location.replace('/app#/dashboard'); location.reload(); }

export async function boot() {
  const err = new URLSearchParams(location.search).get('auth_error');
  if (err) { A.error = cap(err); history.replaceState(null, '', location.pathname + location.hash); }  // shown once
  try { A.config = await req('/api/auth/config'); } catch (e) {}
  try { A.me = await req('/api/me'); A.status = 'in'; } catch (e) { A.me = null; A.status = 'out'; }
  emit();
}

// The workspace reports a 401 (session ended elsewhere): show the sign-in page again.
addEventListener('resonance:unauthorized', () => { if (A.status === 'in') { A.status = 'out'; A.me = null; emit(); } });
addEventListener('hashchange', () => { A.hash = location.hash; emit(); });

async function act(fn) {
  A.busy = true; A.error = ''; emit();
  try { await fn(); } catch (e) { A.error = cap(e.message || String(e)); }
  A.busy = false; emit();
}
// A full reload after signing in or out, so every cached run belongs to the right person.
const reload = () => { location.replace('/app' + (location.hash || '#/dashboard')); location.reload(); };

export const signIn = (email, password) => act(async () => { await post('/api/auth/signin', { email, password }); reload(); });
export const signUp = (email, password, name) => act(async () => { await post('/api/auth/signup', { email, password, name }); reload(); });
export const withProvider = p => { location.href = `/api/auth/${p}/start?next=${encodeURIComponent('/app' + (location.hash || ''))}`; };
export const signOut = () => act(async () => { await post('/api/auth/signout'); reload(); });

export const loadTokens = () => act(async () => { A.tokens = await req('/api/tokens'); });
export const createToken = name => act(async () => { A.made = await post('/api/tokens', { name: name || 'token' }); A.tokens = await req('/api/tokens'); });
export const revokeToken = id => act(async () => { await req('/api/tokens/' + encodeURIComponent(id), { method: 'DELETE' }); if (A.made && A.made.info.id === id) A.made = null; A.tokens = await req('/api/tokens'); });
export const dismissToken = () => { A.made = null; emit(); };

export const linkCode = () => { const q = (A.hash.split('?')[1] || ''); return (new URLSearchParams(q).get('code') || '').toUpperCase(); };
export const loadLink = code => act(async () => { A.link = { code, ...(await req('/api/cli/device/' + encodeURIComponent(code))) }; });
export const approveLink = code => act(async () => { await post('/api/cli/approve', { code }); A.link = { ...(A.link || {}), code, approved: true }; });

export function useAccount() {
  useSyncExternalStore(subscribe, () => version);
  return A;
}
