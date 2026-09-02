// The console's shell: a dark top nav, the seven screens, and the operator menu.
//
// The shell owns three things and nothing else: which screen is showing, the
// loading and error states, and the toast. Every screen is in views.jsx and
// every fetch is in store.js.
//
// The clock in the header is `world.now`, read from the API. This file — and
// every file under it — never calls `new Date()` with no argument. The demo
// world is frozen at 2026-09-02; a browser clock would land outside it and
// produce a screen that is correct and empty, which looks exactly like a screen
// that is broken.

import { useEffect, useRef, useState } from 'react'
import * as V from './views.jsx'
import { useStore } from './store.js'
import { fmtDate } from './format.js'

const NAV_ITEMS = [
  { route: 'case', label: 'Case file' },
  { route: 'deadlines', label: 'Deadlines' },
  { route: 'denials', label: 'Denials' },
  { route: 'letters', label: 'Letters' },
  { route: 'decisions', label: 'Decisions', badge: true },
  { route: 'journal', label: 'Journal' },
  { route: 'autonomy', label: 'Autonomy' },
]

const SCREENS = {
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

  const Screen = SCREENS[route] || V.DeadlinesScreen
  const overdue = deadlines.filter((d) => d.insurer_overdue).length
  const working = Boolean(busy.triage || busy.press)

  return (
    <div className="app-shell">
      <header className="top-nav">
        <div className="top-nav-brand">
          <span className="brand-mark" aria-hidden="true">R</span>
          <span className="brand-name">Recourse</span>
        </div>

        <nav className="top-nav-items" aria-label="Screens">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.route}
              type="button"
              className={`top-nav-item${route === item.route ? ' active' : ''}`}
              aria-current={route === item.route ? 'page' : undefined}
              onClick={() => go(item.route)}
            >
              {item.label}
              {item.badge && decisions.length > 0 && (
                <span className="top-nav-badge">{decisions.length}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="top-nav-right">
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
        {error && <div className="error-strip">{error}</div>}
        <div className="screen-body">{loading ? <Skeleton /> : <Screen />}</div>
      </main>

      {toast && <div className={`toast toast-${toast.tone}`} role="status">{toast.message}</div>}
    </div>
  )
}
