import { StrictMode, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import '../styles.css';
import { makeStore } from '../lib/store.js';
import { boot, dataMode, useAccount } from '../lib/account.js';
import { AuthPage, LinkPage } from './Account.jsx';
import { Logo } from '../components/ui.jsx';
import Shell from './Shell.jsx';
import Dashboard from './pages/Dashboard.jsx';
import { Machines, MachineDetail } from './pages/Machines.jsx';
import Runs from './pages/Runs.jsx';
import Report from './pages/Report.jsx';
import Analyze from './pages/Analyze.jsx';
import Rescan from './pages/Rescan.jsx';
import Guide from './pages/Guide.jsx';
import Usage from './pages/Usage.jsx';
import Settings from './pages/Settings.jsx';
import More from './pages/More.jsx';
import Kit from './pages/Kit.jsx';

const store = makeStore('app');
boot();

// The core parses the hash route; v.p says which page is active.
function App({ a }) {
  useEffect(() => { store.mount(); }, []);
  const v = store.useVals();
  const p = v.p || { dashboard: true };
  return (
    <Shell v={v} a={a}>
      {p.dashboard && <Dashboard v={v} />}
      {p.machines && <Machines v={v} />}
      {p.machine && <MachineDetail v={v} />}
      {p.runs && <Runs v={v} />}
      {p.report && <Report v={v} />}
      {p.analyze && <Analyze v={v} />}
      {p.rescan && <Rescan v={v} />}
      {p.guide && <Guide v={v} />}
      {p.usage && <Usage v={v} />}
      {p.settings && <Settings v={v} a={a} />}
      {p.more && <More v={v} />}
      {p.kit && <Kit v={v} />}
    </Shell>
  );
}

// Live data needs an account; the sample data can be explored without one.
function Root() {
  const a = useAccount();
  const sample = dataMode() === 'sample';
  if (a.status === 'loading') return (
    <div role="status" aria-label="Loading Resonance" className="min-h-screen bg-bg flex flex-col items-center justify-center gap-5 opacity-0 animate-[fadein_.3s_ease_.3s_forwards]">
      <Logo href="/" />
      <span className="size-5 rounded-full border-2 border-line-2 border-t-[var(--accent)] animate-spin" />
    </div>
  );
  if (a.status === 'out' && !sample) return <AuthPage a={a} />;
  if (a.status === 'in' && a.hash.startsWith('#/link')) return <LinkPage a={a} />;
  return <App a={a} />;
}

createRoot(document.getElementById('root')).render(<StrictMode><Root /></StrictMode>);
