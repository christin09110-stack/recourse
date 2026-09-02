// Formatting only. Nothing in this file decides, computes or compares anything
// the API has already decided.
//
// Dates are formatted by splitting the ISO string, never by constructing a
// `Date`. Two reasons, and the second is the one that bites: `new Date('2026-10-02')`
// is parsed as UTC midnight and rendered in the viewer's zone, so a deadline
// lands on 1 October for anyone west of Greenwich — an off-by-one in the exact
// direction that makes a closing window look further away than it is. And the
// world clock is frozen, so a browser's own idea of "now" has no business here.

const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const MONTHS_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                     'August', 'September', 'October', 'November', 'December']

function parts(iso) {
  if (typeof iso !== 'string' || iso.length < 10) return null
  const [y, m, d] = iso.slice(0, 10).split('-')
  const month = Number(m)
  if (!y || !month || !d) return null
  return { year: y, month, day: String(Number(d)) }
}

export function fmtDate(iso) {
  const p = parts(iso)
  return p ? `${p.day} ${MONTHS_SHORT[p.month - 1]} ${p.year}` : ''
}

export function fmtLongDate(iso) {
  const p = parts(iso)
  return p ? `${p.day} ${MONTHS_LONG[p.month - 1]} ${p.year}` : ''
}

export function fmtDateTime(iso) {
  const date = fmtDate(iso)
  if (!date) return ''
  const time = typeof iso === 'string' && iso.length >= 16 ? iso.slice(11, 16) : ''
  return time ? `${date}, ${time}` : date
}

// Money arrives as the string "1290.00" and is grouped as a string. It is never
// parsed to a float: a console that did arithmetic on money would be a second
// implementation of the thing the engine keeps in one place, and it is the copy
// that ends up in the letter.
export function money(dollars) {
  if (typeof dollars !== 'string' || !dollars) return ''
  const negative = dollars.startsWith('-')
  const bare = negative ? dollars.slice(1) : dollars
  const [whole, cents = '00'] = bare.split('.')
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return `${negative ? '-' : ''}$${grouped}.${cents}`
}

export function sentenceCase(value) {
  if (!value) return ''
  const spaced = String(value).replace(/_/g, ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

export const RISK_LABEL = {
  ok: 'On track',
  approaching: 'Approaching',
  critical: 'Critical',
  missed: 'Window closed',
  unassessable: 'Cannot be assessed',
}

export const STAGE_LABEL = {
  internal_1: 'Internal appeal, level 1',
  internal_2: 'Internal appeal, level 2',
  external: 'External review',
  civil_action: 'Civil action',
}

export const CLASS_LABEL = {
  clerical: 'Clerical',
  authorization: 'Authorisation',
  eligibility: 'Eligibility',
  coverage: 'Coverage',
  timeliness: 'Timeliness',
  clinical: 'Clinical',
  unassessable: 'Unassessable',
}

// What each kind of missing document actually is, in words somebody holding a
// letter would recognise. A label lookup on an identifier the API returns — the
// API decided which of these are missing; this only spells them out.
export const EVIDENCE_LABEL = {
  eob: 'Explanation of Benefits',
  denial_letter: 'The denial letter',
  clinical_note: "The clinician's letter of medical necessity",
  authorization: 'The prior authorisation',
  coverage_record: 'The plan document language',
  corrected_claim: "The provider's corrected claim",
  referral: 'The referral',
  proof_of_coverage: 'Proof of coverage on the date of service',
}

export function evidenceLabel(kind) {
  return EVIDENCE_LABEL[kind] || sentenceCase(kind)
}
