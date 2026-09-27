/* Video cockpit V2 — pure event-to-clip resolver + queue.
 *
 * No DOM, no clock, no /state. Input is a fogged /events batch, the seat's own
 * observation (self_id, sector.id), client visit memory, and a v2 manifest.
 * resolve() returns [{clip_key, priority}] highest priority (lowest number) first.
 * createSession() applies queue length 1, preemption, stale drop, cooldown, and
 * tab-hidden (the renderer drives it; tests drive it with an explicit `now`).
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.TW2KMediaResolver = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const COMBAT_WORST = { "combat.incoming": 0, "combat.miss": 1, "combat.hit": 2, "combat.witnessed": 3 };

  function outcomeHit(facts) {
    const o = facts.outcome;
    if (o === "hit" || o === "destroyed") return true;
    if (o === "miss") return false;
    if (typeof facts.defender_losses === "number" && typeof facts.attacker_losses === "number") {
      return facts.defender_losses > facts.attacker_losses;
    }
    return true; // unknown exchange reads as a hit (neutral footage)
  }

  function predicate(name, ev, obs, state) {
    const self = obs.self_id;
    const facts = ev.facts || {};
    const here = obs.sector && obs.sector.id;
    if (name === "self") return ev.actor_id === self;
    if (name === "self_attacker") return facts.attacker === self;
    if (name === "self_defender") return facts.defender === self;
    if (name === "self_victim") return facts.victim === self;
    if (name === "first_in_visit") return state.visit_sector === ev.sector_id && !state.docked_in_visit;
    if (name === "outcome_hit") return outcomeHit(facts);
    if (name === "witnessed_in_my_sector") return ev.actor_id !== self && ev.sector_id === here;
    return false;
  }

  function ruleMatches(rule, ev, obs, state) {
    return String(rule || "").split("&&").every((part) => {
      const token = part.trim();
      if (!token) return false;
      const neg = token.charAt(0) === "!";
      return neg ? !predicate(token.slice(1), ev, obs, state) : predicate(token, ev, obs, state);
    });
  }

  function resolve(batch, obs, state, manifest) {
    const st = { visit_sector: state.visit_sector, docked_in_visit: !!state.docked_in_visit };
    const self = obs && obs.self_id;
    const triggers = (manifest && manifest.triggers) || [];
    const clips = (manifest && manifest.clips) || {};
    const hits = [];
    const rows = [...(batch || [])].sort((a, b) => (a.seq || 0) - (b.seq || 0));
    for (const ev of rows) {
      if (ev.actor_id === self && (ev.kind === "warp" || ev.kind === "autopilot")) {
        const arrived = ev.kind === "warp" ? (ev.facts || {}).to : (ev.facts || {}).target;
        if (arrived !== undefined && arrived !== null) st.visit_sector = arrived;
        st.docked_in_visit = false;
      }
      let matched = null;
      for (const t of triggers) {
        if (t.kind === ev.kind && ruleMatches(t.rule, ev, obs, st)) { matched = t; break; }
      }
      if (!matched) continue;
      const pri = clips[matched.clip] && typeof clips[matched.clip].priority === "number" ? clips[matched.clip].priority : 4;
      hits.push({
        clip_key: matched.clip, priority: pri, seq: ev.seq || 0, sector_id: ev.sector_id,
        group: matched.clip.indexOf("combat.") === 0 ? "combat" : (matched.coalesce === "warp" || matched.clip === "warp.out" ? "warp" : matched.clip),
      });
      if (matched.clip === "dock.port") st.docked_in_visit = true;
    }
    const grouped = new Map();
    for (const h of hits) {
      const prev = grouped.get(h.group);
      if (!prev) { grouped.set(h.group, h); continue; }
      if (h.group === "combat" && (COMBAT_WORST[h.clip_key] ?? 9) < (COMBAT_WORST[prev.clip_key] ?? 9)) grouped.set(h.group, h);
      else if (h.group !== "combat") prev.seq = Math.max(prev.seq, h.seq);
    }
    if (state) { state.visit_sector = st.visit_sector; state.docked_in_visit = st.docked_in_visit; }
    return [...grouped.values()]
      .sort((a, b) => a.priority - b.priority || a.seq - b.seq)
      .map((h) => ({ clip_key: h.clip_key, priority: h.priority, seq: h.seq, sector_id: h.sector_id }));
  }

  function createSession(manifest) {
    const defaults = (manifest && manifest.defaults) || {};
    const staleMs = typeof defaults.stale_ms === "number" ? defaults.stale_ms : 4000;
    const clips = (manifest && manifest.clips) || {};
    const s = { playing: null, waiting: null, lastSeq: 0, playedAt: {} };

    function cooldownOk(key, now) {
      const cd = (clips[key] && clips[key].cooldown_ms) || 0;
      return !(cd && s.playedAt[key] !== undefined && now - s.playedAt[key] < cd);
    }
    function dropStale(now, postedSeq) {
      if (!s.waiting) return;
      if (now - s.waiting.at > staleMs) s.waiting = null;
      else if (typeof postedSeq === "number" && s.waiting.seq < postedSeq) s.waiting = null;
    }
    function start(item, now) {
      s.playing = item;
      s.playedAt[item.clip_key] = now;
    }

    function consider(items, now, opts) {
      opts = opts || {};
      if (typeof opts.maxSeq === "number") s.lastSeq = Math.max(s.lastSeq, opts.maxSeq);
      dropStale(now, opts.postedSeq);
      const was = s.playing && s.playing.clip_key;
      let preempted = false;
      let startedItem = null;
      if (opts.hidden) return { playing: null, waiting: null, preempted: false, started: false, item: null, hidden: true };
      for (const raw of items || []) {
        if (!cooldownOk(raw.clip_key, now)) continue;
        const item = { clip_key: raw.clip_key, priority: raw.priority, seq: raw.seq || 0, sector_id: raw.sector_id, at: now };
        if (!s.playing) { start(item, now); startedItem = s.playing; }
        else if (item.priority < s.playing.priority) { start(item, now); s.waiting = null; preempted = true; startedItem = s.playing; }
        else s.waiting = item;
      }
      return {
        playing: s.playing && s.playing.clip_key,
        waiting: s.waiting && s.waiting.clip_key,
        preempted: preempted && !!was && s.playing.clip_key !== was,
        started: !!startedItem,
        item: startedItem,
      };
    }
    function finish(now) {
      s.playing = null;
      dropStale(now);
      if (s.waiting && cooldownOk(s.waiting.clip_key, now)) {
        start(s.waiting, now);
        s.waiting = null;
        return s.playing;
      }
      s.waiting = null;
      return null;
    }
    function stop() {
      s.playing = null;
      s.waiting = null;
    }
    return {
      consider, finish, stop,
      state: () => ({ playing: s.playing && s.playing.clip_key, waiting: s.waiting && s.waiting.clip_key, lastSeq: s.lastSeq,
        playingSector: s.playing && s.playing.sector_id, waitingSector: s.waiting && s.waiting.sector_id }),
    };
  }

  return { resolve, createSession, outcomeHit };
});
