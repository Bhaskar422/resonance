import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '../styles.css';
import { makeStore } from '../lib/store.js';
import Site from './Site.jsx';

const store = makeStore('site');
store.mount();

function Root() {
  const v = store.useVals();
  return <Site v={v} />;
}

createRoot(document.getElementById('root')).render(<StrictMode><Root /></StrictMode>);
