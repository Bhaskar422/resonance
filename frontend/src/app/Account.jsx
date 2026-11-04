import { useEffect, useState } from 'react';
import { Button, Logo, Panel } from '../components/ui.jsx';
import {
  approveLink, createToken, deleteAccount, dismissToken, exploreSample, linkCode, loadLink, loadTokens, revokeToken,
  signIn, signOut, signUp, withProvider,
} from '../lib/account.js';

const INPUT = 'h-10 px-3 bg-bg border border-line-2 rounded-ctl text-fg text-[14px] min-w-0 w-full';
const LABEL = 'font-mono text-[10.5px] font-semibold leading-none tracking-[.12em] text-fg-3';
const when = t => t ? new Date(t * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'never';

function Frame({ children }) {
  return (
    <div className="min-h-screen bg-bg wash text-fg font-sans text-[14px] flex flex-col">
      <header className="h-[60px] shrink-0 flex items-center border-b border-line" style={{ paddingInline: 'var(--pad)' }}><Logo href="/" /></header>
      <main className="flex-1 grid place-items-center px-4 py-10">{children}</main>
    </div>
  );
}

function Alert({ children }) {
  if (!children) return null;
  return (
    <div role="alert" className="px-3.5 py-2.5 border border-sev-stop rounded-card text-[13px]" style={{ background: 'color-mix(in oklch, var(--sev-stop) 10%, transparent)' }}>{children}</div>
  );
}

const GITHUB = <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" /></svg>;
const GOOGLE = <svg viewBox="0 0 48 48" width="16" height="16" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" /><path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" /><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z" /><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" /></svg>;

export function AuthPage({ a }) {
  const [mode, setMode] = useState('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const up = mode === 'signup';
  const providers = Object.entries(a.config.providers || {}).filter(([, on]) => on).map(([p]) => p);
  const submit = e => { e.preventDefault(); up ? signUp(email, password, name) : signIn(email, password); };
  return (
    <Frame>
      <div className="w-full max-w-[400px] flex flex-col gap-5">
        <div>
          <div className="font-mono text-[11px] font-medium leading-none tracking-[.14em] text-signal">{up ? 'NEW ACCOUNT' : 'WELCOME BACK'}</div>
          <h1 className="mt-2.5 mb-0 text-[28px] font-semibold leading-tight">{up ? 'Create your account' : 'Sign in to Resonance'}</h1>
          <p className="mt-2 mb-0 text-fg-2 text-[14px]">Your machines, runs and reports stay in your account. The command-line tool signs in to the same one.</p>
        </div>

        {providers.length > 0 && (
          <div className="flex flex-col gap-2">
            {providers.map(p => (
              <Button key={p} onClick={() => withProvider(p)} className="w-full h-11">{p === 'github' ? GITHUB : GOOGLE}Continue with {p === 'github' ? 'GitHub' : 'Google'}</Button>
            ))}
            <div className="flex items-center gap-3 pt-1 text-fg-3 font-mono text-[11px] tracking-[.1em]"><span className="flex-1 h-px bg-line" />OR WITH EMAIL<span className="flex-1 h-px bg-line" /></div>
          </div>
        )}

        <form onSubmit={submit} className="flex flex-col gap-3.5" noValidate={false}>
          {up && (
            <label className="flex flex-col gap-1.5"><span className={LABEL}>NAME</span>
              <input value={name} onChange={e => setName(e.target.value)} autoComplete="name" placeholder="Ada Lovelace" className={INPUT} /></label>
          )}
          <label className="flex flex-col gap-1.5"><span className={LABEL}>EMAIL</span>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" placeholder="you@example.com" className={INPUT} /></label>
          <label className="flex flex-col gap-1.5"><span className={LABEL}>PASSWORD</span>
            <input type="password" required minLength={up ? 8 : undefined} value={password} onChange={e => setPassword(e.target.value)} autoComplete={up ? 'new-password' : 'current-password'} className={INPUT} />
            {up && <span className="text-[12px] text-fg-3">At least 8 characters.</span>}</label>
          <Alert>{a.error}</Alert>
          <Button primary type="submit" disabled={a.busy} className="w-full h-11">{a.busy ? 'One moment…' : up ? 'Create account' : 'Sign in'}</Button>
        </form>

        <div className="flex flex-wrap justify-between gap-2 text-[13px]">
          <button type="button" onClick={() => setMode(up ? 'signin' : 'signup')} className="border-0 bg-transparent p-0 text-accent">
            {up ? 'Already have an account? Sign in' : 'New here? Create an account'}</button>
          <button type="button" onClick={exploreSample} className="border-0 bg-transparent p-0 text-fg-2">Explore the sample data →</button>
        </div>
        <p className="m-0 text-[12px] text-fg-3">By continuing you agree to the <a href="/terms" className="text-fg-2 underline">Terms</a> and <a href="/privacy" className="text-fg-2 underline">Privacy Policy</a>.</p>
      </div>
    </Frame>
  );
}

export function LinkPage({ a }) {
  const code = linkCode();
  useEffect(() => { if (code) loadLink(code); }, [code]);
  const l = a.link && a.link.code === code ? a.link : null;
  return (
    <Frame>
      <div className="w-full max-w-[440px] flex flex-col gap-5">
        <div>
          <div className="font-mono text-[11px] font-medium leading-none tracking-[.14em] text-signal">CONNECT A DEVICE</div>
          <h1 className="mt-2.5 mb-0 text-[26px] font-semibold leading-tight">{l && l.approved ? 'Connected' : 'Allow access to your account?'}</h1>
        </div>
        {!code && <Alert>This link has no code. Run <code>resonance login</code> again and open the link it prints.</Alert>}
        {code && !l && !a.error && <p className="m-0 text-fg-2">Checking the code…</p>}
        {code && !l && a.error && <Alert>{a.error}</Alert>}
        {l && !l.approved && (
          <>
            <Panel bodyClass="p-4 flex flex-col gap-3">
              <div className="flex justify-between gap-3"><span className="text-fg-2">Device</span><b className="font-semibold text-right">{l.name}</b></div>
              <div className="flex justify-between gap-3"><span className="text-fg-2">Code</span><b className="font-mono font-semibold tracking-[.12em]">{l.code}</b></div>
              <div className="flex justify-between gap-3"><span className="text-fg-2">Account</span><span className="text-right [overflow-wrap:anywhere]">{a.me.email}</span></div>
            </Panel>
            <p className="m-0 text-[13px] text-fg-2">Only approve if this code matches the one in your terminal. The device can then upload clips and read your runs until you revoke it in Settings.</p>
            <Alert>{a.error}</Alert>
            <div className="flex gap-2.5">
              <Button primary disabled={a.busy} onClick={() => approveLink(code)}>Approve</Button>
              <Button href="#/dashboard">Cancel</Button>
            </div>
          </>
        )}
        {l && l.approved && (
          <>
            <p className="m-0 text-fg-2">{l.name} is signed in as {a.me.email}. You can go back to your terminal.</p>
            <div><Button href="#/dashboard">Open the workspace</Button></div>
          </>
        )}
      </div>
    </Frame>
  );
}

export function AccountMenu({ a }) {
  const [open, setOpen] = useState(false);
  const me = a.me;
  if (!me) {
    return <button type="button" onClick={() => { try { localStorage.setItem('resonance:dataMode', '"live"'); } catch (e) {} location.reload(); }}
      className="h-[34px] px-3 shrink-0 border border-line-2 rounded-ctl bg-transparent text-[13px] text-fg whitespace-nowrap">Sign in</button>;
  }
  const initial = (me.name || me.email || '?')[0].toUpperCase();
  return (
    <div className="relative shrink-0">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} aria-label={`Account: ${me.email}`}
        className="size-[34px] grid place-items-center rounded-full border border-line-2 bg-panel-2 overflow-hidden font-semibold text-[13px] text-fg">
        {me.avatar ? <img src={me.avatar} alt="" className="size-full object-cover" referrerPolicy="no-referrer" /> : initial}
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-40 w-[min(260px,86vw)] p-1.5 bg-panel border border-line-2 rounded-card shadow-pop" onMouseLeave={() => setOpen(false)}>
          <div className="px-2.5 py-2 border-b border-line mb-1">
            <div className="text-[13.5px] font-semibold truncate">{me.name}</div>
            <div className="font-mono text-[11.5px] text-fg-3 truncate">{me.email}</div>
            {!!me.admin && <div className="mt-1 font-mono text-[10.5px] tracking-[.1em] text-signal">ADMIN</div>}
          </div>
          <a href="#/settings" onClick={() => setOpen(false)} className="block px-2.5 py-2 rounded-ctl text-fg text-[13px] no-underline hover:no-underline hover:bg-panel-2">Account &amp; access tokens</a>
          {me.auth && <button type="button" onClick={signOut} className="w-full text-left px-2.5 py-2 rounded-ctl border-0 bg-transparent text-fg text-[13px] hover:bg-panel-2">Sign out</button>}
        </div>
      )}
    </div>
  );
}

export function AccountSettings({ a }) {
  const [name, setName] = useState('');
  const me = a.me;
  useEffect(() => { if (me && me.auth && !a.tokens) loadTokens(); }, [me]);
  if (!me) return null;
  if (!me.auth) {
    return <Panel label="ACCOUNT" bodyClass="px-4 py-3.5 text-[13px] text-fg-2">Accounts are off on this server (RESONANCE_AUTH=off): everyone who can open it uses one shared workspace.</Panel>;
  }
  const how = [me.has_password && 'email and password', ...me.providers.map(p => p === 'github' ? 'GitHub' : 'Google')].filter(Boolean).join(', ');
  return (
    <>
      <Panel label="ACCOUNT" bodyClass="flex flex-wrap items-center gap-x-5 gap-y-3 px-4 py-3.5">
        <div className="flex-1 min-w-[200px]">
          <div className="font-semibold">{me.name}{!!me.admin && <span className="ml-2 font-mono text-[10.5px] tracking-[.1em] text-signal">ADMIN</span>}</div>
          <div className="text-[13px] text-fg-2 [overflow-wrap:anywhere]">{me.email} · signs in with {how}</div>
        </div>
        <Button small onClick={signOut}>Sign out</Button>
      </Panel>

      <Panel label="ACCESS TOKENS · CLI & SCRIPTS" bodyClass="">
        <p className="m-0 px-4 pt-3.5 text-[13px] text-fg-2">
          The easiest way is <code className="font-mono text-[12.5px] text-fg">resonance login --server {location.origin}</code>, which opens this site to approve it.
          For scripts, make a token here and pass it as <code className="font-mono text-[12.5px] text-fg">--token</code> or <code className="font-mono text-[12.5px] text-fg">RESONANCE_TOKEN</code>.
        </p>
        <form onSubmit={e => { e.preventDefault(); createToken(name); setName(''); }} className="flex flex-wrap gap-2 px-4 py-3.5 border-b border-line">
          <input value={name} onChange={e => setName(e.target.value)} placeholder="Name, e.g. workshop laptop" aria-label="Token name" className="h-[34px] px-3 bg-bg border border-line-2 rounded-ctl text-fg text-[13px] flex-1 min-w-[180px]" />
          <Button small primary type="submit" disabled={a.busy}>Create token</Button>
        </form>
        {a.made && (
          <div className="px-4 py-3.5 border-b border-line flex flex-col gap-2" style={{ background: 'color-mix(in oklch, var(--signal) 8%, transparent)' }}>
            <div className="text-[13px]"><b className="font-semibold">Copy this token now.</b> It is shown only once.</div>
            <div className="flex flex-wrap gap-2 items-center">
              <code className="flex-1 min-w-0 px-2.5 py-2 bg-bg border border-line-2 rounded-ctl font-mono text-[12.5px] [overflow-wrap:anywhere]">{a.made.token}</code>
              <Button small onClick={() => { navigator.clipboard && navigator.clipboard.writeText(a.made.token); }}>Copy</Button>
              <Button small onClick={dismissToken}>Done</Button>
            </div>
          </div>
        )}
        {(a.tokens || []).map(t => (
          <div key={t.id} className="flex flex-wrap items-center gap-x-4 gap-y-1.5 px-4 py-3 border-b border-line last:border-b-0">
            <span className="flex-1 min-w-[160px] font-semibold">{t.name}</span>
            <span className="font-mono text-[12px] text-fg-3">{t.hint}…</span>
            <span className="font-mono text-[11.5px] text-fg-3">made {when(t.created)} · used {when(t.last_used)}</span>
            <Button small onClick={() => revokeToken(t.id)} disabled={a.busy}>Revoke</Button>
          </div>
        ))}
        {a.tokens && !a.tokens.length && <p className="m-0 px-4 py-3 text-[13px] text-fg-3">No tokens yet.</p>}
        {a.error && <div className="px-4 py-3"><p className="m-0 text-[13px] text-sev-stop">{a.error}</p></div>}
      </Panel>
    </>
  );
}

export function DeleteAccount({ a }) {
  const [typed, setTyped] = useState('');
  const me = a.me;
  if (!me || !me.auth) return null;
  return (
    <Panel label="DELETE ACCOUNT" bodyClass="px-4 py-3.5 flex flex-col gap-3">
      <p className="m-0 text-[13px] text-fg-2">
        Erases your account, its sign-in links, sessions and access tokens, every run you created, and the clips and files you uploaded for them.
        This cannot be undone. See the <a href="/privacy" className="text-accent">privacy policy</a>.
      </p>
      <form onSubmit={e => { e.preventDefault(); if (typed.trim().toLowerCase() === me.email) deleteAccount(); }} className="flex flex-wrap gap-2">
        <input value={typed} onChange={e => setTyped(e.target.value)} placeholder={`Type ${me.email} to confirm`} aria-label="Type your email to confirm" autoComplete="off"
          className="h-[34px] px-3 bg-bg border border-line-2 rounded-ctl text-fg text-[13px] flex-1 min-w-[220px]" />
        <Button small type="submit" disabled={a.busy || typed.trim().toLowerCase() !== me.email} className="text-sev-stop">Delete my account</Button>
      </form>
    </Panel>
  );
}
