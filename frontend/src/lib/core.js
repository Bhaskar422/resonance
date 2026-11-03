/* Resonance data layer and view-models, ported from the design handoff.
   Live mode talks to the FastAPI backend that serves this page (same origin);
   Sample mode shows the labelled sample and demo data. Switched in Settings. */
import SAMPLE_FAN from './sample-fan.json';

export const CONFIG = {
  API_BASE: '',
  BUDGET_USD: 150,
  POLL_MS: 1000,
  SAMPLE_LABEL: 'Sample run on generated test footage',
  DEMO_LABEL: 'Demo data',
};

/* ---------------- formatting ---------------- */
const MINUS = '\u2212';
const wait = ms => new Promise(r => setTimeout(r, ms));
const fx = (n, d = 2) => (n == null || isNaN(n)) ? '—' : Number(n).toFixed(d);
const sgn = (n, d = 1) => n == null ? '—' : (n < 0 ? MINUS : n > 0 ? '+' : '') + Math.abs(n).toFixed(d);
const money = (n, d = 3) => '$' + (n || 0).toFixed(d);
const int = n => n == null ? '—' : Math.round(n).toLocaleString('en-US');
const cap = s => s ? s[0].toUpperCase() + s.slice(1) : '';
const nice = s => cap((s || '').replace(/_/g, ' '));  // fault enums arrive as snake_case
const slug = s => (s || 'machine').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const nowS = () => Date.now() / 1000;
function ago(t) { const s = nowS() - t; if (s < 90) return 'just now'; if (s < 3600) return Math.round(s / 60) + ' min ago'; if (s < 86400) return Math.round(s / 3600) + ' h ago'; const d = Math.round(s / 86400); return d + (d === 1 ? ' day ago' : ' days ago'); }
const dateL = t => new Date(t * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
const timeL = t => new Date(t * 1000).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
const stampId = t => { const d = new Date(t * 1000), p = n => String(n).padStart(2, '0'); return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`; };
const tint = (c, p = 15) => `color-mix(in oklch, ${c} ${p}%, transparent)`;

const SEV = { normal: ['Normal', 'var(--sev-normal)', 0], monitor: ['Monitor', 'var(--sev-monitor)', 1], act_soon: ['Act soon', 'var(--sev-act)', 2], stop_now: ['Stop now', 'var(--sev-stop)', 3] };
export function sev(k) { const s = SEV[k] || ['Not diagnosed', 'var(--fg-3)', -1]; return { sevKey: k || 'none', sevLabel: s[0], sevColor: s[1], sevTint: tint(s[1]), rank: s[2] }; }
const SRC = { spectrum: ['Spectrum', 'SPEC', 'var(--c1)'], harmonics: ['Harmonics', 'HARM', 'var(--c1)'], magnified_video: ['Magnified video', 'MAG', 'var(--c2)'], original_video: ['Original video', 'VID', 'var(--c2)'], camera_reference: ['Camera reference', 'CAM', 'var(--c2)'], audio: ['Audio', 'AUD', 'var(--c3)'], accelerometer: ['Accelerometer', 'ACC', 'var(--c3)'], manual: ['Manual', 'MAN', 'var(--c4)'] };
const src = k => { const s = SRC[k] || [cap((k || '').replace(/_/g, ' ')), 'SRC', 'var(--fg-3)']; return { srcKey: k, srcLabel: s[0], srcCode: s[1], srcColor: s[2], srcTint: tint(s[2], 14) }; };
const STRIPE = 'repeating-linear-gradient(135deg, var(--stripe-a) 0 9px, var(--stripe-b) 9px 18px)';

/* ================= SAMPLE DATA =================
   Desk fan = real pipeline output on generated test footage.
   Everything flagged _demo is invented for layout. */
const T0 = Math.floor(nowS());
const DY = 86400;
const harm = (f, amps, snrs) => [1, 2, 3, 4, 5, 6].map((o, i) => { const a = amps[i] || 0, p = a > 0; return { order: o, expected_hz: +(f * o).toFixed(4), present: p, relative_amplitude: p ? +(a / amps[0]).toFixed(4) : 0, peak: p ? { freq_hz: +(f * o).toFixed(4), amplitude: a, snr: snrs[i] } : null }; });
const vib = (f, amps, snrs, dir) => ({ dominant: { freq_hz: f, amplitude: amps[0], snr: snrs[0] }, dominant_cpm: +(f * 60).toFixed(2), direction_deg: dir, spectral_resolution_hz: 0.0167, harmonics: harm(f, amps, snrs), top_peaks: amps.map((a, i) => a > 0 ? { freq_hz: +(f * (i + 1)).toFixed(4), amplitude: a, snr: snrs[i] } : null).filter(Boolean) });
const maskOf = (prompt, conf, area, ex) => ({ prompt, source: 'SAM 3.1', detections: [{ box: [212, 148, 688, 866], area_px: Math.round(area * 1.08), confidence: conf }], measured_area_px: area, fast_motion_excluded_fraction: ex });
const ev = (source, detail) => ({ source, detail });
const fault = (fault_type, likelihood, frequency_hz, harmonic_relation, sup, con) => ({ fault_type, likelihood, frequency_hz, harmonic_relation, supporting_evidence: sup.map(x => ev(x[0], x[1])), contradicting_evidence: con });
const act = (step, where, manual_page = null) => ({ step, where, manual_page });
const cite = (page, quote, relevance, verified, match_score) => ({ page, quote, relevance, verified, found_on_page: verified ? page : null, match_score });

// The desk fan is real pipeline output on generated test footage (scripts/export_sample.py).
const FAN_A = SAMPLE_FAN.before.run, FAN_B = SAMPLE_FAN.after.run;
const FAN_COMPARE = normalizeCompare(SAMPLE_FAN.after.detail.compare);

const DEMO = [
  { prompt: 'pump', machine: 'Workshop pump P-2', f: 29.6, h: [1, 0.93, 0.17], dir: 30, snr: 880, runs: [28, 19, 9, 3], amps: [0.21, 0.27, 0.33, 0.41], sevs: [null, null, null, 'act_soon'], cost: 0.022,
    warnings: ['Camera shake detected in 6% of frames; compensated using the camera reference.'],
    diag: { summary: 'Pump vibrates at 1x (29.6 Hz) with a 2x nearly as strong, the signature of angular misalignment at the coupling. Amplitude has doubled over four weeks.', primary_fault: 'misalignment', confidence: 0.72,
      rotation: { rated_rpm: 1750, rated_rpm_source: 'nameplate', measured_hz: 29.6, relation: '1x = 1776 RPM, within 1.5% of rated' },
      faults: [fault('misalignment', 0.72, 59.2, '2x', [['harmonics', '2x at 93% of 1x, typical of angular misalignment'], ['spectrum', 'clean peaks at 29.6 and 59.2 Hz'], ['magnified_video', 'coupling end moves out of phase with motor end']], ['No axial view to confirm axial motion']), fault('imbalance', 0.30, 29.6, '1x', [['spectrum', '1x is the largest single peak']], ['2x nearly equals 1x, unlike pure imbalance']), fault('mechanical looseness', 0.18, 29.6, '1x–3x', [['harmonics', '3x present at 17% of 1x']], ['No 4x–6x orders', 'Base bolts appear stationary'])],
      recommended_actions: [act('Lock out the pump, then check shaft alignment at the coupling with a straightedge or dial indicator', 'coupling between motor and pump', 12), act('Inspect the coupling insert for wear; replace if cracked', 'flexible coupling', 14), act('Re-torque motor foot bolts and shim any soft foot', 'motor feet')],
      action_point: { x: 520, y: 560, label: 'coupling guard' }, manual_citations: [cite(12, 'Check alignment after any maintenance that disturbs the motor or pump mounting.', 'Supports step 1', true, 0.91)],
      rescan_expectation: '2x should fall below 30% of 1x after alignment.', uncertainties: ['Camera shake compensated in 6% of frames.'] } },
  { prompt: 'blower', machine: 'HVAC blower B-1', f: 24.8, h: [1, 0.4, 0.25, 0.16, 0.09], dir: 90, snr: 1210, runs: [21, 12, 2], amps: [0.62, 0.88, 1.31], sevs: [null, null, 'stop_now'], cost: 0.024,
    warnings: [],
    diag: { summary: 'A harmonic series from 1x to 5x with the motor plate lifting each revolution points to structural looseness. Amplitude is up 110% in three weeks. Stop the blower and secure the mount.', primary_fault: 'mechanical looseness', confidence: 0.71,
      rotation: { rated_rpm: 1500, rated_rpm_source: 'nameplate', measured_hz: 24.8, relation: '1x = 1488 RPM, matches rated' },
      faults: [fault('mechanical looseness', 0.74, 24.8, '1x–5x series', [['harmonics', 'harmonic series 1x–5x present'], ['magnified_video', 'motor mount plate visibly lifts each revolution'], ['audio', 'rattle at running speed in the recording']], []), fault('imbalance', 0.41, 24.8, '1x', [['spectrum', '1x dominant at 1.31 px']], ['Strong 3x–5x is not typical of imbalance']), fault('bearing wear', 0.22, 74.4, '3x', [['spectrum', 'slightly raised noise floor above 60 Hz']], ['No non-synchronous peaks resolved'])],
      recommended_actions: [act('Stop the blower and lock out power', 'main disconnect', 3), act('Tighten motor mount plate bolts and check for cracked welds', 'motor mount plate', 9), act('Check the blower wheel set screw on the shaft', 'wheel hub', 11)],
      action_point: { x: 610, y: 720, label: 'motor mount plate' }, manual_citations: [cite(9, 'Motor mounting bolts should be checked for tightness every 6 months.', 'Supports step 2', true, 0.88), cite(11, 'Set screws must be torqued to specification.', 'Step 3', false, 0.37)],
      rescan_expectation: '3x–5x should disappear and 1x should fall below 0.5 px.', uncertainties: ['No accelerometer recording for cross-check.'] } },
  { prompt: 'compressor', machine: 'Air compressor C-1', f: 14.2, h: [1, 0.19], dir: 0, snr: 540, runs: [16, 5], amps: [0.27, 0.31], sevs: [null, 'monitor'], cost: 0.012,
    warnings: [],
    diag: { summary: 'Moderate 1x at 14.2 Hz with belt flutter on the slack side. Likely sheave misalignment or low belt tension. Not urgent; check at next service.', primary_fault: 'belt / sheave misalignment', confidence: 0.58,
      rotation: { rated_rpm: 860, rated_rpm_source: 'pump label', measured_hz: 14.2, relation: '1x = 852 RPM, matches compressor pulley speed' },
      faults: [fault('belt / sheave misalignment', 0.58, 14.2, '1x', [['spectrum', '1x at 14.2 Hz with low 2x'], ['magnified_video', 'belt flutters on the slack side']], ['No belt-frequency peak resolved']), fault('imbalance', 0.33, 14.2, '1x', [['spectrum', '1x dominant']], ['Belt flutter suggests a drive issue'])],
      recommended_actions: [act('Check belt tension and sheave alignment', 'drive belt and pulleys', 21)],
      action_point: { x: 300, y: 380, label: 'drive belt' }, manual_citations: [],
      rescan_expectation: '1x should fall below 0.2 px.', uncertainties: ['Belt frequency is below the spectral resolution of a 10 s clip.'] } },
  { prompt: 'bench grinder', machine: 'Bench grinder', f: 49.9, h: [1, 0.13], dir: 180, snr: 310, runs: [14, 1], amps: [0.088, 0.093], sevs: [null, null], cost: 0, warnings: [], diag: null },
];

function buildSample() {
  const runs = [], details = {};
  const fan = (x, tpl) => {
    details[x.run] = { _sample: true, _tpl: tpl, ...normalizeDetail(x.detail) };
    runs.push({ run: x.run, created: x.created, input: x.input, prompt: x.prompt, machine: x.machine, freq_hz: x.freq_hz, fault: x.fault, severity: x.severity, thumb: x.thumb, _sample: true });
  };
  fan(SAMPLE_FAN.after, 'B');
  fan(SAMPLE_FAN.before, 'A');
  for (const m of DEMO) {
    m.runs.forEach((d, i) => {
      const created = T0 - d * DY - 3600 * (i + 2), id = stampId(created) + '-' + slug(m.prompt), a = m.amps[i], s = m.sevs[i];
      const amps = m.h.map(r => +(r * a).toFixed(4)), snrs = m.h.map((r, j) => Math.round(m.snr * r * (a / m.amps[m.amps.length - 1]) / (j + 1)));
      const last = i === m.runs.length - 1;
      const dg = s && m.diag ? { diagnosis: { machine: m.machine, severity: s, fixed_state_description: '', fix_image_prompt: '', ...m.diag }, api_cost_usd: m.cost } : null;
      details[id] = { _demo: true, report: { vibration: vib(m.f, amps, snrs, m.dir), mask: maskOf(m.prompt, 0.9, 150000 + i * 900, 0.03), accelerometer: null, warnings: last ? m.warnings : [], api_cost_usd: 0.002 }, diagnosis: dg, visualize: null, compare: null, files: {} };
      runs.push({ run: id, created, input: `${slug(m.prompt)}_${i + 1}.mov`, prompt: m.prompt, freq_hz: m.f, fault: dg ? dg.diagnosis.primary_fault : null, severity: s, thumb: null, _demo: true });
    });
  }
  runs.sort((a, b) => b.created - a.created);
  return { runs, details };
}
const SAMPLE = buildSample();

/* -------- PENDING BACKEND (/api/costs, /api/machines) — mocked/derived here -------- */
function mockCosts() {
  const out = [];
  for (const r of SAMPLE.runs) {
    const d = SAMPLE.details[r.run];
    out.push({ time: r.created + 40, model: 'SAM 3.1', endpoint: 'segment', cost_usd: d.report.api_cost_usd, run_id: r.run });
    if (d.diagnosis) out.push({ time: r.created + 95, model: 'Muse Spark', endpoint: 'diagnose', cost_usd: d.diagnosis.api_cost_usd, run_id: r.run });
    if (d.visualize) out.push({ time: r.created + 140, model: 'Muse Image', endpoint: 'visualize', cost_usd: d.visualize.api_cost_usd, run_id: r.run });
  }
  const b = SAMPLE.runs.find(r => r.run === FAN_B);
  out.push({ time: b.created + 600, model: 'Muse Spark', endpoint: 'compare', cost_usd: 0.004, run_id: FAN_B });
  return out.sort((a, b) => b.time - a.time);
}

/* -------- live payloads -> the shapes the view-models expect -------- */
// report.api_cost_usd is {this_run, all_time, calls}; SAM boxes are key-frame pixels;
// the accelerometer block is accel.Comparison.to_dict(); compare harmonics repeat 1x.
export function normalizeDetail(d) {
  const R = { ...(d.report || {}) };
  if (R.api_cost_usd && typeof R.api_cost_usd === 'object') R.api_cost_usd = R.api_cost_usd.this_run || 0;
  const vw = R.video && R.video.width, vh = R.video && R.video.height;
  if (R.mask && vw && vh) {
    R.mask = { ...R.mask, source: R.mask.source && R.mask.source.startsWith('sam') ? 'SAM 3.1' : R.mask.source, detections: (R.mask.detections || []).map(x => x.box ? { ...x, box: [x.box[0] / vw * 1000, x.box[1] / vh * 1000, x.box[2] / vw * 1000, x.box[3] / vh * 1000] } : x) };
  }
  const A = R.accelerometer;
  if (A && A.video_hz != null) {
    const pk = A.accel_match || A.accel_dominant || {};
    R.accelerometer = { source: 'phyphox', dominant_hz: pk.freq_hz, delta_hz: pk.freq_hz != null ? Math.abs(pk.freq_hz - A.video_hz) : null, agrees: !!(A.verifiable && A.accel_match), note: A.note };
  }
  return { ...d, report: R, compare: normalizeCompare(d.compare) };
}
export function normalizeCompare(c) {
  return c ? { ...c, harmonics: (c.harmonics || []).filter(h => h.order > 1) } : c;
}

/* ---------------- spectrum synthesis (sample mode only; live uses spectrum.png) ---------------- */
function rng(seed) { let s = seed >>> 0 || 1; return () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296; }
const LO = -4.6, HI = 0.4, FMAX = 120, W = 600, H = 200;
const yOf = a => Math.max(2, Math.min(H, H - (Math.log10(Math.max(a, 1e-5)) - LO) / (HI - LO) * H));
function spectrum(peaks, seed = 7, floor = 0.00018) {
  const N = 900, r = rng(seed), pts = []; let nz = 1;
  for (let i = 0; i <= N; i++) { const f = FMAX * i / N; nz = nz * 0.82 + (0.55 + r() * 0.9) * 0.18; let a = floor * nz * (1 + 4 * Math.exp(-f / 5)); for (const p of peaks) { const d = (f - p.f) / 0.22; a += p.a * Math.exp(-d * d); } pts.push((W * i / N).toFixed(1) + ' ' + yOf(a).toFixed(1)); }
  const line = 'M' + pts.join(' L');
  return { line, area: line + ` L${W} ${H} L0 ${H} Z` };
}
// Measured spectrum from the API ({fmax, amp[]}, max-pooled bins) on the same log scale.
function realSpec(sp, fm = sp.fmax) {
  const n = sp.amp.length, pts = [];
  for (let i = 0; i < n; i++) { const f = (i + 0.5) / n * sp.fmax; if (f > fm) break; pts.push((W * f / fm).toFixed(1) + ' ' + yOf(Math.max(sp.amp[i], 1e-5)).toFixed(1)); }
  const line = 'M' + pts.join(' L');
  return { line, area: line + ` L${W} ${H} L0 ${H} Z` };
}
const peaksOf = V => (V.harmonics || []).filter(h => h.present && h.peak).map(h => ({ f: h.peak.freq_hz, a: h.peak.amplitude }));
const specCache = {};
function specFor(id, V) { return specCache[id] || (specCache[id] = spectrum(peaksOf(V), id.length * 13 + 5)); }

/* ---------------- canvas instruments ---------------- */
const css = (el, n, d) => (getComputedStyle(el).getPropertyValue(n) || '').trim() || d;
const reduceMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
function canvasLoop(cv, draw) {
  const ctx = cv.getContext('2d'); let w = 0, h = 0, raf = 0, alive = true;
  const fit = () => { const r = cv.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1); w = r.width; h = r.height; cv.width = Math.max(1, w * dpr); cv.height = Math.max(1, h * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); };
  const ro = new ResizeObserver(fit); ro.observe(cv); fit();
  const t0 = performance.now();
  try { draw(ctx, w, h, 0.35); } catch (e) {}
  const tick = now => { if (!alive) return; draw(ctx, w, h, (now - t0) / 1000); if (!reduceMotion()) raf = requestAnimationFrame(tick); };
  raf = requestAnimationFrame(tick);
  return () => { alive = false; cancelAnimationFrame(raf); ro.disconnect(); };
}
function attachWave(cv, o = {}) {
  let mx = -1, g = 0, lx = 0;
  const mm = e => { const r = cv.getBoundingClientRect(); mx = e.clientX - r.left; }, ml = () => { mx = -1; };
  cv.addEventListener('pointermove', mm); cv.addEventListener('pointerleave', ml);
  const stop = canvasLoop(cv, (ctx, w, h, t) => {
    ctx.clearRect(0, 0, w, h);
    const sig = css(cv, '--signal', '#5ef0a0'), dim = css(cv, '--signal-dim', 'rgba(94,240,160,.3)'), grid = css(cv, '--grid', 'rgba(255,255,255,.06)');
    const mid = h / 2, lens = Math.max(90, w * (o.lens || 0.14)), base = o.base || 1.1, period = o.period || 120;
    const target = mx >= 0 ? mx : w * (0.5 + 0.38 * Math.sin(t * 0.45));
    lx += (target - lx) * 0.12; g += ((mx >= 0 ? 1 : (o.idle ?? 0.85)) - g) * 0.06;
    if (o.grid) { ctx.strokeStyle = grid; ctx.lineWidth = 1; for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x + .5, 0); ctx.lineTo(x + .5, h); ctx.stroke(); } for (let y = mid % 40; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y + .5); ctx.lineTo(w, y + .5); ctx.stroke(); } }
    const s = x => Math.sin(2 * Math.PI * (x / period) - t * 5.2) + 0.286 * Math.sin(4 * Math.PI * (x / period) - t * 10.4 + 0.6);
    ctx.lineWidth = 1; ctx.strokeStyle = dim; ctx.beginPath(); for (let x = 0; x <= w; x += 2) { const y = mid + base * s(x); x ? ctx.lineTo(x, y) : ctx.moveTo(x, y); } ctx.stroke();
    ctx.lineWidth = o.width || 2; ctx.strokeStyle = sig; ctx.shadowColor = sig; ctx.shadowBlur = o.glow ?? 10; ctx.beginPath();
    for (let x = 0; x <= w; x += 2) { const k = g * Math.exp(-Math.pow((x - lx) / lens, 2)); const y = mid + base * (1 + 19 * k) * s(x) * Math.min(1, (h * 0.36) / (base * 20)); x ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
    ctx.stroke(); ctx.shadowBlur = 0;
    if (o.lensMarks !== false) { ctx.strokeStyle = dim; ctx.setLineDash([3, 4]); [lx - lens, lx + lens].forEach(x => { ctx.beginPath(); ctx.moveTo(x, 10); ctx.lineTo(x, h - 10); ctx.stroke(); }); ctx.setLineDash([]); ctx.fillStyle = sig; ctx.font = '600 11px ' + css(cv, '--mono-font', 'monospace'); ctx.textAlign = 'center'; ctx.fillText('×20', lx, 18); }
  });
  return () => { stop(); cv.removeEventListener('pointermove', mm); cv.removeEventListener('pointerleave', ml); };
}
function attachMotion(cv, getMode) {
  const trails = [[], []];
  return canvasLoop(cv, (ctx, w, h, t) => {
    ctx.clearRect(0, 0, w, h);
    const mode = getMode(), sig = css(cv, '--signal', '#5ef0a0'), line = css(cv, '--line-2', 'rgba(255,255,255,.18)'), fg = css(cv, '--fg-2', '#aaa'), mono = css(cv, '--mono-font', 'monospace');
    const P = mode === 'side' ? [['ORIGINAL', 1, 1], ['MAGNIFIED ×20', 20, 1]] : mode === 'original' ? [['ORIGINAL', 1, 1]] : mode === 'compare' ? [['BEFORE ×20', 20, 1], ['AFTER ×20', 20, 0.111]] : [['MAGNIFIED ×20', 20, 1]];
    const pw = w / P.length;
    P.forEach(([label, gain, amp], i) => {
      const cx = pw * i + pw / 2, cy = h / 2 + 8, R = Math.min(pw, h) * 0.27, scale = R / 90;
      const d = Math.sin(2 * Math.PI * 1.4 * t) * 0.5 * gain * amp * scale + 0.143 * gain * amp * scale * Math.sin(2 * Math.PI * 2.8 * t + .6);
      if (i) { ctx.strokeStyle = line; ctx.beginPath(); ctx.moveTo(pw * i + .5, 0); ctx.lineTo(pw * i + .5, h); ctx.stroke(); }
      ctx.strokeStyle = line; ctx.lineWidth = 1; ctx.setLineDash([2, 4]); ctx.beginPath(); ctx.moveTo(cx, cy - R * 1.5); ctx.lineTo(cx, cy + R * 1.5); ctx.moveTo(cx - R * 1.5, cy); ctx.lineTo(cx + R * 1.5, cy); ctx.stroke(); ctx.setLineDash([]);
      const tr = trails[i] || (trails[i] = []); tr.push(d); if (tr.length > 26) tr.shift();
      tr.forEach((v, k) => { ctx.globalAlpha = (k / tr.length) * 0.25; ctx.strokeStyle = sig; ctx.beginPath(); ctx.arc(cx + v, cy, R, 0, Math.PI * 2); ctx.stroke(); }); ctx.globalAlpha = 1;
      ctx.strokeStyle = sig; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx + d, cy, R, 0, Math.PI * 2); ctx.stroke();
      ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(cx + d, cy, R * 0.16, 0, Math.PI * 2); ctx.stroke();
      for (let b = 0; b < 3; b++) { const a = t * 7 + b * 2.094; ctx.beginPath(); ctx.moveTo(cx + d + Math.cos(a) * R * 0.2, cy + Math.sin(a) * R * 0.2); ctx.lineTo(cx + d + Math.cos(a) * R * 0.92, cy + Math.sin(a) * R * 0.92); ctx.stroke(); }
      ctx.fillStyle = fg; ctx.font = '600 11px ' + mono; ctx.textAlign = 'left'; ctx.fillText(label, pw * i + 14, 22);
      ctx.textAlign = 'right'; ctx.fillText((0.5009 * amp * (gain > 1 ? 20 : 1)).toFixed(2) + ' px', pw * (i + 1) - 14, 22);
    });
  });
}
function reveal(el) {
  if (!el || el.__rv) return; el.__rv = 1;
  if (el.getBoundingClientRect().top < innerHeight * 0.95 || reduceMotion()) return;
  el.style.opacity = '0'; el.style.transform = 'translateY(36px)'; el.style.transition = 'opacity 1s cubic-bezier(.2,.7,.2,1), transform 1s cubic-bezier(.2,.7,.2,1)';
  const io = new IntersectionObserver(es => { for (const e of es) if (e.isIntersecting) { el.style.opacity = '1'; el.style.transform = 'none'; io.disconnect(); } }, { threshold: 0.12 });
  io.observe(el);
}
function scrollScale(el) {
  if (!el) return () => {};
  const on = () => { const r = el.getBoundingClientRect(); const p = Math.max(0, Math.min(1, 1 - (r.top - innerHeight * 0.1) / (innerHeight * 0.7))); el.style.transform = `scale(${(0.88 + 0.12 * p).toFixed(4)})`; el.style.borderRadius = `${Math.round(28 * (1 - p))}px`; };
  addEventListener('scroll', on, { passive: true }); on();
  return () => removeEventListener('scroll', on);
}
function mkRef(attach) { let cleanup = null; return el => { if (cleanup) { cleanup(); cleanup = null; } if (el) cleanup = attach(el) || null; }; }

/* ---------------- pipeline stages ---------------- */
export const STAGES = [
  ['upload', 'Upload', 'Uploading your video…', 0, 1.0],
  ['prepare', 'Prepare', 'Reading frames and checking the clip…', 0, 0.9],
  ['mask', 'Mask', 'Finding the machine with SAM 3.1…', 0.002, 1.6],
  ['measure', 'Measure', 'Measuring motion in every masked pixel…', 0, 1.4],
  ['accel', 'Accelerometer', 'Cross-checking against the phyphox recording…', 0, 0.7],
  ['magnify', 'Magnify', 'Magnifying the motion about 20×…', 0, 1.5],
  ['plot', 'Plot', 'Drawing the spectrum and harmonics…', 0, 0.6],
  ['diagnose', 'Diagnose', 'Diagnosing the fault with Muse Spark…', 0.021, 2.2],
  ['visualize', 'Visualize', 'Showing the fix on your frame with Muse Image…', 0.012, 1.8],
  ['done', 'Done', 'Report ready.', 0, 0.3],
];
const PIPE = [
  ['Segment', 'SAM 3.1 isolates the machine so only its pixels are measured.', 'SAM 3.1'],
  ['Measure', 'Frequency in Hz and CPM, amplitude in px, harmonics 1x–6x with SNR.', 'on-device math'],
  ['Magnify', 'Motion amplified about 20× so invisible vibration becomes obvious.', 'motion magnification'],
  ['Diagnose', 'Ranked faults with supporting and contradicting evidence, by source.', 'Muse Spark'],
  ['Visualize', 'Where to act, and what the machine looks like after the fix.', 'Muse Image'],
  ['Rescan', 'Film again after the repair. Proof, in dB, that it worked.', 'compare'],
];
const FAQ = [
  ['How accurate is a phone camera?', 'On generated test footage Resonance measured 19.0001 Hz against a 19.000 Hz ground truth. In the field, a 240 fps clip resolves frequencies up to 120 Hz at about 0.02 Hz resolution for a 10-second clip. Attach a phyphox accelerometer recording and it cross-checks the result.'],
  ['Does it replace a vibration analyst?', 'It replaces the first visit. You get a measured spectrum, a ranked diagnosis with evidence for and against, and repair steps checked against the manual. For critical assets, share the report with your analyst; everything they need is in it.'],
  ['What does it cost to run?', 'About $0.04 per analysis in model calls: segmentation with SAM 3.1, diagnosis with Muse Spark and an optional fix image with Muse Image. Measurement and magnification run locally, so they cost nothing.'],
  ['Which machines work best?', 'Rotating equipment running between about 5 and 120 Hz (300–7,200 RPM): fans, pumps, motors, compressors, blowers and grinders. The machine should fill about a third of the frame.'],
  ['Are the manual quotes real?', 'Every quote is searched for in the PDF you attach. If it is found on the cited page it is badged verified, with a match score. If it is not found, it is marked unverified, never hidden.'],
  ['Is it open source?', 'Yes. Resonance is licensed under Apache-2.0. Run the backend yourself and bring your own model keys.'],
];

/* ================= the app ================= */
export function createApp(opts = {}) {
  const ID = opts.id || 'x', MODE = opts.mode || 'app';
  const ON = opts.on || { bg: 'var(--accent)', fg: 'var(--on-accent)', bd: 'var(--accent)' };
  const OFF = opts.off || { bg: 'transparent', fg: 'var(--fg-2)', bd: 'var(--line)' };
  const tab = on => on ? ON : OFF;
  const ld = (k, d) => { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } };
  const sv = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };
  const emit = () => opts.onChange && opts.onChange();
  const freshAz = () => ({ step: 1, file: null, fileName: '', fileSize: '', resolution: '', previewUrl: '', sampleClip: false, prompt: '', machine: '', fps: 0, duration: 10, accel: null, accelName: '', manual: null, manualName: '', diagnose: S ? S.defaults.diagnose : true, visualize: S ? S.defaults.visualize : true, dragging: false, running: false, st: {}, times: {}, error: null, simFail: false, failedOnce: false, rescanOf: null, jobId: null, t0: 0 });
  let S = null;
  S = {
    route: { name: 'dashboard', id: null, q: {} },
    theme: ld(`resonance:${ID}:theme`, opts.defaultTheme || 'dark'),
    dataMode: ld('resonance:dataMode', 'live'),
    units: ld('resonance:units', 'hz'),
    defaults: ld('resonance:defaults', { diagnose: true, visualize: true }),
    runs: null, runsLoading: false, runsError: null, details: {}, detailErr: {}, detailBusy: {},
    costs: null, costsLive: false, health: null, search: '', toast: null,
    rep: { video: 'side', fault: 0, slider: 50 },
    dx: {},  // one-click diagnosis of an existing run, by run id
    rs: { machine: null, before: null, after: null, result: null, plot: null, loading: false, error: null, spark: true },
    az: null, faq: 0, pipe: 0, menu: false,
  };
  S.az = freshAz();
  const live = () => S.dataMode === 'live' && MODE === 'app';
  const base = () => CONFIG.API_BASE.replace(/\/$/, '');
  const abs = u => !u ? u : (/^(https?:|blob:|data:)/.test(u) ? u : base() + (u[0] === '/' ? '' : '/') + u);
  const origin = () => base() || location.origin;
  async function jf(path, init) { const r = await fetch(base() + path, init); if (!r.ok) { let m = `${r.status} ${r.statusText}`; try { const j = await r.json(); m = j.detail || j.error || m; } catch (e) {} throw new Error(m); } return r.json(); }
  const api = {
    async runs() { if (!live()) { await wait(420); return SAMPLE.runs.slice(); } return (await jf('/api/runs')).map(r => ({ ...r, thumb: abs(r.thumb) })); },
    async run(id) { if (!live()) { await wait(280); const d = SAMPLE.details[id]; if (!d) throw new Error(`Run “${id}” was not found.`); return d; } const d = await jf('/api/runs/' + encodeURIComponent(id)); const files = {}; for (const k in d.files || {}) files[k] = abs(d.files[k]); return normalizeDetail({ ...d, files }); },
    async analyze(fd) { return jf('/api/analyze', { method: 'POST', body: fd }); },
    async job(id) { return jf('/api/jobs/' + encodeURIComponent(id)); },
    async diagnoseRun(id, fd) { return jf('/api/runs/' + encodeURIComponent(id) + '/diagnose', { method: 'POST', body: fd }); },
    async compare(before, after, spark) { if (!live()) { await wait(1100); return { result: sampleCompare(before, after, spark), plot: null }; } const r = await jf('/api/compare', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ before, after, spark }) }); return { ...r, result: normalizeCompare(r.result), plot: abs(r.plot) }; },
    async health() { return jf('/api/health'); },
    // PENDING BACKEND: GET /api/costs — falls back to the mock ledger until it exists.
    async costs() { if (live()) { try { const c = await jf('/api/costs'); S.costsLive = true; return c; } catch (e) {} } S.costsLive = false; return mockCosts(); },
  };
  function sampleCompare(b, a, spark) {
    const B = S.details[b] || SAMPLE.details[b], A = S.details[a] || SAMPLE.details[a];
    if (!B || !A) throw new Error('Both runs must be loaded to compare.');
    if (B._tpl === 'A' && A._tpl === 'B') return { ...FAN_COMPARE, before_run: b, after_run: a, spark: spark ? FAN_COMPARE.spark : null };
    const vb = B.report.vibration, va = A.report.vibration, pc = (x, y) => +((y / x - 1) * 100).toFixed(1), db = (x, y) => +(20 * Math.log10(y / x)).toFixed(1);
    const f = vb.dominant.freq_hz, b1 = vb.dominant.amplitude, a1 = va.dominant.amplitude;
    const hs = vb.harmonics.filter(h => h.order > 1 && h.present).map(h => { const ah = va.harmonics.find(x => x.order === h.order); const bp = h.peak.amplitude, ap = ah && ah.peak ? ah.peak.amplitude : bp * 0.02; return { order: h.order, freq_hz: h.expected_hz, before_px: bp, after_px: ap, change_pct: pc(bp, ap), change_db: db(bp, ap) }; });
    const rms = v => Math.sqrt(v.harmonics.filter(h => h.peak).reduce((s, h) => s + h.peak.amplitude ** 2, 0) / 2);
    const rb = rms(vb), ra = rms(va), ch = pc(b1, a1);
    return { before_run: b, after_run: a, fault_frequency_hz: f, fundamental: { before_px: b1, after_px: a1, change_pct: ch, change_db: db(b1, a1) }, harmonics: hs, rms_displacement: { before_px: +rb.toFixed(4), after_px: +ra.toFixed(4), change_pct: pc(rb, ra), change_db: db(rb, ra) }, verdict: ch <= -70 ? 'resolved' : ch <= -20 ? 'improved' : ch < 15 ? 'no_change' : 'worse', warnings: [], spark: null };
  }

  /* ---- loading ---- */
  async function loadRuns(force) {
    if (S.runsLoading || (S.runs && !force)) return;
    S.runsLoading = true; S.runsError = null; emit();
    try { S.runs = await api.runs(); S.runsLoading = false; emit(); await Promise.all(S.runs.map(r => loadDetail(r.run))); }
    catch (e) { S.runsLoading = false; S.runsError = e.message || String(e); emit(); }
  }
  async function loadDetail(id, force) {
    if (!id || (!force && (S.details[id] || S.detailBusy[id]))) return;
    S.detailBusy[id] = true; delete S.detailErr[id]; emit();
    try { S.details[id] = await api.run(id); } catch (e) { S.detailErr[id] = e.message || String(e); }
    S.detailBusy[id] = false; emit();
  }
  async function loadCosts() { S.costs = await api.costs(); emit(); }
  async function loadHealth() { if (!live()) return; try { S.health = await api.health(); } catch (e) { S.health = { ok: false }; } emit(); }
  function resetData() { S.runs = null; S.details = {}; S.detailErr = {}; S.detailBusy = {}; S.costs = null; S.health = null; S.rs.result = null; loadRuns(true); loadCosts(); loadHealth(); onRoute(); }

  /* ---- toast ---- */
  let toastT = 0;
  function toast(msg, kind = 'ok') { S.toast = { msg, kind }; emit(); clearTimeout(toastT); toastT = setTimeout(() => { S.toast = null; emit(); }, 3200); }

  /* ---- routing ---- */
  const KNOWN = ['dashboard', 'machines', 'analyze', 'runs', 'rescan', 'guide', 'usage', 'settings', 'more', 'kit'];
  function parse() {
    const h = (location.hash || '').replace(/^#\/?/, ''); const [p, qs = ''] = h.split('?'); const parts = p.split('/').filter(Boolean); const q = Object.fromEntries(new URLSearchParams(qs)); const n = parts[0] || 'dashboard';
    if (n === 'runs' && parts[1]) return { name: 'report', id: decodeURIComponent(parts[1]), q };
    if (n === 'machines' && parts[1]) return { name: 'machine', id: decodeURIComponent(parts[1]), q };
    return { name: KNOWN.includes(n) ? n : 'dashboard', id: null, q };
  }
  function onRoute() {
    const r = S.route;
    if (r.name === 'report') { loadDetail(r.id); S.rep.fault = 0; }
    if (r.name === 'analyze' && r.q.rescan && S.az.rescanOf !== r.q.rescan && !S.az.running) prefillRescan(r.q.rescan);
    if (r.name === 'rescan' && r.q.before && r.q.after && (S.rs.before !== r.q.before || S.rs.after !== r.q.after || !S.rs.result)) { S.rs.before = r.q.before; S.rs.after = r.q.after; S.rs.machine = null; runCompare(); }
  }
  const onHash = () => { if (MODE !== 'app') return; S.route = parse(); S.menu = false; S.search = ''; onRoute(); emit(); try { scrollTo({ top: 0 }); } catch (e) {} };
  const go = h => { location.hash = h; };

  /* ---- derived: machines ---- */
  function machinesData() {
    const runs = S.runs || [], g = {}, byPrompt = {};
    const sorted = runs.slice().sort((a, b) => a.created - b.created);
    const named = r => { const d = S.details[r.run]; return r.machine || (d && d.report && d.report.machine) || (d && d.diagnosis && d.diagnosis.diagnosis && d.diagnosis.diagnosis.machine) || null; };
    for (const r of sorted) { const n = named(r); if (n && r.prompt) byPrompt[r.prompt.toLowerCase()] = n; }
    for (const r of sorted) {
      const name = named(r) || byPrompt[(r.prompt || '').toLowerCase()] || cap(r.prompt || 'Unknown machine');
      const id = slug(name); (g[id] = g[id] || { id, name, runs: [] }).runs.push(r);
    }
    return Object.values(g).map(m => {
      m.runs.sort((a, b) => b.created - a.created);
      const amp = r => { const d = S.details[r.run]; return d ? d.report.vibration.dominant.amplitude : null; };
      const last = m.runs[0], prev = m.runs[1], rated = m.runs.find(r => r.severity);
      const a0 = amp(last), a1 = prev ? amp(prev) : null, ch = a0 != null && a1 ? (a0 / a1 - 1) * 100 : null;
      const trend = ch == null ? ['·', 'var(--fg-3)', 'First scan'] : ch < -10 ? ['↓', 'var(--sev-normal)', sgn(ch, 0) + '% vs last'] : ch > 10 ? ['↑', 'var(--sev-act)', sgn(ch, 0) + '% vs last'] : ['→', 'var(--fg-2)', 'Stable'];
      const pairs = m.runs.map(r => S.details[r.run] && S.details[r.run].compare).filter(Boolean);
      return { ...m, ...sev(rated && rated.severity), last, amp: a0, trend, pairs, demo: !!last._demo, sample: !!last._sample, fault: rated ? rated.fault : null };
    }).sort((a, b) => b.rank - a.rank || b.last.created - a.last.created);
  }
  const machineOf = (ms, runId) => ms.find(m => m.runs.some(r => r.run === runId));
  const freqMain = hz => S.units === 'cpm' ? int(hz * 60) + ' CPM' : fx(hz, 2) + ' Hz';
  const freqAlt = hz => S.units === 'cpm' ? fx(hz, 2) + ' Hz' : int(hz * 60) + ' CPM';
  const tag = r => r._sample ? CONFIG.SAMPLE_LABEL : r._demo ? CONFIG.DEMO_LABEL : '';
  const imgBg = url => url ? `center / cover no-repeat url("${url}")` : STRIPE;
  const thumbBg = r => imgBg(r.thumb);

  function runItem(r, ms) {
    const m = machineOf(ms, r.run), d = S.details[r.run];
    return { run: r.run, title: m ? m.name : cap(r.prompt), prompt: r.prompt, input: r.input, date: dateL(r.created), time: timeL(r.created), ago: ago(r.created), freq: r.freq_hz != null ? freqMain(r.freq_hz) : '—', freqAlt: r.freq_hz != null ? freqAlt(r.freq_hz) : '', amp: d ? fx(d.report.vibration.dominant.amplitude, 4) + ' px' : '…', fault: r.fault ? nice(r.fault) : 'No diagnosis', ...sev(r.severity), href: '#/runs/' + encodeURIComponent(r.run), tag: tag(r), hasTag: !!tag(r), thumb: thumbBg(r), isCompare: !!(d && d.compare) };
  }
  function machineItem(m) {
    return { id: m.id, name: m.name, href: '#/machines/' + m.id, freq: m.last.freq_hz != null ? freqMain(m.last.freq_hz) : '—', freqAlt: m.last.freq_hz != null ? freqAlt(m.last.freq_hz) : '', amp: m.amp != null ? fx(m.amp, 4) + ' px' : '—', ...sev(m.sevKey === 'none' ? null : m.sevKey), fault: m.fault ? nice(m.fault) : 'Not diagnosed', trend: m.trend[0], trendColor: m.trend[1], trendLabel: m.trend[2], ago: ago(m.last.created), count: m.runs.length + (m.runs.length === 1 ? ' run' : ' runs'), tag: tag(m.last), hasTag: !!tag(m.last), thumb: thumbBg(m.last), fixed: m.pairs.length > 0 };
  }

  /* ---- charts ---- */
  function lineChart(series, opt = {}) {
    const all = series.flatMap(s => s.pts); if (!all.length) return { series: [], ticks: [] };
    const t0 = opt.t0 ?? Math.min(...all.map(p => p[0])), t1 = opt.t1 ?? Math.max(...all.map(p => p[0])), vmax = Math.max(...all.map(p => p[1])) * 1.15 || 1;
    const X = t => 14 + (W - 28) * (t1 === t0 ? 0.5 : (t - t0) / (t1 - t0)), Y = v => H - 12 - (H - 28) * (v / vmax);
    return {
      series: series.map(s => ({ ...s, points: s.pts.map(p => X(p[0]).toFixed(1) + ',' + Y(p[1]).toFixed(1)).join(' '), dots: s.pts.map(p => ({ left: (X(p[0]) / W * 100).toFixed(2) + '%', top: (Y(p[1]) / H * 100).toFixed(2) + '%', label: fx(p[1], 3) + ' px · ' + dateL(p[0]), color: s.color, ...(p[2] || {}) })) })),
      ticks: [1, 0.5, 0].map(k => ({ label: fx(vmax / 1.15 * k * 1.15, 2), top: (Y(vmax * k) / H * 100).toFixed(1) + '%' })),
    };
  }
  const PAL = ['var(--c1)', 'var(--c2)', 'var(--c3)', 'var(--c4)', 'var(--c5)'];

  /* ---- report VM ---- */
  function reportVM(id, details, runs) {
    const d = details[id];
    if (!d) { const err = S.detailErr[id]; return { ok: false, loading: !err, failed: !!err, error: err || '', retry: () => loadDetail(id, true), runId: id }; }
    const R = d.report || {}, V = R.vibration || {}, dom = V.dominant || {}, Dg = d.diagnosis && d.diagnosis.diagnosis, viz = d.visualize, F = d.files || {};
    const meta = (runs || []).find(r => r.run === id) || { created: T0, run: id };
    const s = sev(Dg && Dg.severity);
    const cost = (R.api_cost_usd || 0) + ((d.diagnosis && d.diagnosis.api_cost_usd) || 0) + ((viz && viz.api_cost_usd) || 0);
    const Hm = V.harmonics || [];
    const faults = ((Dg && Dg.faults) || []).slice().sort((a, b) => b.likelihood - a.likelihood);
    const fi = Math.max(0, Math.min(S.rep.fault, faults.length - 1)), sel = faults[fi];
    const dir = V.direction_deg ?? 0, dn = ((dir % 180) + 180) % 180;
    const dirLabel = dn < 20 || dn > 160 ? 'Horizontal · side-to-side' : dn > 70 && dn < 110 ? 'Vertical · up-and-down' : 'Diagonal';
    const real = !!(d.spectrum && d.spectrum.amp && d.spectrum.amp.length), FM = real ? d.spectrum.fmax : FMAX;
    const spec = real ? realSpec(d.spectrum) : F['spectrum.png'] ? null : specFor(id, V);
    const markers = Hm.filter(h => h.present && h.peak && h.peak.freq_hz <= FM).map(h => ({ left: (h.peak.freq_hz / FM * 100).toFixed(2) + '%', top: (yOf(h.peak.amplitude) / H * 100).toFixed(2) + '%', label: h.order + '× ' + fx(h.peak.freq_hz, 2) + ' Hz' }));
    const A = R.accelerometer, ahz = A ? (A.dominant_hz ?? A.freq_hz ?? (A.dominant && A.dominant.freq_hz)) : null;
    const agrees = A ? (A.agrees ?? (ahz != null && Math.abs(ahz - dom.freq_hz) < 0.1)) : false;
    const mk = R.mask || {}, det = (mk.detections || [])[0] || {};
    const ap = (Dg && Dg.action_point) || null;
    const mode = S.rep.video, vid = F['side_by_side.mp4'];
    const sp = S.rep.slider;
    const vtabs = [['original', 'Original'], ['magnified', 'Magnified'], ['side', 'Side by side']].map(([k, l]) => ({ label: l, on: mode === k, ...tab(mode === k), onClick: () => { S.rep.video = k; emit(); } }));
    const ms = MODE === 'app' ? machinesData() : [];
    const mach = meta.machine || R.machine || (Dg ? Dg.machine : (machineOf(ms, id) || {}).name || cap(meta.prompt || mk.prompt || 'Machine'));
    return {
      ok: true, loading: false, failed: false, runId: id, machine: mach, date: dateL(meta.created), time: timeL(meta.created), ago: ago(meta.created), input: meta.input || '',
      tag: tag(d), hasTag: !!tag(d), demo: !!d._demo,
      ...s, conf: Dg ? Math.round(Dg.confidence * 100) + '%' : '—', confW: Dg ? Math.round(Dg.confidence * 100) + '%' : '0%', cost: money(cost), costShort: money(cost, 2),
      diag: !!Dg, noDiag: !Dg, summary: Dg ? Dg.summary : '', primary: Dg ? nice(Dg.primary_fault) : '', nextStep: Dg && Dg.recommended_actions && Dg.recommended_actions[0] ? Dg.recommended_actions[0].step : '', freqRel: faults[0] && faults[0].harmonic_relation ? faults[0].harmonic_relation : '',
      hz: fx(dom.freq_hz, 3), hzShort: fx(dom.freq_hz, 2), cpm: int(V.dominant_cpm), px: fx(dom.amplitude, 4), snr: int(dom.snr), res: fx(V.spectral_resolution_hz, 4) + ' Hz', freqMain: freqMain(dom.freq_hz), freqAlt: freqAlt(dom.freq_hz),
      dirDeg: Math.round(dir) + '°', dirRot: `rotate(${dir}deg)`, dirLabel,
      harm: Hm.map(h => ({ order: h.order + '×', hz: fx(h.expected_hz, 1), rel: h.present ? Math.round(h.relative_amplitude * 100) + '%' : '—', h: h.present ? Math.max(3, h.relative_amplitude * 100).toFixed(1) + '%' : '3%', present: h.present, absent: !h.present, status: h.present ? 'present' : 'not present', snr: h.peak ? int(h.peak.snr) : '—', color: h.present ? 'var(--signal)' : 'var(--line-2)' })),
      spec: { hasImg: !real && !!F['spectrum.png'], noImg: real || !F['spectrum.png'], img: F['spectrum.png'] || '', imgBg: F['spectrum.png'] ? `center / contain no-repeat url("${F['spectrum.png']}")` : 'none', line: spec ? spec.line : '', area: spec ? spec.area : '', markers, fmax: Math.round(FM) },
      mask: { bg: imgBg(F['mask_overlay.png']), label: F['mask_overlay.png'] ? '' : 'mask_overlay.png', prompt: mk.prompt || '', source: mk.source || 'SAM 3.1', conf: det.confidence != null ? Math.round(det.confidence * 100) + '%' : '—', area: int(mk.measured_area_px) + ' px', excluded: fx((mk.fast_motion_excluded_fraction || 0) * 100, 1) + '%', box: det.box && !F['mask_overlay.png'] ? { left: det.box[0] / 10 + '%', top: det.box[1] / 10 + '%', width: (det.box[2] - det.box[0]) / 10 + '%', height: (det.box[3] - det.box[1]) / 10 + '%' } : null },
      hasAcc: !!A, noAcc: !A, acc: A ? { hz: fx(ahz, 2) + ' Hz', delta: 'Δ ' + fx(A.delta_hz ?? Math.abs(ahz - dom.freq_hz), 3) + ' Hz', agrees, label: agrees ? 'Accelerometer agrees' : 'Accelerometer disagrees', color: agrees ? 'var(--sev-normal)' : 'var(--sev-act)', source: A.source || 'phyphox' } : null,
      faults: faults.map((f, i) => ({ rank: String(i + 1).padStart(2, '0'), name: nice(f.fault_type), pct: Math.round(f.likelihood * 100) + '%', w: (f.likelihood * 100).toFixed(0) + '%', freq: f.frequency_hz != null ? fx(f.frequency_hz, 2) + ' Hz' : '—', rel: f.harmonic_relation || '', on: i === fi, ...tab(i === fi), onClick: () => { S.rep.fault = i; emit(); }, nSup: (f.supporting_evidence || []).length, nCon: (f.contradicting_evidence || []).length })),
      sel: sel ? (sel.supporting_evidence = sel.supporting_evidence || [], sel.contradicting_evidence = sel.contradicting_evidence || [], { name: nice(sel.fault_type), pct: Math.round(sel.likelihood * 100) + '%', freq: sel.frequency_hz != null ? fx(sel.frequency_hz, 2) + ' Hz' : '—', rel: sel.harmonic_relation, sup: sel.supporting_evidence.map(e => ({ ...src(e.source), detail: e.detail })), con: sel.contradicting_evidence.map(c => ({ detail: c })), hasSup: sel.supporting_evidence.length > 0, hasCon: sel.contradicting_evidence.length > 0, noCon: !sel.contradicting_evidence.length }) : null,
      rot: Dg && Dg.rotation ? { rated: Dg.rotation.rated_rpm ? int(Dg.rotation.rated_rpm) + ' RPM' : 'Not given', ratedHz: Dg.rotation.rated_rpm ? fx(Dg.rotation.rated_rpm / 60, 2) + ' Hz' : '', source: Dg.rotation.rated_rpm_source || 'no nameplate or manual', measured: fx(Dg.rotation.measured_hz, 2) + ' Hz', measuredRpm: int(Dg.rotation.measured_hz * 60) + ' RPM', relation: Dg.rotation.relation } : null,
      unc: ((Dg && Dg.uncertainties) ? (Array.isArray(Dg.uncertainties) ? Dg.uncertainties : [Dg.uncertainties]) : []).map(u => ({ text: u })), hasUnc: !!(Dg && Dg.uncertainties && Dg.uncertainties.length),
      actions: ((Dg && Dg.recommended_actions) || []).map((a, i) => ({ n: String(i + 1).padStart(2, '0'), num: i + 1, step: a.step, where: a.where, page: a.manual_page ? 'Manual p. ' + a.manual_page : 'No manual page', hasPage: !!a.manual_page })),
      viz: !!(viz || F['fixed_state.png']), noViz: !(viz || F['fixed_state.png']),
      where: { bg: imgBg(F['where_to_act.png'] || F['key_frame.png']), label: F['where_to_act.png'] ? '' : 'where_to_act.png', x: ap ? ap.x / 10 + '%' : '50%', y: ap ? ap.y / 10 + '%' : '50%', pt: ap ? ap.label : '', hasPt: !!ap && !F['where_to_act.png'] },
      slider: { pos: sp, before: imgBg(F['key_frame.png']), after: imgBg(F['fixed_state.png']), beforeLabel: F['key_frame.png'] ? '' : 'key_frame.png · now', afterLabel: F['fixed_state.png'] ? '' : 'fixed_state.png · after the fix', clip: `inset(0 ${100 - sp}% 0 0)`, left: sp + '%', onInput: e => { S.rep.slider = +e.target.value; emit(); } },
      cites: ((Dg && Dg.manual_citations) || []).map(c => ({ page: 'p. ' + c.page, quote: c.quote, relevance: c.relevance, verified: !!c.verified, badge: c.verified ? 'Verified' : 'Unverified', color: c.verified ? 'var(--sev-normal)' : 'var(--sev-monitor)', tintc: tint(c.verified ? 'var(--sev-normal)' : 'var(--sev-monitor)'), score: 'match ' + Math.round((c.match_score || 0) * 100) + '%', found: c.found_on_page ? 'found on p. ' + c.found_on_page : 'not found in PDF' })), hasCites: !!(Dg && Dg.manual_citations && Dg.manual_citations.length), noCites: !(Dg && Dg.manual_citations && Dg.manual_citations.length),
      expect: Dg ? Dg.rescan_expectation : '', fixedDesc: Dg ? Dg.fixed_state_description : '',
      warnings: (R.warnings || []).map(w => ({ text: w })), hasWarnings: !!(R.warnings && R.warnings.length),
      video: { has: !!vid, none: !vid, url: vid || '', poster: F['key_frame.png'] || '', tabs: vtabs, w: mode === 'side' ? '100%' : '200%', x: mode === 'magnified' ? 'translateX(-50%)' : 'none', ratio: mode === 'side' ? '32 / 9' : '16 / 9' },
      motionRef: refs.motion,
      rescanHref: '#/analyze?rescan=' + encodeURIComponent(id),
      dx: dxVM(id),
      hasCompare: !!d.compare, compareHref: d.compare ? `#/rescan?before=${encodeURIComponent(d.compare.before_run)}&after=${encodeURIComponent(d.compare.after_run)}` : '',
      share: () => { const u = location.href; (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(() => toast('Share link copied'), () => toast('Copy this link: ' + u)); },
      print: () => window.print(),
    };
  }

  /* ---- diagnose an existing run ---- */
  const DX_STAGES = [['diagnose', 'Diagnosing the fault with Muse Spark…'], ['visualize', 'Showing the fix on your frame with Muse Image…']];
  const dxOf = id => S.dx[id] || (S.dx[id] = { visualize: S.defaults.visualize, manual: null, manualName: '', running: false, stage: null, error: null, t0: 0, jobId: null });
  async function diagnoseRun(id) {
    const x = dxOf(id);
    if (!live()) { toast('Switch to Live API in Settings to diagnose your own runs', 'error'); return; }
    const fd = new FormData();
    fd.append('visualize', String(x.visualize));
    if (x.manual) fd.append('manual', x.manual);
    Object.assign(x, { running: true, stage: 'diagnose', error: null, t0: performance.now() }); startTick(); emit();
    try { const { job } = await api.diagnoseRun(id, fd); x.jobId = job; pollDx(id); }
    catch (e) { Object.assign(x, { running: false, error: 'Could not start the diagnosis. ' + (e.message || '') }); emit(); }
  }
  function pollDx(id) {
    const x = dxOf(id);
    setTimeout(async () => {
      if (!x.running) return;
      try {
        const j = await api.job(x.jobId);
        x.stage = j.stage;
        if (j.status === 'done') { x.running = false; await loadDetail(id, true); loadCosts(); toast('Diagnosis ready'); emit(); return; }
        if (j.status === 'error') { Object.assign(x, { running: false, error: j.error || 'The diagnosis stopped.' }); emit(); return; }
        emit(); pollDx(id);
      } catch (e) { Object.assign(x, { running: false, error: 'Lost connection while waiting. ' + e.message }); emit(); }
    }, CONFIG.POLL_MS);
  }
  function dxVM(id) {
    const x = dxOf(id), now = performance.now();
    const plan = DX_STAGES.filter(([k]) => k !== 'visualize' || x.visualize);
    const at = plan.findIndex(([k]) => k === x.stage);
    return {
      running: x.running, error: x.error || '', hasError: !!x.error, live: live(),
      cost: x.visualize ? '≈ $0.05' : '≈ $0.03',
      visualize: { on: x.visualize, toggle: () => { if (!x.running) { x.visualize = !x.visualize; emit(); } }, track: x.visualize ? 'var(--accent)' : 'var(--line-2)', knob: x.visualize ? 'translateX(20px)' : 'none' },
      manualName: x.manualName, hasManual: !!x.manualName,
      onManual: e => { const f = e.target.files && e.target.files[0]; if (f) { x.manual = f; x.manualName = f.name; emit(); } },
      clearManual: () => { x.manual = null; x.manualName = ''; emit(); },
      start: () => diagnoseRun(id),
      elapsed: x.t0 ? fx((now - x.t0) / 1000, 0) + ' s' : '',
      stages: plan.map(([k, desc], i) => { const st = !x.running && !x.error && at < 0 ? 'pending' : i < at || (x.stage === 'done') ? 'done' : i === at ? (x.error ? 'error' : 'running') : 'pending'; return { key: k, desc, st, color: st === 'done' ? 'var(--ok)' : st === 'running' ? 'var(--accent)' : st === 'error' ? 'var(--sev-stop)' : 'var(--line-2)' }; }),
    };
  }

  /* ---- compare VM ---- */
  function compareVM(c, plot) {
    if (!c) return null;
    const V = { resolved: ['Resolved', 'var(--sev-normal)', 'The fault is gone.'], improved: ['Improved', 'var(--sev-monitor)', 'Better, but not fully fixed.'], no_change: ['No change', 'var(--fg-2)', 'The repair did not change the vibration.'], worse: ['Worse', 'var(--sev-stop)', 'Vibration increased after the work.'] }[c.verdict] || [cap(c.verdict), 'var(--fg-2)', ''];
    const row = (label, o, hz) => ({ label, hz: fx(hz, 2) + ' Hz', before: fx(o.before_px, 4), after: fx(o.after_px, 4), pct: sgn(o.change_pct, 1) + '%', db: sgn(o.change_db, 1) + ' dB', wA: Math.max(1, Math.min(100, o.after_px / o.before_px * 100)).toFixed(1) + '%', good: o.change_pct < 0, color: o.change_pct < 0 ? 'var(--sev-normal)' : 'var(--sev-stop)' });
    const B = S.details[c.before_run] || SAMPLE.details[c.before_run], A = S.details[c.after_run] || SAMPLE.details[c.after_run];
    const allRuns = (S.runs || SAMPLE.runs);
    const bm = allRuns.find(r => r.run === c.before_run) || {}, am = allRuns.find(r => r.run === c.after_run) || {};
    const sp = c.spark;
    const bothReal = !!(B && A && B.spectrum && A.spectrum), ovMax = bothReal ? Math.min(B.spectrum.fmax, A.spectrum.fmax) : FMAX;
    const h = (c.before_run + c.after_run).split('').reduce((s, ch) => (s * 31 + ch.charCodeAt(0)) >>> 0, 7).toString(36).toUpperCase().slice(0, 6);
    const machine = bm.machine || (B && B.report && B.report.machine) || (B && B.diagnosis && B.diagnosis.diagnosis.machine) || cap(bm.prompt || 'Machine');
    return {
      verdict: c.verdict, label: V[0], color: V[1], tintc: tint(V[1], 14), blurb: V[2], machine,
      big: sgn(c.fundamental.change_pct, 0) + '%', bigDb: sgn(c.fundamental.change_db, 1) + ' dB', hz: fx(c.fault_frequency_hz, 2) + ' Hz',
      rows: [row('1× fundamental', c.fundamental, c.fault_frequency_hz), ...(c.harmonics || []).map(x => row(x.order + '×', x, x.freq_hz))],
      rms: row('RMS displacement', c.rms_displacement, c.fault_frequency_hz),
      hasSpark: !!sp, noSpark: !sp, spark: sp ? { matches: !!sp.matches_prediction, label: sp.matches_prediction ? 'Matches the prediction' : 'Does not match the prediction', color: sp.matches_prediction ? 'var(--sev-normal)' : 'var(--sev-act)', explanation: sp.explanation, next: sp.next_step } : null,
      before: { run: c.before_run, date: bm.created ? dateL(bm.created) : '', href: '#/runs/' + encodeURIComponent(c.before_run) }, after: { run: c.after_run, date: am.created ? dateL(am.created) : '', href: '#/runs/' + encodeURIComponent(c.after_run) },
      cert: 'RSN-' + h, issued: am.created ? dateL(am.created) : dateL(T0),
      hasPlot: !!plot && !bothReal, noPlot: !plot || bothReal, plot: plot || '', plotBg: plot ? `center / contain no-repeat url("${plot}")` : 'none',
      ov: bothReal ? { b: realSpec(B.spectrum, ovMax).line, a: realSpec(A.spectrum, ovMax).line, fmax: Math.round(ovMax) } : { b: B ? specFor(c.before_run, B.report.vibration).line : '', a: A ? specFor(c.after_run, A.report.vibration).line : '', fmax: FMAX },
      warnings: (c.warnings || []).map(w => ({ text: w })), hasWarnings: !!(c.warnings && c.warnings.length),
      tag: (B && B._sample) ? CONFIG.SAMPLE_LABEL : (B && B._demo) ? CONFIG.DEMO_LABEL : '',
    };
  }
  async function runCompare() {
    const { before, after } = S.rs; if (!before || !after) return;
    S.rs.loading = true; S.rs.error = null; S.rs.result = null; emit();
    try { await Promise.all([loadDetail(before), loadDetail(after)]); const r = await api.compare(before, after, S.rs.spark); S.rs.result = r.result; S.rs.plot = r.plot; }
    catch (e) { S.rs.error = e.message || String(e); }
    S.rs.loading = false; emit();
  }

  /* ---- analyze ---- */
  function prefillRescan(runId) {
    const d = S.details[runId] || SAMPLE.details[runId]; const r = (S.runs || SAMPLE.runs).find(x => x.run === runId);
    const az = freshAz(); az.rescanOf = runId; az.prompt = (r && r.prompt) || ''; az.machine = (r && r.machine) || (d && d.report && d.report.machine) || (d && d.diagnosis && d.diagnosis.diagnosis.machine) || '';
    S.az = az;
  }
  function setFile(f) {
    if (!f) return;
    if (!/^video\//.test(f.type) && !/\.(mov|mp4|m4v|avi|webm|mkv)$/i.test(f.name)) { toast('That file isn’t a video. Use .mov or .mp4.', 'error'); return; }
    if (S.az.previewUrl) URL.revokeObjectURL(S.az.previewUrl);
    Object.assign(S.az, { file: f, fileName: f.name, fileSize: (f.size / 1e6).toFixed(1) + ' MB', previewUrl: URL.createObjectURL(f), sampleClip: false, dragging: false }); emit();
  }
  const planned = () => STAGES.filter(([k]) => !(k === 'accel' && !S.az.accelName) && !(k === 'diagnose' && !S.az.diagnose) && !(k === 'visualize' && !(S.az.visualize && S.az.diagnose)));
  let simToken = 0, pollT = 0, tickT = 0;
  const startTick = () => { clearInterval(tickT); tickT = setInterval(() => { if (S.az.running || Object.values(S.dx).some(x => x.running)) emit(); else clearInterval(tickT); }, 200); };
  function markStage(k, state) { const now = performance.now(); if (state === 'running' && !S.az.times[k]) S.az.times[k] = { s: now }; if ((state === 'done' || state === 'error') && S.az.times[k]) S.az.times[k].e = now; S.az.st[k] = state; }
  async function simulate(fromIdx) {
    const tok = ++simToken, P = planned();
    for (let i = fromIdx; i < P.length; i++) {
      const [k, , , , dur] = P[i]; markStage(k, 'running'); emit();
      await wait(dur * 1000); if (tok !== simToken) return;
      if (k === 'magnify' && S.az.simFail && !S.az.failedOnce) { S.az.failedOnce = true; markStage(k, 'error'); S.az.running = false; S.az.error = { stage: k, idx: i, msg: 'Magnification ran out of memory on a 4K clip. Retrying at 1080p usually works.' }; emit(); return; }
      markStage(k, 'done'); emit();
    }
    finishSample();
  }
  function finishSample() {
    const t = Math.floor(nowS()), id = stampId(t) + '-' + slug(S.az.prompt || 'machine');
    const tpl = S.az.rescanOf ? SAMPLE.details[FAN_B] : SAMPLE.details[FAN_A];
    const clone = JSON.parse(JSON.stringify(tpl)); clone.compare = null;
    if (clone.diagnosis && S.az.machine) clone.diagnosis.diagnosis.machine = S.az.machine;
    if (!S.az.diagnose) { clone.diagnosis = null; clone.visualize = null; } else if (!S.az.visualize) clone.visualize = null;
    if (!S.az.accelName) clone.report.accelerometer = null;
    SAMPLE.details[id] = clone;
    const r = { run: id, created: t, input: S.az.fileName || 'clip.mov', prompt: S.az.prompt || 'machine', freq_hz: 19.0001, fault: clone.diagnosis ? clone.diagnosis.diagnosis.primary_fault : null, severity: clone.diagnosis ? clone.diagnosis.diagnosis.severity : null, thumb: null, _sample: true };
    SAMPLE.runs.unshift(r); S.runs = SAMPLE.runs.slice(); S.details[id] = clone;
    complete(id);
  }
  function complete(id) {
    const of = S.az.rescanOf; S.az.running = false; S.az.done = id; emit();
    toast('Analysis complete');
    setTimeout(() => { S.az = freshAz(); go(of ? `/rescan?before=${encodeURIComponent(of)}&after=${encodeURIComponent(id)}` : '/runs/' + encodeURIComponent(id)); }, 700);
  }
  async function startLive() {
    const az = S.az, fd = new FormData();
    if (az.file) fd.append('video', az.file); fd.append('prompt', az.prompt); fd.append('machine', az.machine); if (az.fps > 0) fd.append('capture_fps', String(az.fps)); fd.append('duration', String(az.duration)); fd.append('diagnose', String(az.diagnose)); fd.append('visualize', String(az.visualize && az.diagnose));
    if (az.accel) fd.append('accel', az.accel); if (az.manual) fd.append('manual', az.manual);
    markStage('upload', 'running'); emit();
    try { const { job } = await api.analyze(fd); az.jobId = job; poll(); }
    catch (e) { markStage('upload', 'error'); az.running = false; az.error = { stage: 'upload', idx: 0, msg: 'Could not reach the Resonance server at ' + origin() + '. ' + (e.message || '') }; emit(); }
  }
  function poll() {
    clearTimeout(pollT);
    pollT = setTimeout(async () => {
      const az = S.az; if (!az.jobId || !az.running) return;
      try {
        const j = await api.job(az.jobId); const doneList = j.stages || [];
        for (const [k] of planned()) { if (k === j.stage) markStage(k, j.status === 'error' ? 'error' : j.status === 'done' ? 'done' : 'running'); else if (doneList.includes(k) && az.st[k] !== 'done') markStage(k, 'done'); }
        if (j.status === 'done') { for (const [k] of planned()) markStage(k, 'done'); S.runs = null; loadRuns(true); complete(j.run); return; }
        if (j.status === 'error') { az.running = false; az.error = { stage: j.stage, idx: 0, msg: j.error || 'The pipeline stopped.' }; emit(); return; }
        emit(); poll();
      } catch (e) { const cur = planned().find(([k]) => az.st[k] === 'running'); if (cur) markStage(cur[0], 'error'); az.error = { stage: cur ? cur[0] : 'upload', msg: 'Lost connection while polling. ' + e.message }; az.running = false; emit(); }
    }, CONFIG.POLL_MS);
  }
  function start() {
    const az = S.az; az.running = true; az.error = null; az.st = {}; az.times = {}; az.t0 = performance.now(); az.step = 5; startTick(); emit();
    if (live()) startLive(); else simulate(0);
  }
  function retry() {
    const az = S.az, e = az.error; if (!e) return; az.error = null; az.running = true; startTick();
    if (live()) { az.st = {}; az.times = {}; startLive(); return; }
    delete az.times[e.stage]; simulate(e.idx); emit();
  }
  function analyzeVM() {
    const az = S.az, P = planned(), now = performance.now();
    const can = { 1: !!(az.file || az.sampleClip), 2: !!(az.prompt.trim() && az.fps >= 0 && az.duration > 0), 3: true, 4: true };
    const labels = ['Video', 'Describe', 'Evidence', 'Options', 'Run'];
    const doneN = P.filter(([k]) => az.st[k] === 'done').length;
    const est = P.reduce((s, x) => s + x[3], 0);
    const set = (k, num) => e => { az[k] = num ? +e.target.value : e.target.value; emit(); };
    return {
      step: az.step, s1: az.step === 1, s2: az.step === 2, s3: az.step === 3, s4: az.step === 4, s5: az.step === 5,
      steps: labels.map((l, i) => ({ n: i + 1, nn: String(i + 1).padStart(2, '0'), label: l, on: az.step === i + 1, done: az.step > i + 1, ...tab(az.step === i + 1), mark: az.step > i + 1 ? '✓' : String(i + 1), go: () => { if (!az.running && i + 1 < az.step) { az.step = i + 1; emit(); } } })),
      next: () => { if (can[az.step]) { az.step = Math.min(4, az.step + 1); emit(); } }, back: () => { if (az.step > 1 && !az.running) { az.step--; emit(); } },
      nextDisabled: !can[az.step], canNext: !!can[az.step],
      hasFile: !!(az.file || az.sampleClip), noFile: !(az.file || az.sampleClip), fileName: az.fileName, fileSize: az.fileSize, resolution: az.resolution, previewUrl: az.previewUrl, hasPreview: !!az.previewUrl, sampleClip: az.sampleClip,
      dropBd: az.dragging ? 'var(--accent)' : 'var(--line-2)', dropBg: az.dragging ? tint('var(--accent)', 10) : 'transparent', dragging: az.dragging,
      onFile: e => setFile(e.target.files && e.target.files[0]), onDrop: e => { e.preventDefault(); setFile(e.dataTransfer.files[0]); }, onDragOver: e => { e.preventDefault(); if (!az.dragging) { az.dragging = true; emit(); } }, onDragLeave: () => { az.dragging = false; emit(); },
      onMeta: e => { const v = e.target; if (v.duration && isFinite(v.duration)) { az.duration = +Math.min(10, v.duration).toFixed(1); az.resolution = v.videoWidth + '×' + v.videoHeight; emit(); } },
      clearFile: () => { if (az.previewUrl) URL.revokeObjectURL(az.previewUrl); Object.assign(az, { file: null, fileName: '', fileSize: '', previewUrl: '', sampleClip: false }); emit(); },
      useSample: () => { Object.assign(az, { sampleClip: true, file: null, previewUrl: '', fileName: 'desk-fan_240fps_10s.mov', fileSize: '48.2 MB', resolution: '1920×1080', prompt: az.prompt || 'fan', machine: az.machine || 'Desk fan', fps: 240, duration: 10, step: 2 }); emit(); },
      isSample: !live(),
      prompt: az.prompt, machine: az.machine, fps: az.fps, duration: az.duration, onPrompt: set('prompt'), onMachine: set('machine'), onFps: set('fps', 1), onDuration: set('duration', 1),
      fpsOpts: [0, 120, 240, 480].map(v => ({ label: v ? v + ' fps' : 'Auto', on: az.fps === v, ...tab(az.fps === v), onClick: () => { az.fps = v; emit(); } })),
      nyquist: az.fps ? fx(az.fps / 2, 0) + ' Hz' : 'half the file’s frame rate', resHz: az.duration ? fx(1 / az.duration, 3) + ' Hz' : '—',
      accelName: az.accelName, hasAccel: !!az.accelName, noAccel: !az.accelName, manualName: az.manualName, hasManual: !!az.manualName, noManual: !az.manualName,
      onAccel: e => { const f = e.target.files[0]; if (f) { az.accel = f; az.accelName = f.name; emit(); } }, onManual: e => { const f = e.target.files[0]; if (f) { az.manual = f; az.manualName = f.name; emit(); } },
      clearAccel: () => { az.accel = null; az.accelName = ''; emit(); }, clearManual: () => { az.manual = null; az.manualName = ''; emit(); },
      sampleAccel: () => { az.accelName = 'phyphox_desk-fan.zip'; emit(); }, sampleManual: () => { az.manualName = 'desk-fan-manual.pdf'; emit(); },
      diagnose: { on: az.diagnose, toggle: () => { az.diagnose = !az.diagnose; emit(); }, track: az.diagnose ? 'var(--accent)' : 'var(--line-2)', knob: az.diagnose ? 'translateX(20px)' : 'none', label: az.diagnose ? 'On' : 'Off' },
      visualize: { on: az.visualize && az.diagnose, disabled: !az.diagnose, toggle: () => { if (az.diagnose) { az.visualize = !az.visualize; emit(); } }, track: (az.visualize && az.diagnose) ? 'var(--accent)' : 'var(--line-2)', knob: (az.visualize && az.diagnose) ? 'translateX(20px)' : 'none', label: (az.visualize && az.diagnose) ? 'On' : 'Off', op: az.diagnose ? '1' : '0.45' },
      simFail: { on: az.simFail, toggle: () => { az.simFail = !az.simFail; az.failedOnce = false; emit(); }, track: az.simFail ? 'var(--sev-stop)' : 'var(--line-2)', knob: az.simFail ? 'translateX(20px)' : 'none' },
      est: money(est), estRange: '$' + fx(Math.max(0.002, est * 0.8), 3) + '–' + fx(est * 1.2 + 0.002, 3), nStages: P.length,
      start, retry, reset: () => { simToken++; clearTimeout(pollT); S.az = freshAz(); emit(); },
      running: az.running, idle: !az.running && !az.error && !az.done, error: az.error ? az.error.msg : '', hasError: !!az.error, errStage: az.error ? cap(az.error.stage || '') : '', done: !!az.done,
      pct: Math.round(doneN / P.length * 100) + '%', pctN: Math.round(doneN / P.length * 100), elapsed: az.t0 ? fx(((az.running ? now : (Math.max(...Object.values(az.times).map(t => t.e || t.s), az.t0))) - az.t0) / 1000, 1) + ' s' : '0.0 s',
      current: (P.find(([k]) => az.st[k] === 'running') || P.find(([k]) => az.st[k] === 'error') || [])[2] || (az.done ? 'Report ready. Opening…' : ''),
      stages: P.map(([k, l, desc, cost], i) => { const st = az.st[k] || 'pending', t = az.times[k]; return { key: k, label: l, desc, n: String(i + 1).padStart(2, '0'), st, isRun: st === 'running', isDone: st === 'done', isErr: st === 'error', isPend: st === 'pending', stLabel: { pending: 'Waiting', running: 'Running', done: 'Done', error: 'Failed' }[st], elapsed: t ? fx(((t.e || now) - t.s) / 1000, 1) + ' s' : '—', cost: cost ? '≈ ' + money(cost) : 'local · free', color: st === 'done' ? 'var(--ok)' : st === 'running' ? 'var(--accent)' : st === 'error' ? 'var(--sev-stop)' : 'var(--line-2)', op: st === 'pending' ? '0.5' : '1' }; }),
      rescanOf: az.rescanOf, isRescan: !!az.rescanOf, rescanBg: az.rescanOf ? imgBg(((S.details[az.rescanOf] || {}).files || {})['key_frame.png']) : STRIPE,
    };
  }

  /* ---- canvas refs (stable identities) ---- */
  const refs = {
    wave: mkRef(el => attachWave(el, { grid: opts.waveGrid !== false, glow: opts.waveGlow, width: opts.waveWidth })),
    waveSmall: mkRef(el => attachWave(el, { grid: false, lensMarks: false, glow: 0, width: 1.5, lens: 0.25 })),
    motion: mkRef(el => attachMotion(el, () => S.rep.video)),
    motionSide: mkRef(el => attachMotion(el, () => 'side')),
    motionCompare: mkRef(el => attachMotion(el, () => 'compare')),
    reveal, scale: mkRef(scrollScale),
  };

  /* ---- controlled <select> sync (options render after the select mounts) ---- */
  const selEls = {}; let selWant = {};
  const selRefs = { machine: el => { selEls.machine = el; }, before: el => { selEls.before = el; }, after: el => { selEls.after = el; } };
  function syncSelects() { for (const k in selEls) { const el = selEls[k]; if (el && selWant[k] != null && el.value !== selWant[k]) el.value = selWant[k]; } }

  /* ---- vals ---- */
  function vals() {
    const r = S.route;
    const nav = [['dashboard', 'Dashboard'], ['machines', 'Machines'], ['analyze', 'Analyze'], ['runs', 'Runs'], ['rescan', 'Rescan'], ['guide', 'Recording guide'], ['usage', 'Usage & cost'], ['settings', 'Settings']];
    const activeKey = r.name === 'report' ? 'runs' : r.name === 'machine' ? 'machines' : r.name;
    const navItem = ([k, l], i) => ({ key: k, label: l, n: String(i + 1).padStart(2, '0'), href: '#/' + k, on: activeKey === k, ...tab(activeKey === k), current: activeKey === k ? 'page' : undefined });
    const base = {
      ready: true, booting: false, theme: S.theme, isDark: S.theme === 'dark', themeLabel: S.theme === 'dark' ? 'Light' : 'Dark', themeIcon: S.theme === 'dark' ? '☀' : '☾',
      toggleTheme: () => { S.theme = S.theme === 'dark' ? 'light' : 'dark'; sv(`resonance:${ID}:theme`, S.theme); document.documentElement.dataset.theme = S.theme; emit(); },
      toast: S.toast || { msg: '', kind: 'ok' }, hasToast: !!S.toast, toastColor: S.toast && S.toast.kind === 'error' ? 'var(--sev-stop)' : 'var(--ok)', dismissToast: () => { S.toast = null; emit(); },
      refs, sampleLabel: CONFIG.SAMPLE_LABEL, demoLabel: CONFIG.DEMO_LABEL, apiBase: origin(),
    };
    if (MODE === 'site') {
      const fan = reportVM(FAN_A, SAMPLE.details, SAMPLE.runs);
      return { ...base, fan, cmp: compareVM(FAN_COMPARE, null),
        faq: FAQ.map(([q, a], i) => ({ q, a, open: S.faq === i, sign: S.faq === i ? '−' : '+', toggle: () => { S.faq = S.faq === i ? -1 : i; emit(); }, n: String(i + 1).padStart(2, '0') })),
        pipe: PIPE.map(([t, d, m], i) => ({ n: String(i + 1).padStart(2, '0'), title: t, desc: d, model: m, on: S.pipe === i, past: i < S.pipe, op: S.pipe === i ? '1' : i < S.pipe ? '0.8' : '0.45', bar: S.pipe === i ? '100%' : i < S.pipe ? '100%' : '0%', dot: i <= S.pipe ? 'var(--accent)' : 'var(--line-2)', ...tab(S.pipe === i), onClick: () => { S.pipe = i; pipeHold = 2; emit(); } })),
        pipeNow: PIPE[S.pipe][0], pipeW: ((S.pipe + 1) / 6 * 100).toFixed(1) + '%' };
    }
    const runs = S.runs || [], ms = machinesData();
    const items = runs.map(x => runItem(x, ms)), mItems = ms.map(machineItem);
    const costs = S.costs || [], spend = costs.reduce((s, c) => s + c.cost_usd, 0);
    const q = S.search.trim().toLowerCase();
    const results = q ? [...mItems.filter(m => (m.name + ' ' + m.fault).toLowerCase().includes(q)).map(m => ({ label: m.name, sub: 'Machine · ' + m.sevLabel, href: m.href })), ...items.filter(x => (x.title + ' ' + x.run + ' ' + x.fault + ' ' + x.prompt).toLowerCase().includes(q)).map(x => ({ label: x.title + ' · ' + x.date, sub: 'Run ' + x.run, href: x.href }))].slice(0, 7) : [];
    const loading = !S.runs && !S.runsError;
    const out = {
      ...base, live: live(), sample: !live(), modeLabel: live() ? 'Live API' : 'Sample data',
      p: { dashboard: r.name === 'dashboard', machines: r.name === 'machines', machine: r.name === 'machine', analyze: r.name === 'analyze', runs: r.name === 'runs', report: r.name === 'report', rescan: r.name === 'rescan', guide: r.name === 'guide', usage: r.name === 'usage', settings: r.name === 'settings', more: r.name === 'more', kit: r.name === 'kit' },
      pageTitle: { dashboard: 'Dashboard', machines: 'Machines', machine: 'Machine', analyze: 'New analysis', runs: 'Runs', report: 'Run report', rescan: 'Rescan & compare', guide: 'Recording guide', usage: 'Usage & cost', settings: 'Settings', more: 'More', kit: 'Components' }[r.name],
      nav: nav.map(navItem), tabs: [['dashboard', 'Home'], ['machines', 'Machines'], ['analyze', 'Analyze'], ['runs', 'Runs'], ['more', 'More']].map(([k, l], i) => ({ ...navItem([k, l], i), on: activeKey === k || (k === 'more' && ['rescan', 'guide', 'usage', 'settings', 'kit'].includes(activeKey)) })).map(t => ({ ...t, ...tab(t.on) })),
      more: nav.slice(4).concat([['kit', 'Components']]).map(navItem),
      search: S.search, onSearch: e => { S.search = e.target.value; emit(); }, clearSearch: () => { S.search = ''; emit(); }, results, hasResults: results.length > 0, noResults: !!q && !results.length, searching: !!q,
      menu: S.menu, toggleMenu: () => { S.menu = !S.menu; emit(); },
      loading, loaded: !!S.runs, error: S.runsError || '', failed: !!S.runsError, retry: () => loadRuns(true), empty: !!S.runs && !runs.length, hasRuns: runs.length > 0,
      skel: [1, 2, 3, 4], skel6: [1, 2, 3, 4, 5, 6],
      runs: items, machines: mItems, nMachines: mItems.length,
    };
    // dashboard
    const open = ms.filter(m => m.rank >= 1);
    out.dash = {
      machines: String(ms.length), stop: String(ms.filter(m => m.sevKey === 'stop_now').length), act: String(ms.filter(m => m.sevKey === 'act_soon').length), mon: String(ms.filter(m => m.sevKey === 'monitor').length), openN: String(open.length),
      fixes: String(ms.reduce((s, m) => s + m.pairs.filter(p => p.verdict === 'resolved' || p.verdict === 'improved').length, 0)), spend: money(spend, 2), budget: '$' + CONFIG.BUDGET_USD, budgetPct: (spend / CONFIG.BUDGET_USD * 100).toFixed(2) + '%',
      attention: open.map(machineItem), hasAttention: open.length > 0, allClear: !!S.runs && !open.length,
      recent: items.slice(0, 6),
      chart: (() => { const c = lineChart(ms.map((m, i) => ({ name: m.name, color: PAL[i % 5], pts: m.runs.slice().reverse().filter(x => S.details[x.run]).map(x => [x.created, S.details[x.run].report.vibration.dominant.amplitude]) })), { t1: nowS() }); return { ...c, legend: c.series.map(s => ({ name: s.name, color: s.color })), from: runs.length ? dateL(Math.min(...runs.map(x => x.created))) : '', to: 'Today' }; })(),
    };
    // machine detail
    if (r.name === 'machine') {
      const m = ms.find(x => x.id === r.id);
      if (m) {
        const ch = lineChart([{ name: m.name, color: 'var(--signal)', pts: m.runs.slice().reverse().filter(x => S.details[x.run]).map(x => [x.created, S.details[x.run].report.vibration.dominant.amplitude, { sevColor: sev(x.severity).sevColor }]) }]);
        out.machine = { ...machineItem(m), found: true, chart: ch, runs: m.runs.map(x => runItem(x, ms)), pairs: m.pairs.map(c => compareVM(c)), hasPairs: m.pairs.length > 0, noPairs: !m.pairs.length, fhz: m.last.freq_hz != null ? fx(m.last.freq_hz, 2) + ' Hz' : '—', rescanHref: '#/analyze?rescan=' + encodeURIComponent(m.last.run) };
      } else out.machine = { found: false, missing: !!S.runs };
    }
    if (r.name === 'report' || r.name === 'kit') out.rep = reportVM(r.id || FAN_A, S.details, runs);
    if (r.name === 'analyze') out.az = analyzeVM();
    if (r.name === 'rescan' || r.name === 'kit') {
      const two = ms.filter(m => m.runs.length >= 2);
      let mid = S.rs.machine || (S.rs.before && (machineOf(ms, S.rs.before) || {}).id) || (two[0] && two.find(m => m.pairs.length) ? two.find(m => m.pairs.length).id : two[0] && two[0].id);
      const m = ms.find(x => x.id === mid);
      const opt = sel => (m ? m.runs : []).map(x => ({ value: x.run, label: dateL(x.created) + ' · ' + timeL(x.created) + ' · ' + (S.details[x.run] ? fx(S.details[x.run].report.vibration.dominant.amplitude, 3) + ' px' : ''), selected: x.run === sel }));
      if (m && !S.rs.before) { S.rs.before = (m.runs[1] || m.runs[0]).run; S.rs.after = m.runs[0].run; }
      out.rs = {
        selMachine: selRefs.machine, selBefore: selRefs.before, selAfter: selRefs.after,
        machine: mid || '', machineOpts: two.map(x => ({ value: x.id, label: x.name, selected: x.id === mid })), onMachine: e => { const nm = ms.find(x => x.id === e.target.value); S.rs.machine = e.target.value; if (nm) { S.rs.before = (nm.runs[1] || nm.runs[0]).run; S.rs.after = nm.runs[0].run; } S.rs.result = null; emit(); },
        before: S.rs.before || '', after: S.rs.after || '', beforeOpts: opt(S.rs.before), afterOpts: opt(S.rs.after), onBefore: e => { S.rs.before = e.target.value; S.rs.result = null; emit(); }, onAfter: e => { S.rs.after = e.target.value; S.rs.result = null; emit(); },
        same: S.rs.before && S.rs.before === S.rs.after, spark: { on: S.rs.spark, toggle: () => { S.rs.spark = !S.rs.spark; emit(); }, track: S.rs.spark ? 'var(--accent)' : 'var(--line-2)', knob: S.rs.spark ? 'translateX(20px)' : 'none' },
        run: () => { if (S.rs.before && S.rs.after && S.rs.before !== S.rs.after) { go(`/rescan?before=${encodeURIComponent(S.rs.before)}&after=${encodeURIComponent(S.rs.after)}`); if (S.route.q.before === S.rs.before && S.route.q.after === S.rs.after) runCompare(); } },
        loading: S.rs.loading, error: S.rs.error || '', failed: !!S.rs.error, hasResult: !!S.rs.result, idle: !S.rs.result && !S.rs.loading && !S.rs.error, none: !!S.runs && !two.length, can: two.length > 0,
        res: compareVM(S.rs.result || (r.name === 'kit' ? FAN_COMPARE : null), S.rs.plot), share: () => { (navigator.clipboard ? navigator.clipboard.writeText(location.href) : Promise.reject()).then(() => toast('Certificate link copied'), () => toast('Copy: ' + location.href)); }, print: () => window.print(),
      };
      selWant = { machine: mid || '', before: S.rs.before || '', after: S.rs.after || '' }; setTimeout(syncSelects, 0);
    }
    if (r.name === 'usage' || r.name === 'dashboard') {
      const byM = ['SAM 3.1', 'Muse Spark', 'Muse Image'].map(mn => { const cs = costs.filter(c => c.model === mn); return { model: mn, cost: money(cs.reduce((s, c) => s + c.cost_usd, 0)), raw: cs.reduce((s, c) => s + c.cost_usd, 0), calls: cs.length + ' calls', use: { 'SAM 3.1': 'Segmentation', 'Muse Spark': 'Diagnosis & compare', 'Muse Image': 'Fix visualization' }[mn] }; });
      const mx = Math.max(...byM.map(b => b.raw), 1e-9);
      const byRunMap = {}; costs.forEach(c => { if (c.run_id) byRunMap[c.run_id] = (byRunMap[c.run_id] || 0) + c.cost_usd; });
      const runRows = Object.entries(byRunMap).map(([id, v]) => { const it = items.find(x => x.run === id); return { run: id, title: it ? it.title : id, date: it ? it.date : '', cost: money(v), raw: v, href: '#/runs/' + encodeURIComponent(id) }; }).sort((a, b) => b.raw - a.raw);
      const mr = Math.max(...runRows.map(x => x.raw), 1e-9);
      const analyses = runRows.length || 1;
      out.usage = { total: money(spend, 2), totalExact: money(spend, 3), budget: '$' + CONFIG.BUDGET_USD.toFixed(2), remaining: money(CONFIG.BUDGET_USD - spend, 2), pct: (spend / CONFIG.BUDGET_USD * 100).toFixed(2) + '%', barW: Math.max(0.6, spend / CONFIG.BUDGET_USD * 100).toFixed(2) + '%', avg: money(spend / analyses), left: int((CONFIG.BUDGET_USD - spend) / (spend / analyses || 0.04)),
        byModel: byM.map(b => ({ ...b, w: (b.raw / mx * 100).toFixed(1) + '%' })), byRun: runRows.slice(0, 8).map(x => ({ ...x, w: (x.raw / mr * 100).toFixed(1) + '%' })),
        calls: costs.slice(0, 14).map(c => ({ time: dateL(c.time) + ' ' + timeL(c.time), model: c.model, endpoint: c.endpoint, cost: money(c.cost_usd), run: c.run_id || '—', hasRun: !!c.run_id, href: c.run_id ? '#/runs/' + encodeURIComponent(c.run_id) : '' })),
        mock: !S.costsLive, loading: !S.costs, loaded: !!S.costs };
    }
    if (r.name === 'settings') {
      out.set = {
        themes: [['dark', 'Dark'], ['light', 'Light']].map(([k, l]) => ({ label: l, on: S.theme === k, ...tab(S.theme === k), onClick: () => { S.theme = k; sv(`resonance:${ID}:theme`, k); document.documentElement.dataset.theme = k; emit(); } })),
        units: [['hz', 'Hz'], ['cpm', 'CPM']].map(([k, l]) => ({ label: l, on: S.units === k, ...tab(S.units === k), onClick: () => { S.units = k; sv('resonance:units', k); emit(); } })),
        modes: [['sample', 'Sample data'], ['live', 'Live API']].map(([k, l]) => ({ label: l, on: S.dataMode === k, ...tab(S.dataMode === k), onClick: () => { if (S.dataMode !== k) { S.dataMode = k; sv('resonance:dataMode', k); resetData(); toast(k === 'live' ? 'Connecting to ' + origin() : 'Showing sample data'); } } })),
        diag: { on: S.defaults.diagnose, toggle: () => { S.defaults.diagnose = !S.defaults.diagnose; sv('resonance:defaults', S.defaults); emit(); }, track: S.defaults.diagnose ? 'var(--accent)' : 'var(--line-2)', knob: S.defaults.diagnose ? 'translateX(20px)' : 'none' },
        viz: { on: S.defaults.visualize, toggle: () => { S.defaults.visualize = !S.defaults.visualize; sv('resonance:defaults', S.defaults); emit(); }, track: S.defaults.visualize ? 'var(--accent)' : 'var(--line-2)', knob: S.defaults.visualize ? 'translateX(20px)' : 'none' },
        keys: [['SAM 3.1', 'Segmentation'], ['Muse Spark', 'Diagnosis & compare'], ['Muse Image', 'Fix visualization']].map(([n, u]) => { const bad = live() && (S.runsError || (S.health && (S.health.ok === false || !S.health.api_key_configured))); const status = !live() ? 'Configured on server' : S.runsError || (S.health && S.health.ok === false) ? 'Server unreachable' : S.health && !S.health.api_key_configured ? 'Missing on server' : 'Configured on server'; return { name: n, use: u, status, ok: !bad, color: bad ? 'var(--sev-stop)' : 'var(--sev-normal)' }; }),
        apiBase: origin(), budget: '$' + CONFIG.BUDGET_USD,
      };
    }
    if (r.name === 'kit') {
      out.kit = {
        sevs: ['normal', 'monitor', 'act_soon', 'stop_now', null].map(sev), chips: Object.keys(SRC).map(src),
        stages: STAGES.slice(1, 6).map(([k, l, desc, cost], i) => { const st = ['done', 'done', 'running', 'error', 'pending'][i]; return { label: l, desc, n: String(i + 1).padStart(2, '0'), st, isRun: st === 'running', isDone: st === 'done', isErr: st === 'error', isPend: st === 'pending', stLabel: { pending: 'Waiting', running: 'Running', done: 'Done', error: 'Failed' }[st], elapsed: ['0.9 s', '1.6 s', '0.7 s', '1.2 s', '—'][i], cost: cost ? '≈ ' + money(cost) : 'local · free', color: st === 'done' ? 'var(--ok)' : st === 'running' ? 'var(--accent)' : st === 'error' ? 'var(--sev-stop)' : 'var(--line-2)', op: st === 'pending' ? '0.5' : '1' }; }),
        toastOk: () => toast('Report exported'), toastErr: () => toast('Upload failed: the server closed the connection.', 'error'),
      };
    }
    return out;
  }

  let pipeT = 0, pipeHold = 0;
  return {
    vals,
    mount() {
      document.documentElement.dataset.theme = S.theme;
      if (MODE === 'app') { S.route = parse(); addEventListener('hashchange', onHash); loadRuns(); loadCosts(); loadHealth(); onRoute(); }
      else pipeT = setInterval(() => { if (pipeHold > 0) { pipeHold--; return; } S.pipe = (S.pipe + 1) % 6; emit(); }, 1800);
      emit();
    },
    unmount() { removeEventListener('hashchange', onHash); clearInterval(pipeT); clearInterval(tickT); clearTimeout(pollT); simToken++; },
  };
}
