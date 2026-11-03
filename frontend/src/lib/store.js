import { useSyncExternalStore } from 'react';
import { createApp } from './core.js';

// One app instance per page; React re-renders whenever the core emits a change.
const listeners = new Set();
let version = 0;
const notify = () => { version++; listeners.forEach(l => l()); };
const subscribe = l => { listeners.add(l); return () => listeners.delete(l); };
const getVersion = () => version;

const ON = { bg: 'color-mix(in oklch, var(--signal) 14%, transparent)', fg: 'var(--signal)', bd: 'var(--signal)' };
const OFF = { bg: 'transparent', fg: 'var(--fg-2)', bd: 'var(--line-2)' };

const SITE_ON = { bg: 'color-mix(in oklch, var(--signal) 12%, var(--panel))', fg: 'var(--fg)', bd: 'var(--signal)' };
const SITE_OFF = { bg: 'var(--panel)', fg: 'var(--fg)', bd: 'var(--line)' };

export function makeStore(mode) {
  const site = mode === 'site';
  const app = createApp({ id: 'A', mode, defaultTheme: 'dark', on: site ? SITE_ON : ON, off: site ? SITE_OFF : OFF, onChange: notify });
  let mounted = false;
  return {
    mount() { if (!mounted) { mounted = true; app.mount(); } },
    useVals() {
      useSyncExternalStore(subscribe, getVersion);
      return app.vals();
    },
  };
}
