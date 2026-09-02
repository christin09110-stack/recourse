// Thin fetch client for the Recourse API. One function per route. No caching,
// no retry policy, no business logic — the store decides what a response means;
// this file only knows how to ask for it.
//
// BASE is already "/api". **Every path below is relative to it.** Writing one
// with the prefix spelled out asks for /api/api/demo/reset, and because the
// console is served from a static mount at "/", that comes back as 405 — a
// method error for a route that simply is not there. Muster shipped exactly
// that. tests/api/test_console_routes.py reads these paths out of this file and
// checks them against the app's own route table so it cannot happen twice.

const BASE = import.meta.env.VITE_RECOURSE_API || '/api'

async function request(path, options = {}) {
  const { body, ...rest } = options
  // A multipart upload must carry the boundary the browser generates, so the
  // JSON content-type is set only when we are actually sending JSON.
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData
  const res = await fetch(`${BASE}${path}`, {
    ...rest,
    headers: isForm ? rest.headers : { 'Content-Type': 'application/json', ...rest.headers },
    ...(body === undefined ? {} : { body }),
  })
  if (!res.ok) {
    let detail = ''
    try {
      const problem = await res.json()
      const named = problem?.detail
      detail = named ? ` — ${typeof named === 'string' ? named : JSON.stringify(named)}` : ''
    } catch {
      // not JSON; fall through with no detail
    }
    throw new Error(`${options.method || 'GET'} ${path} failed: ${res.status}${detail}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export function getWorld() {
  return request('/world')
}

export function getCase() {
  return request('/case')
}

export function getDenials() {
  return request('/denials')
}

export function getDeadlines() {
  return request('/deadlines')
}

export function getAppeals() {
  return request('/appeals')
}

export function getDecisions() {
  return request('/decisions')
}

export function answerDecision(id, body) {
  return request(`/decisions/${encodeURIComponent(id)}/answer`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function getJournal() {
  return request('/journal')
}

export function getTimeline() {
  return request('/timeline')
}

export function getAutonomy() {
  return request('/autonomy')
}

export function setAutonomy(level) {
  return request('/autonomy', { method: 'PUT', body: JSON.stringify({ level }) })
}

export function triage() {
  return request('/triage', { method: 'POST' })
}

export function press() {
  return request('/press', { method: 'POST' })
}

export function uploadEob(file) {
  const form = new FormData()
  form.append('file', file, file.name)
  return request('/eob', { method: 'POST', body: form })
}

export function resetDemo() {
  return request('/demo/reset', { method: 'POST' })
}

// A download, not a fetch: the browser follows this href and saves the file the
// content-disposition names. Same BASE, same rule about the prefix.
export function journalCsvUrl() {
  return `${BASE}/journal.csv`
}
