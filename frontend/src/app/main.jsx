import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '../styles.css';
import { makeStore } from '../lib/store.js';
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
store.mount();

// The core parses the hash route; v.p says which page is active.
function App() {
  const v = store.useVals();
  const p = v.p || { dashboard: true };
  return (
    <Shell v={v}>
      {p.dashboard && <Dashboard v={v} />}
      {p.machines && <Machines v={v} />}
      {p.machine && <MachineDetail v={v} />}
      {p.runs && <Runs v={v} />}
      {p.report && <Report v={v} />}
      {p.analyze && <Analyze v={v} />}
      {p.rescan && <Rescan v={v} />}
      {p.guide && <Guide v={v} />}
      {p.usage && <Usage v={v} />}
      {p.settings && <Settings v={v} />}
      {p.more && <More v={v} />}
      {p.kit && <Kit v={v} />}
    </Shell>
  );
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>);
