// The console's only source of truth. It never classifies a denial, counts a
// day or decides what a rule means — every action here is: call the API,
// refetch, render what came back. A console that reimplemented the policy could
// disagree with the engine, and the whole claim this codebase makes is that it
// cannot.
//
// `world.now` is the frozen demo clock. Nothing in this console calls
// `new Date()` with no argument: the world is fixed at 2026-09-02, and a browser
// that used its own clock would render a correct-but-empty screen that looks
// broken.

import { create } from 'zustand'
import * as api from './api.js'

const TOAST_MS = 5000

function emptyWorld() {
  return { now: null, now_at: null, case_id: null, autonomy: null, plans: [] }
}

export const useStore = create((set, get) => ({
  // Deadlines is the screen that carries the product, so it is what opens.
  route: 'deadlines',
  go: (route) => set({ route }),

  loading: true,
  error: null,
  busy: {},
  toast: null,

  world: emptyWorld(),
  caseFile: { case_id: null, claims: [], documents: [], denial_ids: [] },
  denials: [],
  deadlines: [],
  appeals: [],
  decisions: [],
  journal: [],
  timeline: [],
  autonomy: { level: 'balanced', levels: [], thresholds: {}, non_negotiable_rules: [] },

  // The last EOB upload's parse result, kept so the Case file screen can show
  // what was read and — the part that matters — what could not be.
  eob: null,
  clearEob: () => set({ eob: null }),

  notify: (message, tone = 'plain') => {
    const ticket = Symbol('toast')
    set({ toast: { message, tone }, _toastTicket: ticket })
    setTimeout(() => {
      if (get()._toastTicket === ticket) set({ toast: null })
    }, TOAST_MS)
  },

  refresh: async ({ quiet } = {}) => {
    if (!quiet) set({ loading: true })
    try {
      const [world, caseFile, denials, deadlines, appeals, decisions, journal, timeline, autonomy] =
        await Promise.all([
          api.getWorld(),
          api.getCase(),
          api.getDenials(),
          api.getDeadlines(),
          api.getAppeals(),
          api.getDecisions(),
          api.getJournal(),
          api.getTimeline(),
          api.getAutonomy(),
        ])
      set({
        world, caseFile, denials, deadlines, appeals, decisions, journal, timeline, autonomy,
        loading: false, error: null,
      })
    } catch (err) {
      set({ loading: false, error: err?.message || 'Could not reach Recourse' })
    }
  },

  triage: async () => {
    const key = 'triage'
    set((s) => ({ busy: { ...s.busy, [key]: true } }))
    try {
      const res = await api.triage()
      await get().refresh({ quiet: true })
      if (res.status === 'awaiting_decision') {
        get().notify('Recourse stopped and asked you something.', 'held')
        set({ route: 'decisions' })
      } else {
        get().notify('Triaged. The denials and any drafts are below.', 'good')
      }
      return res
    } catch (err) {
      get().notify(err?.message || 'Could not triage the case file', 'bad')
      throw err
    } finally {
      set((s) => ({ busy: { ...s.busy, [key]: false } }))
    }
  },

  press: async () => {
    const key = 'press'
    set((s) => ({ busy: { ...s.busy, [key]: true } }))
    try {
      const res = await api.press()
      await get().refresh({ quiet: true })
      if (res.status === 'awaiting_decision') {
        get().notify('Recourse stopped and asked you something.', 'held')
        set({ route: 'decisions' })
      } else {
        get().notify('Every open appeal has been swept against its clocks.', 'good')
      }
      return res
    } catch (err) {
      get().notify(err?.message || 'Could not sweep the clocks', 'bad')
      throw err
    } finally {
      set((s) => ({ busy: { ...s.busy, [key]: false } }))
    }
  },

  answerDecision: async (id, outcome, { by, role, note }) => {
    const key = `decision:${id}`
    set((s) => ({ busy: { ...s.busy, [key]: true } }))
    try {
      const res = await api.answerDecision(id, { outcome, by, role, note: note || '' })
      await get().refresh({ quiet: true })

      if (res.status === 'declined') {
        // The API already says, in plain words, that nothing was done. Say its
        // sentence rather than a cheerful paraphrase: a decline that reads like
        // a success is the failure this route was written to prevent.
        get().notify(res.detail || 'Nothing was done. The appeal is exactly as it was.', 'declined')
      } else if (res.status === 'awaiting_decision') {
        get().notify('Recourse went on and stopped again — there is another question below.', 'held')
      } else {
        get().notify('Approved. Recourse carried on from where it stopped.', 'good')
      }
      return res
    } catch (err) {
      get().notify(err?.message || 'Could not record that decision', 'bad')
      throw err
    } finally {
      set((s) => ({ busy: { ...s.busy, [key]: false } }))
    }
  },

  setAutonomy: async (level) => {
    const key = 'autonomy'
    set((s) => ({ busy: { ...s.busy, [key]: true } }))
    try {
      const autonomy = await api.setAutonomy(level)
      set({ autonomy })
      // The warning window moves with the dial, so the deadline screen is a
      // different screen after this call. Refetch rather than leave it stale.
      await get().refresh({ quiet: true })
      get().notify(`Autonomy set to ${level}.`, 'good')
      return autonomy
    } catch (err) {
      get().notify(err?.message || 'Could not change autonomy', 'bad')
      throw err
    } finally {
      set((s) => ({ busy: { ...s.busy, [key]: false } }))
    }
  },

  uploadEob: async (file) => {
    const key = 'eob'
    set((s) => ({ busy: { ...s.busy, [key]: true } }))
    try {
      const parsed = await api.uploadEob(file)
      set({ eob: parsed })
      await get().refresh({ quiet: true })
      if (parsed.needs_review) {
        get().notify('Read, but some of it needs a person to check it.', 'held')
      } else {
        get().notify(`Read ${parsed.lines.length} service lines, ${parsed.denied.length} denied.`, 'good')
      }
      return parsed
    } catch (err) {
      get().notify(err?.message || 'Could not read that file', 'bad')
      throw err
    } finally {
      set((s) => ({ busy: { ...s.busy, [key]: false } }))
    }
  },

  resetDemo: async () => {
    const key = 'reset'
    set((s) => ({ busy: { ...s.busy, [key]: true } }))
    try {
      await api.resetDemo()
      set({ eob: null })
      await get().refresh({ quiet: true })
      set({ route: 'deadlines' })
      get().notify('The world is back to how it started.', 'good')
    } catch (err) {
      get().notify(err?.message || 'Could not reset the world', 'bad')
      throw err
    } finally {
      set((s) => ({ busy: { ...s.busy, [key]: false } }))
    }
  },
}))
