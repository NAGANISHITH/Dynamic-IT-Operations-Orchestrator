// App.jsx — Multi-Agent IT Ops Platform — Complete Frontend
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import { api } from './services/api';
import { useWebSocket } from './hooks/useWebSocket';
import './App.css';

// ─── Constants ───────────────────────────────────────────────────────────────

const WS_URL = (process.env.REACT_APP_WS_URL || 'ws://localhost:8000') + '/ws';

const AGENT_META = {
  server_monitor: { label: 'Server Monitor',    color: '#4d9eff', layer: 'Monitoring' },
  cloud_monitor:  { label: 'Cloud Monitor',     color: '#4d9eff', layer: 'Monitoring' },
  app_health:     { label: 'App Health',        color: '#4d9eff', layer: 'Monitoring' },
  predictive:     { label: 'Predictive Failure',color: '#a78bfa', layer: 'Intelligence' },
  remediation:    { label: 'Remediation',       color: '#2dd4bf', layer: 'Remediation' },
  deployment:     { label: 'Deployment',        color: '#2dd4bf', layer: 'Remediation' },
  reporting:      { label: 'Reporting & SLA',   color: '#fbbf24', layer: 'Reporting' },
};

const SEV_COLORS = { P1: '#f87171', P2: '#fbbf24', P3: '#4d9eff' };

const RISK_COLOR = (prob) =>
  prob >= 0.75 ? '#f87171' : prob >= 0.50 ? '#fbbf24' : '#4ade80';

// ─── Small reusable UI pieces ─────────────────────────────────────────────────

function Pill({ label, cls }) {
  const colors = {
    green:  { bg: 'rgba(74,222,128,0.12)', color: '#4ade80' },
    amber:  { bg: 'rgba(251,191,36,0.12)', color: '#fbbf24' },
    red:    { bg: 'rgba(248,113,113,0.12)',color: '#f87171' },
    blue:   { bg: 'rgba(77,158,255,0.12)', color: '#4d9eff' },
    teal:   { bg: 'rgba(45,212,191,0.12)', color: '#2dd4bf' },
    purple: { bg: 'rgba(167,139,250,0.12)',color: '#a78bfa' },
    gray:   { bg: 'rgba(255,255,255,0.07)',color: '#8b92a8'  },
  };
  const s = colors[cls] || colors.gray;
  return (
    <span style={{
      fontSize: 10, fontWeight: 600, padding: '3px 8px', borderRadius: 99,
      background: s.bg, color: s.color, fontFamily: 'monospace',
    }}>{label}</span>
  );
}

function StatusDot({ status }) {
  const colors = { active: '#4ade80', busy: '#fbbf24', idle: '#545c72' };
  return (
    <span style={{
      display: 'inline-block', width: 7, height: 7,
      borderRadius: '50%', background: colors[status] || '#545c72',
      flexShrink: 0, marginTop: 1,
    }} />
  );
}

function SectionLabel({ children }) {
  return (
    <div style={{
      fontSize: 10, fontWeight: 600, color: '#545c72',
      textTransform: 'uppercase', letterSpacing: '.1em',
      fontFamily: 'monospace', marginBottom: 14,
    }}>{children}</div>
  );
}

function Card({ children, style = {} }) {
  return (
    <div style={{
      background: '#0f1218', border: '1px solid rgba(255,255,255,0.07)',
      borderRadius: 16, ...style,
    }}>{children}</div>
  );
}

// ─── KPI Bar ──────────────────────────────────────────────────────────────────

function KPIBar({ kpi }) {
  const items = [
    { label: 'Uptime',          val: kpi.uptime_pct != null ? `${kpi.uptime_pct}%` : '—', color: '#4ade80', accent: '#4ade80' },
    { label: 'Active Incidents',val: kpi.active_incidents ?? '—',                          color: '#fbbf24', accent: '#fbbf24' },
    { label: 'Auto-Resolved 24h',val: kpi.resolved_24h ?? '—',                            color: '#4ade80', accent: '#4ade80' },
    { label: 'Avg MTTR',        val: kpi.avg_mttr_minutes != null ? `${kpi.avg_mttr_minutes}m` : '—', color: '#4d9eff', accent: '#4d9eff' },
    { label: 'SLA Adherence',   val: kpi.sla_adherence_pct != null ? `${kpi.sla_adherence_pct}%` : '—', color: '#2dd4bf', accent: '#2dd4bf' },
  ];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 12, marginBottom: 28 }}>
      {items.map(({ label, val, color, accent }) => (
        <Card key={label} style={{ padding: '16px 18px', borderBottom: `2px solid ${accent}`, position: 'relative', overflow: 'hidden' }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#545c72', textTransform: 'uppercase', letterSpacing: '.07em', fontFamily: 'monospace', marginBottom: 8 }}>{label}</div>
          <div style={{ fontSize: 26, fontWeight: 800, color, letterSpacing: '-0.03em' }}>{val}</div>
        </Card>
      ))}
    </div>
  );
}

// ─── Agent Topology SVG ───────────────────────────────────────────────────────

function TopologySVG() {
  return (
    <svg width="100%" viewBox="0 0 760 350" style={{ display: 'block' }}>
      <defs>
        <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </marker>
        <style>{`
          @keyframes dashflow { to { stroke-dashoffset: -24; } }
          @keyframes pingout  { 0%{r:4;opacity:.9} 100%{r:16;opacity:0} }
          .aflow { animation: dashflow 1.4s linear infinite; }
          .aflow2{ animation: dashflow 1.8s linear infinite; }
          .aflow3{ animation: dashflow 2.2s linear infinite; }
          .ping  { animation: pingout  2s ease-out infinite; }
          .ping2 { animation: pingout  2s ease-out infinite .7s; }
        `}</style>
      </defs>

      {/* Layer lines */}
      {[185,380,575].map(x => (
        <line key={x} x1={x} y1={10} x2={x} y2={340} stroke="rgba(255,255,255,0.04)" strokeWidth={1}/>
      ))}

      {/* Layer labels */}
      {[
        [92,'#4d9eff','MONITORING'],
        [282,'#a78bfa','INTELLIGENCE'],
        [477,'#2dd4bf','REMEDIATION'],
        [662,'#fbbf24','REPORTING'],
      ].map(([x,c,t])=>(
        <text key={t} x={x} y={18} textAnchor="middle" fontFamily="monospace" fontSize={9} fill={c} fontWeight={600} letterSpacing={1} opacity={.8}>{t}</text>
      ))}

      {/* A2A flow lines */}
      <path className="aflow"  d="M170 100 C215 100 235 185 258 185" fill="none" stroke="#4d9eff" strokeWidth={1.2} strokeDasharray="5 4" opacity={.6} markerEnd="url(#arr)"/>
      <path className="aflow2" d="M170 185 L258 185"                  fill="none" stroke="#4d9eff" strokeWidth={1.2} strokeDasharray="5 4" opacity={.6} markerEnd="url(#arr)"/>
      <path className="aflow3" d="M170 270 C215 270 235 185 258 185" fill="none" stroke="#4d9eff" strokeWidth={1.2} strokeDasharray="5 4" opacity={.6} markerEnd="url(#arr)"/>
      <path className="aflow"  d="M362 165 C405 165 410 110 448 110" fill="none" stroke="#a78bfa" strokeWidth={1.2} strokeDasharray="5 4" opacity={.6} markerEnd="url(#arr)"/>
      <path className="aflow2" d="M362 205 C405 205 410 260 448 260" fill="none" stroke="#a78bfa" strokeWidth={1.2} strokeDasharray="5 4" opacity={.6} markerEnd="url(#arr)"/>
      <path className="aflow"  d="M562 110 C610 110 625 175 640 175" fill="none" stroke="#2dd4bf" strokeWidth={1.2} strokeDasharray="5 4" opacity={.6} markerEnd="url(#arr)"/>
      <path className="aflow3" d="M562 260 C610 260 625 195 640 195" fill="none" stroke="#2dd4bf" strokeWidth={1.2} strokeDasharray="5 4" opacity={.6} markerEnd="url(#arr)"/>

      {/* Monitoring nodes */}
      {[
        [14,68,'Server Monitor','240 hosts · 15s','#4d9eff'],
        [14,153,'Cloud Monitor','12 regions · 3 clouds','#4d9eff'],
        [14,238,'App Health','38 svcs · OpenTelemetry','#fbbf24'],
      ].map(([x,y,title,sub,stroke],i)=>(
        <g key={title}>
          <rect x={x} y={y} width={156} height={64} rx={10} fill={`${stroke}10`} stroke={stroke} strokeWidth={0.8} strokeOpacity={.5}/>
          <text x={x+78} y={y+24} textAnchor="middle" fontFamily="Syne,sans-serif" fontSize={12} fontWeight={700} fill="#e8eaf0">{title}</text>
          <text x={x+78} y={y+42} textAnchor="middle" fontFamily="monospace" fontSize={10} fill="rgba(139,146,168,.9)">{sub}</text>
          <circle cx={x+140} cy={y+12} r={4} fill={i===2?'#fbbf24':'#4ade80'} opacity={.9}/>
          <circle className={i%2===0?"ping":"ping2"} cx={x+140} cy={y+12} r={4} fill={i===2?'#fbbf24':'#4ade80'} opacity={0}/>
        </g>
      ))}

      {/* Predictive */}
      <rect x={202} y={148} width={160} height={74} rx={12} fill="rgba(167,139,250,0.1)" stroke="#a78bfa" strokeWidth={1} strokeOpacity={.6}/>
      <text x={282} y={178} textAnchor="middle" fontFamily="Syne,sans-serif" fontSize={13} fontWeight={700} fill="#e8eaf0">Predictive</text>
      <text x={282} y={196} textAnchor="middle" fontFamily="Syne,sans-serif" fontSize={12} fontWeight={600} fill="#e8eaf0">Failure Agent</text>
      <text x={282} y={213} textAnchor="middle" fontFamily="monospace" fontSize={10} fill="rgba(167,139,250,.8)">LSTM · 72h forecast</text>

      {/* Remediation agents */}
      {[
        [396,78,'Remediation Agent','Policy · Runbooks','#2dd4bf','#fbbf24'],
        [396,228,'Deployment Agent','K8s · Terraform · Ansible','#2dd4bf','#4ade80'],
      ].map(([x,y,title,sub,stroke,dotc])=>(
        <g key={title}>
          <rect x={x} y={y} width={166} height={64} rx={10} fill={`${stroke}10`} stroke={stroke} strokeWidth={0.8} strokeOpacity={.5}/>
          <text x={x+83} y={y+24} textAnchor="middle" fontFamily="Syne,sans-serif" fontSize={12} fontWeight={700} fill="#e8eaf0">{title}</text>
          <text x={x+83} y={y+42} textAnchor="middle" fontFamily="monospace" fontSize={10} fill="rgba(139,146,168,.9)">{sub}</text>
          <circle cx={x+152} cy={y+12} r={4} fill={dotc} opacity={.9}/>
        </g>
      ))}

      {/* Reporting */}
      <rect x={588} y={148} width={148} height={74} rx={12} fill="rgba(251,191,36,0.08)" stroke="#fbbf24" strokeWidth={0.8} strokeOpacity={.5}/>
      <text x={662} y={176} textAnchor="middle" fontFamily="Syne,sans-serif" fontSize={12} fontWeight={700} fill="#e8eaf0">Reporting Agent</text>
      <text x={662} y={194} textAnchor="middle" fontFamily="Syne,sans-serif" fontSize={11} fontWeight={600} fill="#e8eaf0">&amp; SLA Tracker</text>
      <text x={662} y={212} textAnchor="middle" fontFamily="monospace" fontSize={10} fill="rgba(251,191,36,.7)">Executive dashboards</text>
      <circle cx={726} cy={160} r={4} fill="#4ade80" opacity={.9}/>
    </svg>
  );
}

// ─── Topology View ────────────────────────────────────────────────────────────

function TopologyView({ agents }) {
  return (
    <div>
      <SectionLabel>Agent topology — live A2A communication flow</SectionLabel>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20 }}>
        <Card style={{ padding: 24, overflow: 'hidden' }}>
          <TopologySVG />
        </Card>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {agents.map(agent => {
            const meta = AGENT_META[agent.agent_type] || {};
            return (
              <Card key={agent.agent_type} style={{ padding: '14px 16px', cursor: 'pointer', transition: 'border-color .2s' }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.18)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <StatusDot status={agent.status} />
                  <span style={{ fontSize: 12, fontWeight: 700 }}>{meta.label || agent.agent_type}</span>
                  <span style={{ fontSize: 10, color: meta.color, fontFamily: 'monospace', marginLeft: 'auto', fontWeight: 600 }}>{meta.layer}</span>
                </div>
                <div style={{ fontSize: 11, color: '#545c72', fontFamily: 'monospace', marginBottom: 8 }}>{agent.description}</div>
                <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                  {(agent.pills || []).map((p, i) => <Pill key={i} label={p.label} cls={p.cls} />)}
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── Incidents View ───────────────────────────────────────────────────────────

function IncidentsView({ incidents, onSimulate, simulating }) {
  const [filter, setFilter] = useState('all');
  const filtered = filter === 'all' ? incidents
    : filter === 'active' ? incidents.filter(i => i.status !== 'resolved')
    : incidents.filter(i => i.severity === filter.toUpperCase() || i.status === filter);

  const statusStyle = {
    remediating: { bg: 'rgba(251,191,36,0.12)', color: '#fbbf24' },
    resolved:    { bg: 'rgba(74,222,128,0.10)',  color: '#4ade80' },
    triaging:    { bg: 'rgba(77,158,255,0.12)',  color: '#4d9eff' },
    preempting:  { bg: 'rgba(167,139,250,0.12)', color: '#a78bfa' },
    open:        { bg: 'rgba(248,113,113,0.12)', color: '#f87171' },
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>
        <SectionLabel>Active &amp; recent incidents — agent-managed</SectionLabel>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {['all','active','resolved','P1','P2','P3'].map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: '5px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600,
              fontFamily: 'monospace', cursor: 'pointer', transition: 'all .15s',
              border: `1px solid ${filter===f?'#4d9eff':'rgba(255,255,255,0.1)'}`,
              background: filter===f?'rgba(77,158,255,0.12)':'transparent',
              color: filter===f?'#4d9eff':'#8b92a8',
            }}>{f}</button>
          ))}
          <select onChange={e => onSimulate(e.target.value)} defaultValue=""
            style={{
              padding: '5px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600,
              fontFamily: 'monospace', cursor: 'pointer',
              border: '1px solid rgba(77,158,255,0.3)',
              background: 'rgba(77,158,255,0.1)', color: '#4d9eff',
            }}
            disabled={simulating}
          >
            <option value="" disabled>{simulating ? 'Simulating…' : '⚡ Simulate'}</option>
            <option value="oom">OOMKill</option>
            <option value="cpu">CPU Saturation</option>
            <option value="network">Packet Loss</option>
            <option value="latency">Latency Spike</option>
            <option value="disk">Disk Pressure</option>
          </select>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: '#545c72', fontFamily: 'monospace', fontSize: 12 }}>No incidents match filter</div>
        )}
        {filtered.map(inc => {
          const ss = statusStyle[inc.status] || statusStyle.open;
          const chain = inc.agent_chain || [];
          return (
            <Card key={inc.id} style={{
              padding: '16px 18px', display: 'flex', gap: 14, alignItems: 'flex-start',
              borderLeft: `3px solid ${SEV_COLORS[inc.severity] || '#8b92a8'}`,
              cursor: 'pointer', transition: 'border-color .2s',
            }}
              onMouseEnter={e => e.currentTarget.style.background = '#161b24'}
              onMouseLeave={e => e.currentTarget.style.background = '#0f1218'}
            >
              <div style={{
                width: 32, height: 32, borderRadius: 8, display: 'flex', alignItems: 'center',
                justifyContent: 'center', fontSize: 10, fontWeight: 800, fontFamily: 'monospace',
                flexShrink: 0, background: `${SEV_COLORS[inc.severity]}20`, color: SEV_COLORS[inc.severity],
              }}>{inc.severity}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>{inc.title}</div>
                <div style={{ fontSize: 11, color: '#8b92a8', fontFamily: 'monospace', lineHeight: 1.5, marginBottom: 8 }}>
                  {inc.runbook && <span style={{ color: '#a78bfa', marginRight: 8 }}>#{inc.runbook}</span>}
                  {inc.host && <span style={{ marginRight: 8 }}>{inc.host}</span>}
                  {inc.region && <span style={{ marginRight: 8 }}>{inc.region}</span>}
                  {inc.mttr_seconds && <span>MTTR: {(inc.mttr_seconds/60).toFixed(1)}m</span>}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, fontFamily: 'monospace', color: '#545c72', flexWrap: 'wrap' }}>
                  {chain.map((c, i) => (
                    <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ padding: '2px 7px', borderRadius: 4, background: '#1c2333', color: '#8b92a8', fontWeight: 600 }}>
                        {AGENT_META[c]?.label || c}
                      </span>
                      {i < chain.length - 1 && <span style={{ color: '#545c72' }}>→</span>}
                    </span>
                  ))}
                </div>
              </div>
              <div style={{
                fontSize: 10, fontWeight: 700, padding: '4px 10px', borderRadius: 99,
                alignSelf: 'flex-start', flexShrink: 0, fontFamily: 'monospace',
                background: ss.bg, color: ss.color,
              }}>{inc.status.replace('_', '-')}</div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ─── Predictions View ─────────────────────────────────────────────────────────

function PredictionsView({ predictions }) {
  return (
    <div>
      <SectionLabel>72-hour failure horizon — Predictive Failure Agent · LSTM ensemble</SectionLabel>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 14 }}>
        {predictions.map(p => {
          const rc = RISK_COLOR(p.probability);
          const pct = Math.round(p.probability * 100);
          const riskLabel = p.probability >= 0.75 ? 'HIGH' : p.probability >= 0.5 ? 'MEDIUM' : 'LOW';
          return (
            <Card key={p.id} style={{ padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>
                    {p.failure_class.replace(/([A-Z])/g, ' $1').trim()} — {p.target}
                  </div>
                  <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 4, fontFamily: 'monospace', background: `${rc}20`, color: rc }}>
                    {riskLabel}
                  </span>
                </div>
                <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.03em', color: rc }}>{pct}%</div>
              </div>
              <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, marginBottom: 14 }}>
                <div style={{ height: 4, width: `${pct}%`, background: rc, borderRadius: 2, transition: 'width .8s ease' }} />
              </div>
              <div style={{ fontSize: 11, color: '#8b92a8', fontFamily: 'monospace', lineHeight: 1.7, marginBottom: 10 }}>
                {p.signal_description}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
                <span style={{ fontSize: 10, fontWeight: 600, padding: '4px 10px', borderRadius: 6, background: '#1c2333', color: '#8b92a8', fontFamily: 'monospace' }}>
                  Runbook: {p.recommended_runbook}
                </span>
                <span style={{ fontSize: 10, fontFamily: 'monospace', color: '#545c72' }}>
                  Horizon: <span style={{ color: '#fbbf24', fontWeight: 700 }}>{p.horizon_minutes}m</span>
                </span>
              </div>
            </Card>
          );
        })}
        {predictions.length === 0 && (
          <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: 40, color: '#545c72', fontFamily: 'monospace', fontSize: 12 }}>
            No active predictions · monitoring...
          </div>
        )}
      </div>
    </div>
  );
}

// ─── A2A Log Stream View ──────────────────────────────────────────────────────

const AG_STYLE = {
  server_monitor: { color: '#4d9eff', tag: '[MON-SVR]' },
  cloud_monitor:  { color: '#4d9eff', tag: '[MON-CLOUD]' },
  app_health:     { color: '#4d9eff', tag: '[MON-APP]' },
  predictive:     { color: '#a78bfa', tag: '[PRED]' },
  remediation:    { color: '#2dd4bf', tag: '[REM]' },
  deployment:     { color: '#4ade80', tag: '[DEP]' },
  reporting:      { color: '#fbbf24', tag: '[REP]' },
};

function LogsView({ logs, a2aMessages }) {
  const logRef = useRef(null);
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  return (
    <div>
      <SectionLabel>Agent-to-agent message bus — real-time event stream</SectionLabel>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 20 }}>
        <Card style={{ overflow: 'hidden' }}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid rgba(255,255,255,0.07)', fontSize: 12, fontWeight: 700, fontFamily: 'monospace', color: '#8b92a8' }}>
            📡 A2A Event Stream
          </div>
          <div ref={logRef} style={{
            padding: '14px 18px', maxHeight: 500, overflowY: 'auto',
            fontFamily: 'monospace', fontSize: 11, lineHeight: 1.9,
          }}>
            {logs.map((log, i) => {
              const fromStyle = AG_STYLE[log.from_agent] || { color: '#8b92a8', tag: `[${log.from_agent}]` };
              const toStyle   = AG_STYLE[log.to_agent]   || { color: '#8b92a8', tag: `[${log.to_agent}]` };
              const ts = new Date(log.timestamp).toLocaleTimeString('en-GB', { hour12: false });
              const action = log.payload?.action || log.payload?.alert_type || log.payload?.step || 'message';
              const target  = log.payload?.target || log.payload?.host || log.payload?.service || log.payload?.region || '';
              return (
                <div key={log.id || i} style={{ display: 'flex', gap: 10, padding: '1px 0', animation: i === logs.length-1 ? 'fadein .2s ease' : undefined }}>
                  <span style={{ color: '#545c72', flexShrink: 0 }}>{ts}</span>
                  <span style={{ color: fromStyle.color, fontWeight: 600, flexShrink: 0 }}>{fromStyle.tag}</span>
                  <span style={{ color: '#8b92a8' }}>
                    A2A→<span style={{ color: toStyle.color }}>{toStyle.tag}</span>
                    {' '}<span style={{ color: '#e8eaf0' }}>{action}</span>
                    {target && <span style={{ color: '#545c72' }}> · {target}</span>}
                    {log.payload?.incident_id && <span style={{ color: '#a78bfa' }}> {log.payload.incident_id}</span>}
                    {log.payload?.probability && <span style={{ color: '#fbbf24' }}> prob={log.payload.probability}</span>}
                  </span>
                </div>
              );
            })}
            {logs.length === 0 && (
              <div style={{ color: '#545c72', fontFamily: 'monospace', fontSize: 12 }}>Waiting for A2A events…</div>
            )}
          </div>
        </Card>

        {/* Latest A2A payloads */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          <Card style={{ padding: 16, flex: 1 }}>
            <div style={{ fontSize: 11, fontWeight: 700, fontFamily: 'monospace', color: '#545c72', marginBottom: 12 }}>
              // Latest A2A payloads
            </div>
            {a2aMessages.slice(0, 5).map((msg, i) => {
              const fs = AG_STYLE[msg.from_agent] || {};
              const ts = AG_STYLE[msg.to_agent]   || {};
              return (
                <div key={i} style={{
                  background: '#161b24', border: '1px solid rgba(255,255,255,0.07)',
                  borderRadius: 10, padding: '10px 12px', marginBottom: 8,
                  fontFamily: 'monospace', fontSize: 10, lineHeight: 1.7,
                  animation: 'fadein .3s ease',
                }}>
                  <div style={{ fontWeight: 700, marginBottom: 4, color: fs.color }}>
                    {fs.tag} → <span style={{ color: ts.color }}>{ts.tag}</span>
                  </div>
                  <div style={{ color: '#545c72' }}>
                    {Object.entries(msg.payload || {}).slice(0, 4).map(([k, v]) => (
                      <div key={k}>&nbsp;&nbsp;<span style={{ color: '#8b92a8' }}>{k}:</span> <span style={{ color: typeof v === 'number' ? '#fbbf24' : '#4ade80' }}>"{String(v)}"</span></div>
                    ))}
                  </div>
                </div>
              );
            })}
          </Card>
        </div>
      </div>
    </div>
  );
}

// ─── Metrics View ─────────────────────────────────────────────────────────────

function MetricsView({ hostMetrics, appMetrics }) {
  const chartData = hostMetrics.slice(0, 8).map(m => ({
    name: m.host.replace('payment-api-','pa-').replace('-cluster-','clus-'),
    cpu: m.cpu_pct,
    mem: m.mem_pct,
    disk: m.disk_pct,
  }));
  const appData = appMetrics.slice(0, 6).map(m => ({
    name: m.service.replace('-service','').replace('-api',''),
    p99: m.p99_ms,
    err: m.error_rate_pct,
    rps: m.rps,
  }));

  const tt = { contentStyle: { background: '#0f1218', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }, labelStyle: { color: '#8b92a8' } };

  return (
    <div>
      <SectionLabel>Live telemetry — host &amp; application metrics</SectionLabel>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        <Card style={{ padding: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 16, color: '#8b92a8', fontFamily: 'monospace' }}>Host Resource Usage</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 0, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)"/>
              <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#545c72', fontFamily: 'monospace' }} axisLine={false} tickLine={false}/>
              <YAxis tick={{ fontSize: 9, fill: '#545c72', fontFamily: 'monospace' }} axisLine={false} tickLine={false} domain={[0,100]}/>
              <Tooltip {...tt}/>
              <Bar dataKey="cpu"  fill="#4d9eff" radius={[3,3,0,0]} opacity={.8} name="CPU %"/>
              <Bar dataKey="mem"  fill="#a78bfa" radius={[3,3,0,0]} opacity={.8} name="Mem %"/>
              <Bar dataKey="disk" fill="#2dd4bf" radius={[3,3,0,0]} opacity={.8} name="Disk %"/>
            </BarChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 12, marginTop: 8, justifyContent: 'center' }}>
            {[['#4d9eff','CPU'],['#a78bfa','Memory'],['#2dd4bf','Disk']].map(([c,l])=>(
              <span key={l} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10, color: '#8b92a8', fontFamily: 'monospace' }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: c, display: 'inline-block' }}/>
                {l}
              </span>
            ))}
          </div>
        </Card>

        <Card style={{ padding: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 16, color: '#8b92a8', fontFamily: 'monospace' }}>App p99 Latency (ms)</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={appData} margin={{ top: 0, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)"/>
              <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#545c72', fontFamily: 'monospace' }} axisLine={false} tickLine={false}/>
              <YAxis tick={{ fontSize: 9, fill: '#545c72', fontFamily: 'monospace' }} axisLine={false} tickLine={false}/>
              <Tooltip {...tt}/>
              <Bar dataKey="p99" fill="#fbbf24" radius={[3,3,0,0]} opacity={.85} name="p99 ms"/>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Host metric table */}
      <Card style={{ padding: 20 }}>
        <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 16, color: '#8b92a8', fontFamily: 'monospace' }}>Host detail table</div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, fontFamily: 'monospace' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
              {['Host','CPU %','Mem %','Disk %','Status'].map(h=>(
                <th key={h} style={{ padding: '6px 10px', textAlign: 'left', color: '#545c72', fontWeight: 600, fontSize: 10 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {hostMetrics.map(m => {
              const alert = m.mem_pct > 85 || m.cpu_pct > 85;
              return (
                <tr key={m.host} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '7px 10px', color: alert ? '#fbbf24' : '#e8eaf0', fontWeight: alert ? 700 : 400 }}>{m.host}</td>
                  <td style={{ padding: '7px 10px', color: m.cpu_pct > 85 ? '#f87171' : '#8b92a8' }}>{m.cpu_pct.toFixed(1)}</td>
                  <td style={{ padding: '7px 10px', color: m.mem_pct > 85 ? '#f87171' : '#8b92a8' }}>{m.mem_pct.toFixed(1)}</td>
                  <td style={{ padding: '7px 10px', color: '#8b92a8' }}>{m.disk_pct.toFixed(1)}</td>
                  <td style={{ padding: '7px 10px' }}>
                    <Pill label={alert ? 'Alert' : 'OK'} cls={alert ? 'amber' : 'green'} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

// ─── Architecture View ────────────────────────────────────────────────────────

function ArchitectureView() {
  const cards = [
    {
      icon: '🔭', title: 'Data Sources', sub: 'Ingestion layer', color: '#4d9eff',
      items: [
        ['Cloud monitoring logs','CloudWatch · Azure Monitor · GCP Ops Suite · Kinesis'],
        ['Application telemetry','OpenTelemetry traces, metrics, logs · 38 instrumented services'],
        ['Incident logs','Historical incident database · feeds LSTM training pipeline'],
        ['CMDB','Service dependency graphs · ownership · runbook mapping'],
      ],
    },
    {
      icon: '🧠', title: 'AI & ML Stack', sub: 'Intelligence layer', color: '#a78bfa',
      items: [
        ['LSTM ensemble','Multi-variate time-series failure prediction · 72h horizon · 94.1% accuracy'],
        ['Adaptive learning','Online policy updates from outcomes · continuous retraining'],
        ['Anomaly detection','Isolation Forest + DBSCAN for multi-dimensional outlier detection'],
        ['Decision policies','RL-learned auto-approval thresholds per severity × SLA class'],
      ],
    },
    {
      icon: '⚙️', title: 'Orchestration & Execution', sub: 'Remediation layer', color: '#2dd4bf',
      items: [
        ['Multi-agent framework','Event-driven A2A message bus · async task queuing · conflict resolution'],
        ['Kubernetes HPA/VPA','Horizontal and vertical pod autoscaling · GitOps via ArgoCD'],
        ['Terraform','Cloud resource provisioning · state-locked · drift detection'],
        ['Runbook engine','140+ codified runbooks · parameterised · rollback-safe'],
      ],
    },
    {
      icon: '📊', title: 'Enterprise Impact', sub: 'Business outcomes', color: '#fbbf24',
      items: [
        ['Downtime reduction','87% fewer outages via pre-emptive remediation'],
        ['MTTR improvement','4.2 min avg vs 11.8 min manual — 63% reduction'],
        ['Resource optimisation','22% cloud cost reduction via right-sizing intelligence'],
        ['SLA adherence','99.1% uptime maintained — proactive breach prevention'],
      ],
    },
  ];

  const workflow = [
    { num: '1', label: 'Monitoring Agents', desc: 'Poll servers, cloud, network & app health · emit telemetry to A2A bus', color: '#4d9eff' },
    { num: '2', label: 'Predictive Failure', desc: 'LSTM scores failure probability · classifies incident class · fires directive', color: '#a78bfa' },
    { num: '3', label: 'Remediation & Deployment', desc: 'Policy-approved fixes: scale K8s, reroute traffic, restart, provision', color: '#2dd4bf' },
    { num: '4', label: 'Reporting Agent', desc: 'Aggregates MTTR & SLA, updates dashboards, compliance records', color: '#fbbf24' },
  ];

  return (
    <div>
      <SectionLabel>System architecture &amp; technical design</SectionLabel>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 16, marginBottom: 20 }}>
        {cards.map(({ icon, title, sub, color, items }) => (
          <Card key={title} style={{ padding: 22 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14, paddingBottom: 14, borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
              <div style={{ width: 34, height: 34, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, background: `${color}18`, flexShrink: 0 }}>
                {icon}
              </div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 700 }}>{title}</div>
                <div style={{ fontSize: 11, color: '#545c72', fontFamily: 'monospace' }}>{sub}</div>
              </div>
            </div>
            {items.map(([k, v]) => (
              <div key={k} style={{ display: 'flex', gap: 10, padding: '7px 0', borderBottom: '1px solid rgba(255,255,255,0.04)', fontSize: 12, lineHeight: 1.5 }}>
                <span style={{ color: '#545c72', flexShrink: 0, marginTop: 1, fontSize: 10 }}>▸</span>
                <span><strong style={{ color, fontWeight: 600 }}>{k}</strong>{' — '}<span style={{ color: '#8b92a8' }}>{v}</span></span>
              </div>
            ))}
          </Card>
        ))}
      </div>

      {/* Workflow strip */}
      <Card style={{ padding: 24 }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: '#545c72', textTransform: 'uppercase', letterSpacing: '.1em', fontFamily: 'monospace', marginBottom: 24 }}>
          Agent workflow pipeline
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 0 }}>
          {workflow.map(({ num, label, desc, color }, i) => (
            <div key={num} style={{ textAlign: 'center', padding: '0 12px', position: 'relative' }}>
              {i < 3 && (
                <div style={{
                  position: 'absolute', right: 0, top: 27, width: '100%',
                  height: 2, background: `linear-gradient(90deg,${color},${workflow[i+1].color})`, opacity: .25,
                }}/>
              )}
              <div style={{
                width: 56, height: 56, borderRadius: '50%', margin: '0 auto 12px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 22, fontWeight: 800, border: `2px solid ${color}`,
                color, background: '#0a0c10', position: 'relative', zIndex: 1,
                boxShadow: `0 0 20px ${color}30`,
              }}>{num}</div>
              <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 6 }}>{label}</div>
              <div style={{ fontSize: 10, color: '#545c72', fontFamily: 'monospace', lineHeight: 1.6 }}>{desc}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ─── Root App ─────────────────────────────────────────────────────────────────

const TABS = ['topology','incidents','predictions','logs','metrics','architecture'];
const TAB_LABELS = {
  topology:     'Agent Topology',
  incidents:    'Incidents',
  predictions:  'Predictions',
  logs:         'A2A Log Stream',
  metrics:      'Live Metrics',
  architecture: 'Architecture',
};

export default function App() {
  const [tab, setTab] = useState('topology');
  const [kpi, setKpi] = useState({});
  const [incidents, setIncidents] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [agents, setAgents] = useState([]);
  const [logs, setLogs] = useState([]);
  const [a2aMessages, setA2aMessages] = useState([]);
  const [hostMetrics, setHostMetrics] = useState([]);
  const [appMetrics, setAppMetrics] = useState([]);
  const [simulating, setSimulating] = useState(false);
  const [backendOk, setBackendOk] = useState(null);

  // Initial REST fetch
  useEffect(() => {
    Promise.all([
      api.kpi(), api.incidents(), api.predictions(),
      api.agents(), api.logs(80), api.hostMetrics(), api.appMetrics(),
    ]).then(([k, inc, preds, ag, lg, hm, am]) => {
      setKpi(k); setIncidents(inc); setPredictions(preds);
      setAgents(ag); setLogs(lg); setHostMetrics(hm); setAppMetrics(am);
      setBackendOk(true);
    }).catch(() => setBackendOk(false));

    // Refresh metrics every 15s
    const t = setInterval(() => {
      api.hostMetrics().then(setHostMetrics).catch(() => {});
      api.appMetrics().then(setAppMetrics).catch(() => {});
    }, 15000);
    return () => clearInterval(t);
  }, []);

  // WebSocket handler
  const onEvent = useCallback((msg) => {
    const { event, data } = msg;
    if (event === 'kpi') setKpi(data);
    else if (event === 'incidents_snapshot') setIncidents(data);
    else if (event === 'predictions_snapshot') setPredictions(data);
    else if (event === 'agents_snapshot') setAgents(data);
    else if (event === 'log_snapshot') setLogs(data);
    else if (event === 'incident') {
      setIncidents(prev => {
        const existing = prev.find(i => i.id === data.id);
        if (existing) return prev.map(i => i.id === data.id ? data : i);
        return [data, ...prev];
      });
    }
    else if (event === 'incident_update') {
      setIncidents(prev => prev.map(i => i.id === data.id ? { ...i, ...data } : i));
    }
    else if (event === 'prediction') {
      setPredictions(prev => [data, ...prev.slice(0, 19)]);
    }
    else if (event === 'a2a_log') {
      setLogs(prev => [...prev.slice(-200), data]);
      setA2aMessages(prev => [data, ...prev.slice(0, 9)]);
    }
    else if (event === 'metric') {
      if (data.type === 'host') {
        setHostMetrics(prev => {
          const filtered = prev.filter(m => m.host !== data.host);
          return [data, ...filtered].slice(0, 20);
        });
      } else if (data.type === 'app') {
        setAppMetrics(prev => {
          const filtered = prev.filter(m => m.service !== data.service);
          return [data, ...filtered].slice(0, 15);
        });
      }
    }
  }, []);

  const { connected } = useWebSocket(WS_URL, onEvent);

  const handleSimulate = async (type) => {
    if (!type || simulating) return;
    setSimulating(true);
    try { await api.simulateIncident(type); }
    catch (e) { console.error('Simulate failed:', e); }
    finally { setTimeout(() => setSimulating(false), 3000); }
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0a0c10', color: '#e8eaf0' }}>
      {/* Background grid */}
      <div style={{
        position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0,
        backgroundImage: 'linear-gradient(rgba(77,158,255,0.025) 1px,transparent 1px),linear-gradient(90deg,rgba(77,158,255,0.025) 1px,transparent 1px)',
        backgroundSize: '40px 40px',
      }}/>
      <div style={{ position: 'relative', zIndex: 1, maxWidth: 1380, margin: '0 auto', padding: '0 24px 60px' }}>

        {/* Nav */}
        <nav style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '20px 0 24px', borderBottom: '1px solid rgba(255,255,255,0.07)',
          marginBottom: 28, flexWrap: 'wrap', gap: 12,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10, fontSize: 18,
              background: 'linear-gradient(135deg,#4d9eff,#a78bfa)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>⬡</div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: '-0.02em', fontFamily: 'Syne,sans-serif' }}>
                Autonomous IT Ops Platform
              </div>
              <div style={{ fontSize: 11, color: '#545c72', fontFamily: 'monospace' }}>
                Multi-agent · A2A orchestration · Real-time
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {TABS.map(t => (
              <button key={t} onClick={() => setTab(t)} style={{
                padding: '6px 14px', borderRadius: 20, fontSize: 12, fontWeight: 600,
                cursor: 'pointer', transition: 'all .2s', fontFamily: 'Syne,sans-serif',
                border: `1px solid ${tab===t?'#4d9eff':'rgba(255,255,255,0.1)'}`,
                background: tab===t?'#4d9eff':'transparent',
                color: tab===t?'#fff':'#8b92a8',
              }}>{TAB_LABELS[t]}</button>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6, fontSize: 12,
              color: connected ? '#4ade80' : '#f87171', fontFamily: 'monospace', fontWeight: 500,
              padding: '6px 14px', border: `1px solid ${connected?'rgba(74,222,128,0.2)':'rgba(248,113,113,0.2)'}`,
              borderRadius: 20, background: connected ? 'rgba(74,222,128,0.08)' : 'rgba(248,113,113,0.08)',
            }}>
              <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: connected ? '#4ade80' : '#f87171',
                animation: connected ? 'pulsedot 2s infinite' : 'none',
              }}/>
              {connected ? '6 agents live' : backendOk === false ? 'Backend offline' : 'Connecting…'}
            </div>
          </div>
        </nav>

        {backendOk === false && (
          <div style={{
            background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)',
            borderRadius: 12, padding: '14px 20px', marginBottom: 20,
            fontSize: 12, fontFamily: 'monospace', color: '#f87171',
          }}>
            ⚠ Backend not reachable. Start with: <code style={{ background: 'rgba(0,0,0,0.3)', padding: '2px 6px', borderRadius: 4 }}>cd backend && uvicorn main:app --reload</code>
          </div>
        )}

        <KPIBar kpi={kpi} />

        {tab === 'topology'     && <TopologyView     agents={agents} />}
        {tab === 'incidents'    && <IncidentsView    incidents={incidents} onSimulate={handleSimulate} simulating={simulating} />}
        {tab === 'predictions'  && <PredictionsView  predictions={predictions} />}
        {tab === 'logs'         && <LogsView         logs={logs} a2aMessages={a2aMessages} />}
        {tab === 'metrics'      && <MetricsView      hostMetrics={hostMetrics} appMetrics={appMetrics} />}
        {tab === 'architecture' && <ArchitectureView />}
      </div>
    </div>
  );
}
