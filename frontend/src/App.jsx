// The console's shell: a fixed white sidebar, an orange top bar, the eight
// screens, and the operator menu.
//
// The shell owns three things and nothing else: which screen is showing, the
// loading and error states, and the toast. Every screen is in views.jsx and
// every fetch is in store.js.
//
// The clock in the top bar is `world.now`, read from the API. This file — and
// every file under it — never calls `new Date()` with no argument. The demo
// world is frozen at 2026-09-02; a browser clock would land outside it and
// produce a screen that is correct and empty, which looks exactly like a screen
// that is broken.

import { useEffect, useRef, useState } from 'react'
import * as V from './views.jsx'
import Icon from './components/Icon.jsx'
import { useStore } from './store.js'
import { fmtDate } from './format.js'

const NAV_ITEMS = [
  { route: 'overview', label: 'Overview', icon: 'overview' },
  { route: 'case', label: 'Case file', icon: 'case' },
  { route: 'deadlines', label: 'Deadlines', icon: 'deadlines' },
  { route: 'denials', label: 'Denials', icon: 'denials' },
  { route: 'letters', label: 'Letters', icon: 'letters' },
  { route: 'decisions', label: 'Decisions', icon: 'decisions', badge: true },
  { route: 'journal', label: 'Journal', icon: 'journal' },
  { route: 'autonomy', label: 'Autonomy', icon: 'autonomy' },
]

const SCREENS = {
  overview: V.OverviewScreen,
  case: V.CaseFileScreen,
  deadlines: V.DeadlinesScreen,
  denials: V.DenialsScreen,
  letters: V.LettersScreen,
  decisions: V.DecisionsScreen,
  journal: V.JournalScreen,
  autonomy: V.AutonomyScreen,
}

function OperatorMenu({ onReset, resetting }) {
  const [open, setOpen] = useState(false)
  const wrap = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    const onDown = (e) => {
      if (wrap.current && !wrap.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('mousedown', onDown)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('mousedown', onDown)
    }
  }, [open])

  return (
    <div className="operator-menu" ref={wrap}>
      <button
        type="button"
        className="operator-chip"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <span className="operator-avatar">AO</span>
        <span className="operator-name">Ana Okafor</span>
        <span className="caret" aria-hidden="true">▾</span>
      </button>
      {open && (
        <div className="operator-dropdown" role="menu">
          <div className="operator-dropdown-note">
            Signed in as the member. Everything Recourse prepares is sent by a person.
          </div>
          <button
            type="button"
            role="menuitem"
            disabled={resetting}
            onClick={() => {
              setOpen(false)
              onReset()
            }}
          >
            {resetting ? 'Resetting…' : 'Reset the demo world'}
          </button>
        </div>
      )}
    </div>
  )
}

function Skeleton() {
  return (
    <div className="skeleton" aria-hidden="true">
      <div className="skeleton-line" style={{ width: '32%' }} />
      <div className="skeleton-line" style={{ width: '88%' }} />
      <div className="skeleton-line" style={{ width: '80%' }} />
      <div className="skeleton-line" style={{ width: '66%' }} />
    </div>
  )
}

function Sidebar({ route, go, decisionCount }) {
  return (
    <aside className="sidebar">
      <div className="side-brand">
        <span className="brand-mark" aria-hidden="true">R</span>
        <span className="brand-words">
          <span className="brand-name">Recourse</span>
          <span className="brand-sub">Health-claim appeals</span>
        </span>
      </div>

      <nav className="side-nav" aria-label="Screens">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.route}
            type="button"
            className={`side-nav-item${route === item.route ? ' active' : ''}`}
            aria-current={route === item.route ? 'page' : undefined}
            onClick={() => go(item.route)}
          >
            <Icon name={item.icon} size={20} />
            <span className="side-nav-label">{item.label}</span>
            {item.badge && decisionCount > 0 && (
              <span className="side-nav-badge">{decisionCount}</span>
            )}
          </button>
        ))}
      </nav>

      <p className="side-foot">
        Recourse prepares. A person sends. Nothing here is filed on your behalf.
      </p>
    </aside>
  )
}

export default function App() {
  const route = useStore((s) => s.route)
  const go = useStore((s) => s.go)
  const loading = useStore((s) => s.loading)
  const error = useStore((s) => s.error)
  const toast = useStore((s) => s.toast)
  const world = useStore((s) => s.world)
  const decisions = useStore((s) => s.decisions) || []
  const deadlines = useStore((s) => s.deadlines) || []
  const autonomy = useStore((s) => s.autonomy)
  const busy = useStore((s) => s.busy) || {}
  const refresh = useStore((s) => s.refresh)
  const resetDemo = useStore((s) => s.resetDemo)

  useEffect(() => {
    refresh()
  }, [refresh])

  const Screen = SCREENS[route] || V.OverviewScreen
  const overdue = deadlines.filter((d) => d.insurer_overdue).length
  const working = Boolean(busy.triage || busy.press)

  return (
    <div className="app-shell">
      <Sidebar route={route} go={go} decisionCount={decisions.length} />

      <div className="app-column">
        {/* The bar names the case rather than the screen: the screen already
            has an <h1> under it, and a second copy of the same word is not a
            heading, it is furniture. */}
        <header className="topbar">
          <span className="topbar-case">
            <span className="topbar-case-label">Case</span>
            <span className="topbar-case-id">{world?.case_id || '—'}</span>
          </span>
          <div className="topbar-right">
            <span className="clock" title="The demo world runs on a frozen clock">
              <span className="clock-label">Today</span>
              {fmtDate(world?.now) || '—'}
            </span>
            <button
              type="button"
              className="autonomy-pill"
              onClick={() => go('autonomy')}
              title="Autonomy level"
            >
              {autonomy?.level || '—'}
            </button>
            <OperatorMenu onReset={() => resetDemo()} resetting={Boolean(busy.reset)} />
          </div>
        </header>

        {/* A WATCH or PRESS run is a real model round-trip and takes tens of
            seconds. A disabled button is not enough feedback for that long, and
            the alternative — a console that looks frozen — is what people reload. */}
        {working && (
          <div className="working-rail" role="status">
            <span className="working-bar" aria-hidden="true" />
            <span>
              {busy.triage
                ? 'Recourse is reading the case file, classifying each denial and checking the evidence behind it.'
                : 'Recourse is sweeping every open appeal against its clocks.'}
            </span>
          </div>
        )}

        {overdue > 0 && route !== 'deadlines' && (
          <button type="button" className="overdue-rail" onClick={() => go('deadlines')}>
            <strong>
              {overdue === 1
                ? 'One plan is past its own deadline to answer.'
                : `${overdue} plans are past their own deadlines to answer.`}
            </strong>
            <span>See the deadlines →</span>
          </button>
        )}

        <main className="app-main">
          <div className="screen-body">
            {error && <div className="error-strip">{error}</div>}
            {loading ? <Skeleton /> : <Screen />}
          </div>
        </main>
      </div>

      {toast && <div className={`toast toast-${toast.tone}`} role="status">{toast.message}</div>}
    </div>
  )
}
