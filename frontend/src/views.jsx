// The seven screens: Case file, Deadlines, Denials, Letters, Decisions,
// Journal, Autonomy.
//
// Three rules hold across every screen in this file.
//
//   1. Nothing here computes a date, a deadline, a denial class or a policy
//      outcome. Where a screen shows a class, a countdown or a sentence, that
//      value came off an API response unchanged. Joins by id (a line to its
//      denial, an assertion to its document) are lookups, not judgements.
//   2. "Now" always means `world.now`, read from the store. No file under this
//      one calls `new Date()` with no argument.
//   3. No control is decoration. Every button below either calls a route or
//      changes something on screen.

import { useMemo, useRef, useState } from 'react'
import { useStore } from './store.js'
import { journalCsvUrl } from './api.js'
import Modal from './components/Modal.jsx'
import Icon, { DenialAndClock } from './components/Icon.jsx'
import {
  fmtDate, fmtLongDate, fmtDateTime, money, sentenceCase,
  evidenceLabel, RISK_LABEL, STAGE_LABEL, CLASS_LABEL,
} from './format.js'

/* ── shared pieces ─────────────────────────────────────────────────────── */

function PageHead({ title, lede, actions }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {lede && <p className="lede">{lede}</p>}
      </div>
      {actions && <div className="page-head-actions">{actions}</div>}
    </div>
  )
}

function Empty({ title, children, action }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  )
}

function RiskChip({ risk }) {
  return <span className={`risk-chip risk-${risk}`}>{RISK_LABEL[risk] || sentenceCase(risk)}</span>
}

function ClassChip({ denialClass }) {
  const clinical = denialClass === 'clinical'
  return (
    <span className={`class-chip${clinical ? ' class-clinical' : ''}`}>
      {CLASS_LABEL[denialClass] || sentenceCase(denialClass)}
    </span>
  )
}

function Cite({ href, children }) {
  if (!href) return null
  return (
    <a className="cite" href={href} target="_blank" rel="noreferrer noopener">
      {children || 'the rule this comes from'} ↗
    </a>
  )
}

// The API sends some fields as free-shaped JSON: a timeline entry's `detail` is
// an object (often empty), and a paused call's `proposal` carries the whole
// drafted argument as a list of objects. Rendering either of those straight into
// JSX crashes React, and stringifying them shows a person a wall of braces. So
// they are walked: scalars as text, lists as lists, objects as key/value rows.
function Detail({ value }) {
  if (value === null || value === undefined || value === '') return <span className="muted">—</span>
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="muted">—</span>
    return (
      <ul className="detail-list">
        {value.map((item, i) => <li key={i}><Detail value={item} /></li>)}
      </ul>
    )
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value)
    if (entries.length === 0) return <span className="muted">—</span>
    return (
      <ul className="detail-pairs">
        {entries.map(([k, v]) => (
          <li key={k}>
            <span className="detail-key">{sentenceCase(k)}</span>
            <Detail value={v} />
          </li>
        ))}
      </ul>
    )
  }
  return <span className="detail-value">{String(value)}</span>
}

function TriageButton({ className = 'btn btn-brand' }) {
  const triage = useStore((s) => s.triage)
  const busy = useStore((s) => s.busy.triage)
  return (
    <button type="button" className={className} disabled={busy} onClick={() => triage()}>
      {busy ? 'Triaging…' : 'Triage the case file'}
    </button>
  )
}

/* ── Overview ──────────────────────────────────────────────────────────── */

// The landing. Six cards, one per screen, and every figure on them is counted
// off a response the API already returned — the console classifies nothing and
// computes no date to fill one in. Grouping the API's own risk values into "at
// risk" is a count, not a second opinion about which clock matters.
const AT_RISK = new Set(['approaching', 'critical', 'missed'])

function Tile({ icon, title, value, unit, tone, body, onClick }) {
  return (
    <button type="button" className="tile" onClick={onClick}>
      <span className="tile-icon"><Icon name={icon} size={24} /></span>
      <span className="tile-title">{title}</span>
      <span className={`tile-figure${tone ? ` tone-${tone}` : ''}`}>
        <span className="tile-value">{value}</span>
        <span className="tile-unit">{unit}</span>
      </span>
      <span className="tile-body">{body}</span>
      <span className="tile-arrow" aria-hidden="true"><Icon name="arrow" size={20} /></span>
    </button>
  )
}

function plural(n, one, many) {
  return n === 1 ? one : many
}

export function OverviewScreen() {
  const go = useStore((s) => s.go)
  const world = useStore((s) => s.world)
  const caseFile = useStore((s) => s.caseFile)
  const denials = useStore((s) => s.denials)
  const deadlines = useStore((s) => s.deadlines)
  const appeals = useStore((s) => s.appeals)
  const decisions = useStore((s) => s.decisions)
  const journal = useStore((s) => s.journal)

  const claims = caseFile.claims || []
  const documents = caseFile.documents || []
  const plans = world.plans || []

  const atRisk = deadlines.filter((f) => AT_RISK.has(f.risk))
  const missed = deadlines.filter((f) => f.risk === 'missed')
  const overdue = deadlines.filter((f) => f.insurer_overdue)
  // A missed window has no "days left", and an unassessable one has no figure
  // at all. Neither is folded into a nearest-deadline number.
  const running = deadlines.filter(
    (f) => f.risk !== 'missed' && typeof f.days_remaining === 'number',
  )
  const nearest = running.length
    ? running.reduce((a, b) => (b.days_remaining < a.days_remaining ? b : a))
    : null

  const alone = denials.filter((d) => d.can_prepare_alone)
  const clinical = denials.filter((d) => d.denial_class === 'clinical')

  const drafted = appeals.reduce((n, appeal) => {
    const levels = [...(appeal.history || []), ...(appeal.levels || [])]
    return n + levels.filter((l) => l.letter_body).length
  }, 0)

  const flagged = claims.reduce(
    (n, claim) => n + claim.lines.filter((l) => l.needs_review).length, 0,
  )

  return (
    <>
      {/* Where the reference portal puts a photograph. There is no photograph
          here and no drawing of a person: the subject of this product is a
          denial letter and a clock, and that is what is drawn. */}
      <section className="status-strip">
        <div className="strip-words">
          <h1 className="strip-title">The case, so far</h1>
          <p className="strip-line">
            The Okafor&ndash;Reyes household, <span className="mono">{caseFile.case_id || world.case_id || '—'}</span>
            {' — '}{claims.length} {plural(claims.length, 'claim', 'claims')} across{' '}
            {plans.length} {plural(plans.length, 'plan', 'plans')},{' '}
            {denials.length} denied {plural(denials.length, 'line', 'lines')}, and{' '}
            {nearest
              ? `the nearest appeal deadline is ${nearest.days_remaining} ${plural(nearest.days_remaining, 'day', 'days')} away.`
              : 'no appeal clock running yet.'}
          </p>
          <p className="strip-note">
            Counted from {fmtLongDate(world.now) || 'the world clock'}
            {overdue.length > 0 && `, and ${overdue.length} ${plural(overdue.length, 'plan is', 'plans are')} past ${plural(overdue.length, 'its', 'their')} own deadline to answer`}.
          </p>
          <div className="strip-actions">
            <TriageButton className="btn btn-brand btn-pill" />
          </div>
        </div>
        <DenialAndClock />
      </section>

      <div className="tile-grid">
        <Tile
          icon="deadlines"
          title="Deadlines"
          value={nearest ? nearest.days_remaining : '—'}
          unit={nearest
            ? `${plural(nearest.days_remaining, 'day', 'days')} to the nearest deadline`
            : 'no clock running'}
          tone={nearest ? nearest.risk : null}
          body={deadlines.length === 0
            ? 'No appeal is open yet.'
            : `${atRisk.length} of ${deadlines.length} open ${plural(deadlines.length, 'appeal', 'appeals')} ${plural(atRisk.length, 'is', 'are')} at risk${missed.length ? `, and ${missed.length} ${plural(missed.length, 'window has', 'windows have')} closed` : ''}.`}
          onClick={() => go('deadlines')}
        />

        <Tile
          icon="denials"
          title="Denials"
          value={denials.length}
          unit={`${plural(denials.length, 'denial', 'denials')} on file`}
          body={denials.length === 0
            ? 'Nothing has been classified yet.'
            : `Recourse can prepare ${alone.length} of them on its own${clinical.length ? `; ${clinical.length} ${plural(clinical.length, 'is', 'are')} your doctor’s to argue` : ''}.`}
          onClick={() => go('denials')}
        />

        <Tile
          icon="letters"
          title="Letters"
          value={drafted}
          unit={`${plural(drafted, 'letter', 'letters')} drafted`}
          body={drafted === 0
            ? 'Nothing drafted yet. Triage the case file and Recourse writes the appeals the evidence already supports.'
            : 'Every assertion in them is shown with the document it cites.'}
          onClick={() => go('letters')}
        />

        <Tile
          icon="decisions"
          title="Decisions"
          value={decisions.length}
          unit={`${plural(decisions.length, 'question', 'questions')} waiting for a person`}
          body={decisions.length === 0
            ? 'Nothing is waiting on you.'
            : 'Recourse stopped and asked. Nothing moves on those appeals until you answer.'}
          onClick={() => go('decisions')}
        />

        <Tile
          icon="case"
          title="Case file"
          value={claims.length}
          unit={`${plural(claims.length, 'claim', 'claims')} on file`}
          body={`${documents.length} ${plural(documents.length, 'document', 'documents')} behind them${flagged ? `, and ${flagged} ${plural(flagged, 'line needs', 'lines need')} a person to check ${plural(flagged, 'it', 'them')}` : ''}.`}
          onClick={() => go('case')}
        />

        <Tile
          icon="journal"
          title="Journal"
          value={journal.length}
          unit={`${plural(journal.length, 'entry', 'entries')} recorded`}
          body="Written as things happened, in the order they happened. Append-only."
          onClick={() => go('journal')}
        />
      </div>
    </>
  )
}

/* ── Case file ─────────────────────────────────────────────────────────── */

function PlanCard({ plan }) {
  const rules = plan.rules || {}
  return (
    <div className="plan-card">
      <div className="plan-card-head">
        <h3>{plan.name}</h3>
        <span className="tag">{rules.in_scope ? rules.label : 'Not in scope'}</span>
      </div>
      {!rules.in_scope ? (
        // A plan type with no clock table is reported as a refusal, with its
        // reason, rather than quietly defaulted to the figures for a plan type
        // it is not.
        <p className="refusal">{rules.refusal}</p>
      ) : (
        <dl className="kv">
          <div><dt>Member</dt><dd className="mono">{plan.member_id}</dd></div>
          <div><dt>Time to appeal</dt><dd>{rules.time_to_appeal}</dd></div>
          <div><dt>Internal levels</dt><dd>{rules.internal_levels}</dd></div>
          <div><dt>External review</dt><dd>{rules.external_review ? 'Available' : 'Not available'}</dd></div>
          <div><dt>Appeals address</dt><dd>{plan.appeals_address}</dd></div>
        </dl>
      )}
      <Cite href={rules.time_to_appeal_citation || rules.source}>where these figures come from</Cite>
    </div>
  )
}

function LineRow({ line, denial }) {
  const denied = line.is_denied
  return (
    <tr className={denied ? 'line-denied' : ''}>
      <td>
        <div className="line-desc">{line.description}</div>
        <div className="line-meta">
          {fmtDate(line.service_date)} · {line.provider}
        </div>
        {line.needs_review && (
          // Never hidden and never rolled into a count. A line the parser could
          // not read is the one thing on this screen a person has to look at.
          <div className="needs-review">⚑ Recourse could not read this line with confidence — check it against the paper EOB.</div>
        )}
      </td>
      <td className="num">{money(line.billed)}</td>
      <td className="num">{money(line.allowed)}</td>
      <td className="num">{money(line.plan_paid)}</td>
      <td className="num strong">{money(line.patient_responsibility)}</td>
      <td>
        {denied ? (
          <div className="line-codes">
            <span className="code-chip">CARC {line.carc.join(', ')}</span>
            {line.rarc.length > 0 && <span className="code-chip code-chip-quiet">RARC {line.rarc.join(', ')}</span>}
            {denial ? <ClassChip denialClass={denial.denial_class} /> : <span className="class-chip">Unclassified</span>}
            {line.is_partial_denial && <span className="tag tag-quiet">Part of the line only</span>}
          </div>
        ) : (
          <span className="line-ok">
            {line.carc.length > 0 ? `Cost share, CARC ${line.carc.join(', ')}` : 'Paid'}
          </span>
        )}
      </td>
    </tr>
  )
}

function EobPanel({ parsed, onOpen }) {
  if (!parsed) return null
  return (
    <div className={`eob-panel${parsed.needs_review ? ' eob-panel-flagged' : ''}`}>
      <div>
        <strong>
          {parsed.lines.length} service {parsed.lines.length === 1 ? 'line' : 'lines'} read,
          {' '}{parsed.denied.length} denied
          {parsed.flagged.length > 0 && `, ${parsed.flagged.length} flagged for a person to check`}
        </strong>
        {parsed.warnings.length > 0 && (
          <ul className="warn-list">
            {parsed.warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        )}
      </div>
      <button type="button" className="btn btn-ghost" onClick={onOpen}>See what was read</button>
    </div>
  )
}

function EobModal({ open, onClose }) {
  const uploadEob = useStore((s) => s.uploadEob)
  const busy = useStore((s) => s.busy.eob)
  const parsed = useStore((s) => s.eob)
  const [file, setFile] = useState(null)
  const input = useRef(null)

  return (
    <Modal
      open={open}
      onClose={onClose}
      wide
      title="Upload an Explanation of Benefits"
      subtitle="Recourse reads what it can and says plainly what it could not. It never fills a gap in with a guess."
      footer={
        <>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Close</button>
          <button
            type="button"
            className="btn btn-brand"
            disabled={!file || busy}
            onClick={async () => {
              await uploadEob(file)
              setFile(null)
              if (input.current) input.current.value = ''
            }}
          >
            {busy ? 'Reading…' : 'Read this EOB'}
          </button>
        </>
      }
    >
      <label className="file-field">
        <span>Choose a file</span>
        <input
          ref={input}
          type="file"
          accept=".pdf,.txt,.csv,application/pdf,text/plain"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
      </label>

      {parsed && (
        <div className="eob-result">
          <h4>What was read</h4>
          <dl className="kv kv-tight">
            <div><dt>Plan</dt><dd>{parsed.plan_name || '—'}</dd></div>
            <div><dt>Member</dt><dd className="mono">{parsed.member_id || '—'}</dd></div>
            <div><dt>Claim</dt><dd className="mono">{parsed.claim_id || '—'}</dd></div>
            <div><dt>Notice date</dt><dd>{fmtDate(parsed.notice_date) || '—'}</dd></div>
            <div><dt>Provider</dt><dd>{parsed.provider || '—'}</dd></div>
          </dl>

          {parsed.warnings.length > 0 && (
            <div className="callout callout-warn">
              <strong>What could not be read</strong>
              <ul>{parsed.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
            </div>
          )}

          {parsed.flagged.length > 0 && (
            <div className="callout callout-warn">
              <strong>⚑ Flagged for a person to check</strong>
              <ul>
                {parsed.flagged.map((line) => (
                  <li key={line.line_id}>{line.description || line.line_id} — {money(line.patient_responsibility)}</li>
                ))}
              </ul>
            </div>
          )}

          {parsed.denied.length > 0 ? (
            <table className="table">
              <thead>
                <tr><th>Line</th><th>Codes</th><th>Class</th><th>Reason</th></tr>
              </thead>
              <tbody>
                {parsed.denied.map((d) => (
                  <tr key={d.line_id}>
                    <td className="mono">{d.line_id}</td>
                    <td>
                      <span className="code-chip">CARC {d.carc.join(', ') || '—'}</span>
                      {d.rarc.length > 0 && <span className="code-chip code-chip-quiet">RARC {d.rarc.join(', ')}</span>}
                    </td>
                    <td><ClassChip denialClass={d.denial_class} /></td>
                    <td>{d.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted">No denied lines were found in this file.</p>
          )}
        </div>
      )}
    </Modal>
  )
}

export function CaseFileScreen() {
  const world = useStore((s) => s.world)
  const caseFile = useStore((s) => s.caseFile)
  const denials = useStore((s) => s.denials)
  const eob = useStore((s) => s.eob)
  const [eobOpen, setEobOpen] = useState(false)

  const denialByLine = useMemo(() => {
    const map = {}
    for (const d of denials) map[d.line_id] = d
    return map
  }, [denials])

  const claims = caseFile.claims || []
  const flaggedCount = claims.reduce(
    (n, claim) => n + claim.lines.filter((l) => l.needs_review).length, 0,
  )

  return (
    <>
      <PageHead
        title="Case file"
        lede={`The Okafor–Reyes household, ${caseFile.case_id || ''} — one hospital episode and the outpatient care after it, across two plans.`}
        actions={
          <>
            <button type="button" className="btn btn-ghost" onClick={() => setEobOpen(true)}>
              Upload an EOB
            </button>
            <TriageButton />
          </>
        }
      />

      {flaggedCount > 0 && (
        <div className="callout callout-warn callout-wide">
          <strong>⚑ {flaggedCount} {flaggedCount === 1 ? 'line needs' : 'lines need'} a person to check {flaggedCount === 1 ? 'it' : 'them'}.</strong>
          <span>They are marked in the claims below. Nothing has been decided about them.</span>
        </div>
      )}

      <EobPanel parsed={eob} onOpen={() => setEobOpen(true)} />

      <section className="panel">
        <h2 className="panel-title">The plans</h2>
        <div className="plan-grid">
          {(world.plans || []).map((plan) => <PlanCard key={plan.plan_id} plan={plan} />)}
        </div>
      </section>

      <section className="panel">
        <h2 className="panel-title">The claims</h2>
        {claims.length === 0 ? (
          <Empty title="No claims on file." />
        ) : (
          claims.map((claim) => (
            <div className="claim-card" key={claim.claim_id}>
              <header className="claim-head">
                <div>
                  <h3>{claim.provider}</h3>
                  <p className="claim-meta">
                    <span className="mono">{claim.claim_id}</span> · notice dated {fmtLongDate(claim.notice_date)}
                    {' '}· {sentenceCase(claim.service_type)}
                  </p>
                </div>
                <div className="claim-denied">
                  <span className="claim-denied-label">Denied on this claim</span>
                  <span className="claim-denied-amount">{money(claim.denied_total)}</span>
                </div>
              </header>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Service</th><th className="num">Billed</th><th className="num">Allowed</th>
                      <th className="num">Plan paid</th><th className="num">Yours</th><th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {claim.lines.map((line) => (
                      <LineRow key={line.line_id} line={line} denial={denialByLine[line.line_id]} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))
        )}
      </section>

      <section className="panel">
        <h2 className="panel-title">Documents in the file</h2>
        <ul className="doc-list">
          {(caseFile.documents || []).map((doc) => (
            <li key={doc.document_id}>
              <span className="doc-kind">{sentenceCase(doc.kind)}</span>
              <span className="doc-title">{doc.title}</span>
              <span className="doc-date">received {fmtDate(doc.received_on)}</span>
            </li>
          ))}
        </ul>
      </section>

      <EobModal open={eobOpen} onClose={() => setEobOpen(false)} />
    </>
  )
}

/* ── Deadlines ─────────────────────────────────────────────────────────── */

function DeadlineCard({ finding }) {
  const d = finding.deadlines || {}
  const missed = finding.risk === 'missed'
  return (
    <article className={`deadline-card risk-band-${finding.risk}${missed ? ' deadline-missed' : ''}`}>
      <div className="deadline-count">
        {missed ? (
          <>
            <span className="count-terminal">Closed</span>
            <span className="count-label">nothing recovers this</span>
          </>
        ) : (
          <>
            <span className="count-number">{finding.days_remaining ?? '—'}</span>
            <span className="count-label">{finding.days_remaining === 1 ? 'day left' : 'days left'}</span>
          </>
        )}
      </div>

      <div className="deadline-main">
        <header className="deadline-head">
          <h3>{finding.provider || finding.appeal_id}</h3>
          <RiskChip risk={finding.risk} />
          {finding.insurer_overdue && <span className="against-chip">The plan is late</span>}
        </header>

        {/* The API composes this sentence so that it reads identically in a
            notification, an escalation and here. The console never writes its own. */}
        <p className="deadline-sentence">{finding.sentence}</p>

        <div className="clock-pair">
          <div className="clock-col">
            <span className="clock-whose">Your clock</span>
            <span className="clock-date">{fmtLongDate(d.mine) || 'not assessable'}</span>
            <span className="clock-note">{STAGE_LABEL[d.stage] || sentenceCase(d.stage)}</span>
          </div>
          <div className={`clock-col clock-theirs${finding.insurer_overdue ? ' clock-col-late' : ''}`}>
            <span className="clock-whose">The plan&rsquo;s clock</span>
            <span className="clock-date">{fmtLongDate(d.theirs) || 'not yet running'}</span>
            <span className="clock-note">
              {d.theirs
                ? (finding.insurer_overdue ? 'passed without an answer' : 'to answer this appeal')
                : 'starts when the appeal is sent'}
            </span>
          </div>
        </div>

        <footer className="deadline-foot">
          <span className="mono">{finding.appeal_id}</span>
          <span>{d.basis}</span>
          {d.next_stage && (
            <span>
              next: {STAGE_LABEL[d.next_stage] || sentenceCase(d.next_stage)}
              {d.next_stage_window_days ? `, within ${d.next_stage_window_days} days` : ''}
            </span>
          )}
          <Cite href={d.citation} />
        </footer>
      </div>
    </article>
  )
}

export function DeadlinesScreen() {
  const deadlines = useStore((s) => s.deadlines)
  const world = useStore((s) => s.world)
  const autonomy = useStore((s) => s.autonomy)
  const press = useStore((s) => s.press)
  const busy = useStore((s) => s.busy.press)

  // Order comes from the API — the same sweep the PRESS loop runs. A second
  // ordering here would be a second opinion about which clock matters most.
  const overdue = deadlines.filter((f) => f.insurer_overdue)

  return (
    <>
      <PageHead
        title="Deadlines"
        lede={`Every open appeal, worst first, counted from ${fmtLongDate(world.now)}. Warning at ${autonomy?.thresholds?.warn_days ?? '—'} days, which is what the autonomy dial moves.`}
        actions={
          <button type="button" className="btn btn-brand" disabled={busy} onClick={() => press()}>
            {busy ? 'Sweeping…' : 'Sweep the clocks'}
          </button>
        }
      />

      {overdue.length > 0 && (
        <section className="against-panel">
          <header>
            <h2>The plan is past its own deadline</h2>
            <p>
              This is the one clock in the process running against the insurer rather than
              against you. A plan that misses it has failed to give you the review it owes,
              and on an ERISA plan that is a door to the next stage without waiting.
            </p>
          </header>
          <ul>
            {overdue.map((f) => (
              <li key={f.appeal_id}>
                <span className="against-provider">{f.provider || f.appeal_id}</span>
                <span className="against-date">
                  owed an answer by {fmtLongDate(f.deadlines?.theirs)}
                </span>
                <span className="against-sentence">{f.sentence}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {deadlines.length === 0 ? (
        <Empty title="No open appeals.">
          Nothing is running. Triage the case file and Recourse will open what it can.
        </Empty>
      ) : (
        <div className="deadline-list">
          {deadlines.map((f) => <DeadlineCard key={f.appeal_id} finding={f} />)}
        </div>
      )}
    </>
  )
}

/* ── Denials ───────────────────────────────────────────────────────────── */

function DenialCard({ denial }) {
  const line = denial.line
  const clinical = denial.denial_class === 'clinical'
  return (
    <article className={`denial-card${clinical ? ' denial-clinical' : ''}`}>
      <header className="denial-head">
        <div>
          <h3>{line?.description || denial.denial_id}</h3>
          <p className="denial-meta">
            {line?.provider} · {fmtDate(line?.service_date)} · <span className="mono">{denial.denial_id}</span>
          </p>
        </div>
        <div className="denial-amount">
          <span className="denial-amount-label">At stake</span>
          <span className="denial-amount-value">{money(line?.patient_responsibility)}</span>
        </div>
      </header>

      <div className="denial-codes">
        <ClassChip denialClass={denial.denial_class} />
        <span className="code-chip">CARC {denial.matched_code || '—'}</span>
        {denial.narrowed_by && <span className="code-chip code-chip-quiet">narrowed by {denial.narrowed_by}</span>}
        <Cite href={denial.citation}>the code table</Cite>
      </div>

      <p className="denial-reason">{denial.reason_text}</p>

      {denial.unknown_codes.length > 0 && (
        <div className="callout callout-warn">
          <strong>Codes nobody here recognises: {denial.unknown_codes.join(', ')}</strong>
          <span>Recourse will not guess at a reason the insurer declined to give.</span>
        </div>
      )}

      <div className="evidence">
        <h4>What an appeal on this needs</h4>
        <ul className="evidence-list">
          {denial.requirements.map((req) => {
            const missing = denial.gaps.some((g) => g.kind === req.kind)
            return (
              <li key={req.kind} className={missing ? 'evidence-missing' : 'evidence-held'}>
                <span className="evidence-mark" aria-hidden="true">{missing ? '○' : '✓'}</span>
                <span className="evidence-body">
                  <span className="evidence-kind">
                    {evidenceLabel(req.kind)}
                    {!req.required && <span className="tag tag-quiet">optional</span>}
                    {missing && <span className="tag tag-missing">not in the file</span>}
                  </span>
                  <span className="evidence-why">{req.why}</span>
                </span>
              </li>
            )
          })}
        </ul>
      </div>

      {denial.can_prepare_alone ? (
        <div className="verdict verdict-alone">
          <strong>Recourse can prepare this one on its own.</strong>
          <span>Everything the argument rests on is already in the file. A person still sends it.</span>
        </div>
      ) : clinical ? (
        // The gap here is authorship, not paperwork. Even with every document
        // in the file this stays handed back: it is the treating clinician's
        // argument and nobody else's.
        <div className="verdict verdict-handback">
          <strong>Handed back to you. This is your doctor&rsquo;s to argue.</strong>
          <span>
            A medical-necessity appeal is a clinical judgement made in the patient&rsquo;s name.
            Recourse will not write one, at any autonomy level. What it will do is tell you
            exactly what to ask your clinician for, and keep counting the days while you do.
          </span>
        </div>
      ) : (
        <div className="verdict verdict-blocked">
          <strong>Recourse cannot prepare this yet.</strong>
          <span>
            {denial.gaps.map((g) => evidenceLabel(g.kind)).join(', ')} {denial.gaps.length === 1 ? 'is' : 'are'} not in the file,
            and that is what the appeal argues against.
          </span>
        </div>
      )}
    </article>
  )
}

export function DenialsScreen() {
  const denials = useStore((s) => s.denials)
  return (
    <>
      <PageHead
        title="Denials"
        lede="Each one classified from its own X12 code, not from a guess about the wording. The class decides who can argue it."
        actions={<TriageButton />}
      />
      {denials.length === 0 ? (
        <Empty title="No denials on file." action={<TriageButton />} />
      ) : (
        <div className="denial-list">
          {denials.map((d) => <DenialCard key={d.denial_id} denial={d} />)}
        </div>
      )}
    </>
  )
}

/* ── Letters ───────────────────────────────────────────────────────────── */

function Assertion({ assertion, documents }) {
  const doc = assertion.document_id ? documents[assertion.document_id] : null
  const uncited = assertion.clinical && !assertion.document_id
  return (
    <li className={`assertion${uncited ? ' assertion-uncited' : ''}`}>
      <p className="assertion-text">{assertion.text}</p>
      <p className="assertion-cite">
        {assertion.clinical && <span className="tag tag-clinical">clinical</span>}
        {doc ? (
          <>
            <span className="assertion-cite-label">cites</span>
            <span className="assertion-doc">{doc.title}</span>
            <span className="mono assertion-doc-id">{doc.document_id}</span>
            <span className="assertion-doc-date">received {fmtDate(doc.received_on)}</span>
          </>
        ) : assertion.document_id ? (
          <>
            <span className="assertion-cite-label">cites</span>
            <span className="mono assertion-doc-id">{assertion.document_id}</span>
          </>
        ) : uncited ? (
          <span className="assertion-none">
            ⚠ Nothing in the file supports this. It must not go into a letter.
          </span>
        ) : (
          <span className="assertion-cite-label">no document needed — this is not a clinical claim</span>
        )}
      </p>
    </li>
  )
}

function LetterCard({ appeal, level, historic, denial, documents }) {
  return (
    <article className={`letter-card${historic ? ' letter-historic' : ''}`}>
      <header className="letter-head">
        <div>
          <h3>{denial?.line?.provider || appeal.appeal_id}</h3>
          <p className="letter-meta">
            {STAGE_LABEL[level.stage] || sentenceCase(level.stage)} · <span className="mono">{appeal.appeal_id}</span>
            {level.sent_on ? ` · sent ${fmtDate(level.sent_on)}` : ' · not sent'}
            {level.answered_on && ` · answered ${fmtDate(level.answered_on)}`}
          </p>
        </div>
        <span className={`tag tag-outcome-${level.outcome}`}>{sentenceCase(level.outcome)}</span>
      </header>

      <div className="letter-body">{level.letter_body}</div>

      <div className="letter-assertions">
        {/* Every assertion, not only the clinical ones: the point of the list is
            that a reader can see which sentences needed a document and whether
            they got one. Showing only the cited ones would hide the failure. */}
        <h4>What this letter asserts, and what each sentence rests on</h4>
        {level.assertions.length === 0 ? (
          <p className="muted">This draft makes no assertions that need a document behind them.</p>
        ) : (
          <ul className="assertion-list">
            {level.assertions.map((a, i) => (
              <Assertion key={i} assertion={a} documents={documents} />
            ))}
          </ul>
        )}
      </div>
    </article>
  )
}

export function LettersScreen() {
  const appeals = useStore((s) => s.appeals)
  const denials = useStore((s) => s.denials)
  const caseFile = useStore((s) => s.caseFile)

  const documents = useMemo(() => {
    const map = {}
    for (const doc of caseFile.documents || []) map[doc.document_id] = doc
    return map
  }, [caseFile.documents])

  const denialById = useMemo(() => {
    const map = {}
    for (const d of denials) map[d.denial_id] = d
    return map
  }, [denials])

  const drafted = []
  for (const appeal of appeals) {
    for (const level of appeal.history || []) {
      if (level.letter_body) drafted.push({ appeal, level, historic: true })
    }
    for (const level of appeal.levels || []) {
      if (level.letter_body) drafted.push({ appeal, level, historic: false })
    }
  }

  return (
    <>
      <PageHead
        title="Letters"
        lede="What Recourse has drafted, and — sentence by sentence — the document each clinical claim rests on. A letter is only worth what it can point at."
        actions={<TriageButton />}
      />
      {drafted.length === 0 ? (
        <Empty title="Nothing has been drafted yet.">
          Triage the case file and Recourse will write the appeals the evidence already supports.
          It will not write the clinical one — see the Denials screen for why.
        </Empty>
      ) : (
        <div className="letter-list">
          {drafted.map(({ appeal, level, historic }, i) => (
            <LetterCard
              key={`${appeal.appeal_id}-${level.stage}-${i}`}
              appeal={appeal}
              level={level}
              historic={historic}
              denial={denialById[appeal.denial_id]}
              documents={documents}
            />
          ))}
        </div>
      )}
    </>
  )
}

/* ── Decisions ─────────────────────────────────────────────────────────── */

const ROLES = ['self', 'daughter', 'son', 'spouse', 'care manager', 'advocate']

function DecisionCard({ decision }) {
  const answer = useStore((s) => s.answerDecision)
  const busy = useStore((s) => s.busy[`decision:${decision.decision_id}`])
  const [by, setBy] = useState('Ana Okafor')
  const [role, setRole] = useState('self')
  const [note, setNote] = useState('')
  const subject = decision.subject || {}

  return (
    <article className={`decision-card sev-${Math.min(decision.severity || 0, 3)}`}>
      <header className="decision-head">
        <span className="rule-chip">{sentenceCase(decision.rule)}</span>
        {decision.severity > 1 && (
          <span className="sev-chip">asked {decision.severity} times, and getting louder</span>
        )}
      </header>

      <p className="decision-prompt">{decision.prompt}</p>

      {/* Which claim this is about. A question rendered without its subject asks
          somebody to approve a sentence with no answer to "about which claim". */}
      <div className="decision-subject">
        <span className="subject-provider">{subject.provider || 'Subject not recorded'}</span>
        {subject.description && <span className="subject-desc">{subject.description}</span>}
        <span className="subject-tags">
          {subject.denial_class && <ClassChip denialClass={subject.denial_class} />}
          {subject.matched_code && <span className="code-chip">CARC {subject.matched_code}</span>}
          {subject.amount && <span className="subject-amount">{money(subject.amount)}</span>}
          {subject.appeal_id && <span className="mono">{subject.appeal_id}</span>}
        </span>
      </div>

      {decision.rule_hits?.length > 0 && (
        <ul className="hit-list">
          {decision.rule_hits.map((hit, i) => (
            <li key={i}>
              <span className="hit-rule">{sentenceCase(hit.rule)}</span>
              <span className="hit-detail">{hit.detail}</span>
            </li>
          ))}
        </ul>
      )}

      {decision.proposal && (
        <details className="proposal">
          <summary>What Recourse was about to do</summary>
          <dl className="kv kv-tight">
            {Object.entries(decision.proposal).map(([k, v]) => (
              <div key={k}>
                <dt>{sentenceCase(k)}</dt>
                <dd><Detail value={v} /></dd>
              </div>
            ))}
          </dl>
        </details>
      )}

      <div className="decision-who">
        <label className="field">
          <span>Who is deciding</span>
          <input value={by} onChange={(e) => setBy(e.target.value)} placeholder="Your name" />
        </label>
        <label className="field">
          <span>Their relationship to the patient</span>
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        <label className="field field-grow">
          <span>Note for the record (optional)</span>
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Why you decided this" />
        </label>
      </div>

      <div className="decision-actions">
        <p className="decline-note">
          <strong>Declining does not do a smaller version of this.</strong> Nothing happens: the
          appeal stays exactly as it is, its deadline keeps running, and the record says you refused.
        </p>
        <div className="decision-buttons">
          <button
            type="button"
            className="btn btn-quiet"
            disabled={busy || !by.trim()}
            onClick={() => answer(decision.decision_id, 'decline', { by, role, note })}
          >
            Decline
          </button>
          <button
            type="button"
            className="btn btn-brand"
            disabled={busy || !by.trim()}
            onClick={() => answer(decision.decision_id, 'approve', { by, role, note })}
          >
            {busy ? 'Recording…' : 'Approve'}
          </button>
        </div>
      </div>
    </article>
  )
}

export function DecisionsScreen() {
  const decisions = useStore((s) => s.decisions)
  return (
    <>
      <PageHead
        title="Decisions"
        lede="Where Recourse stopped and asked. Each one names the claim it is about and the rule that stopped it."
      />
      {decisions.length === 0 ? (
        <Empty title="Nothing is waiting on you.">
          Recourse escalates when a rule stops it, and when a deadline is close enough that
          silence would be the failure. Neither is true right now.
        </Empty>
      ) : (
        <div className="decision-list">
          {decisions.map((d) => <DecisionCard key={d.decision_id} decision={d} />)}
        </div>
      )}
    </>
  )
}

/* ── Journal ───────────────────────────────────────────────────────────── */

export function JournalScreen() {
  const journal = useStore((s) => s.journal)
  const timeline = useStore((s) => s.timeline)

  return (
    <>
      <PageHead
        title="Journal"
        lede="Written as things happened, in the order they happened. Append-only: nothing over the network can edit or remove a line of it."
        actions={
          <a className="btn btn-ghost" href={journalCsvUrl()} download="journal.csv">
            Download the CSV
          </a>
        }
      />

      <section className="panel">
        <h2 className="panel-title">What happened</h2>
        {journal.length === 0 ? (
          <Empty title="Nothing has been written yet." />
        ) : (
          <ol className="journal">
            {journal.map((entry, i) => (
              <li key={i}>
                <span className="journal-at">{fmtDateTime(entry.at)}</span>
                <span className="journal-body">
                  <span className="journal-sentence">{entry.sentence}</span>
                  <span className="journal-meta">
                    <span className="journal-kind">{sentenceCase(entry.kind)}</span>
                    {entry.appeal_id && <span className="mono">{entry.appeal_id}</span>}
                    {entry.document_id && <span className="mono">{entry.document_id}</span>}
                    <span className={entry.decided_by ? 'journal-by' : 'journal-unattended'}>
                      {entry.decided_by ? `decided by ${entry.decided_by}` : 'Recourse, unattended'}
                    </span>
                  </span>
                </span>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="panel">
        <h2 className="panel-title">The agent&rsquo;s own trail</h2>
        <p className="panel-lede">
          Every model call and tool call, recorded by the loop rather than by the agent
          describing itself.
        </p>
        {timeline.length === 0 ? (
          <Empty title="No runs yet.">
            Triage the case file or sweep the clocks and each call will appear here.
          </Empty>
        ) : (
          <table className="table">
            <thead><tr><th>At</th><th>Kind</th><th>What</th><th>Detail</th></tr></thead>
            <tbody>
              {timeline.map((e, i) => (
                <tr key={i}>
                  <td className="mono">{fmtDateTime(e.at)}</td>
                  <td><span className="tag tag-quiet">{sentenceCase(e.kind)}</span></td>
                  <td>{e.label}</td>
                  <td className="trail-detail"><Detail value={e.detail} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  )
}

/* ── Autonomy ──────────────────────────────────────────────────────────── */

const LEVEL_COPY = {
  conservative: {
    title: 'Conservative',
    body: 'Recourse reads, classifies and counts, and asks before it writes anything.',
  },
  balanced: {
    title: 'Balanced',
    body: 'Recourse drafts the appeals the file already supports, without being asked. It still never sends one.',
  },
  trusted: {
    title: 'Trusted',
    body: 'Recourse may also ask a provider or the plan for records in your name.',
  },
}

// The API sends the three rule names; the prose and the statute behind each one
// are console copy. They are the product's actual promise, so they are written
// here rather than derived from anything — and the citation is the same source
// the engine itself cites for that rule.
const RULE_COPY = {
  uncited_clinical_assertion: {
    title: 'It will not assert anything clinical the file cannot support.',
    body: 'A symptom, a diagnosis or a course of treatment that no document in the file supports does not go into a letter. That is not a weak appeal — it is a false statement on an insurance document, made in the patient’s name.',
    statute: '18 U.S.C. § 1035 — false statements relating to health care matters',
    href: 'https://www.law.cornell.edu/uscode/text/18/1035',
  },
  filing_is_not_the_agents: {
    title: 'It will not file. Ever, at any level.',
    body: 'No tool in this system submits an appeal, and this rule exists to refuse anything that tries. Submitting is a legal act taken in someone else’s name. Recourse prepares; a person sends.',
    statute: '29 CFR 2560.503-1(c) — the claimant’s own request for review',
    href: 'https://www.govinfo.gov/content/pkg/CFR-2023-title29-vol9/xml/CFR-2023-title29-vol9-sec2560-503-1.xml',
  },
  deadline_at_risk: {
    title: 'It will not let a deadline pass in silence.',
    body: 'This one is a duty rather than a prohibition: it fires because the agent must act, not because it must not. An unanswered deadline escalation gets louder rather than going quiet. Fewer than one denied claim in a hundred is ever appealed, and the reason is not that people accept the decision — it is that nobody told them the clock was running.',
    statute: '29 CFR 2560.503-1(h)(3)(i) — at least 180 days to request a review',
    href: 'https://www.govinfo.gov/content/pkg/CFR-2023-title29-vol9/xml/CFR-2023-title29-vol9-sec2560-503-1.xml',
  },
}

export function AutonomyScreen() {
  const autonomy = useStore((s) => s.autonomy)
  const setAutonomy = useStore((s) => s.setAutonomy)
  const busy = useStore((s) => s.busy.autonomy)
  const t = autonomy?.thresholds || {}

  return (
    <>
      <PageHead
        title="Autonomy"
        lede="What the dial moves, and — beneath it — the three rules no setting reaches."
      />

      <section className="panel">
        <h2 className="panel-title">The dial</h2>
        <div className="level-grid">
          {(autonomy?.levels || []).map((level) => {
            const copy = LEVEL_COPY[level] || { title: sentenceCase(level), body: '' }
            const active = autonomy.level === level
            return (
              <button
                key={level}
                type="button"
                className={`level-card${active ? ' level-active' : ''}`}
                disabled={busy || active}
                aria-pressed={active}
                onClick={() => setAutonomy(level)}
              >
                <span className="level-title">{copy.title}</span>
                <span className="level-body">{copy.body}</span>
                <span className="level-state">{active ? 'Current setting' : 'Switch to this'}</span>
              </button>
            )
          })}
        </div>

        <dl className="kv kv-row">
          <div>
            <dt>Warns at</dt>
            <dd>{t.warn_days} days before your own deadline</dd>
          </div>
          <div>
            <dt>Drafts unprompted</dt>
            <dd>{t.may_draft_unprompted ? 'Yes' : 'No — it asks first'}</dd>
          </div>
          <div>
            <dt>Requests records in your name</dt>
            <dd>{t.may_request_records ? 'Yes' : 'No — it asks first'}</dd>
          </div>
        </dl>
        <p className="panel-note">
          Even Conservative warns early. The dial governs what Recourse <em>does</em>, and warning
          you is not doing anything to anybody — a setting that went quieter about a closing
          deadline would be a setting that made this useless.
        </p>
      </section>

      <section className="panel panel-rules">
        <h2 className="panel-title">Beneath the dial</h2>
        <p className="panel-lede">
          These three fire at every level. There is no setting that loosens any of them, and
          there is no screen in this console that can.
        </p>
        <ol className="rule-list">
          {(autonomy?.non_negotiable_rules || []).map((rule) => {
            const copy = RULE_COPY[rule]
            if (!copy) {
              // A rule the engine enforces that this screen has no words for is
              // shown as itself rather than dropped. A promise the console has
              // silently stopped displaying is a promise nobody is checking.
              return (
                <li key={rule} className="rule-item">
                  <h3 className="mono">{rule}</h3>
                  <p>Enforced at every autonomy level.</p>
                </li>
              )
            }
            return (
              <li key={rule} className="rule-item">
                <h3>{copy.title}</h3>
                <p>{copy.body}</p>
                <p className="rule-statute">
                  <Cite href={copy.href}>{copy.statute}</Cite>
                </p>
                <span className="mono rule-id">{rule}</span>
              </li>
            )
          })}
        </ol>
      </section>
    </>
  )
}
