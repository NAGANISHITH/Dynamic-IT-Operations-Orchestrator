// services/api.js
const BASE = process.env.REACT_APP_API_URL || '';

async function get(path) {
  const res = await fetch(BASE + path);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

async function post(path, body = {}) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export const api = {
  kpi:              () => get('/api/kpi'),
  incidents:        (status) => get(`/api/incidents${status ? `?status=${status}` : ''}`),
  predictions:      () => get('/api/predictions'),
  agents:           () => get('/api/agents'),
  logs:             (limit = 100) => get(`/api/logs?limit=${limit}`),
  hostMetrics:      () => get('/api/metrics/hosts'),
  appMetrics:       () => get('/api/metrics/apps'),
  simulateIncident: (type = 'oom') => post(`/api/incidents/simulate?incident_type=${type}`),
  health:           () => get('/health'),
};
