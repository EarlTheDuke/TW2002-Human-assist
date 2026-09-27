/* Cockpit parity (G1 = CP1-CP5, docs/plans/2026-09-26-cockpit-parity-plan.md).
 *
 * Pure text formatters for the Observation fields an API LLM seat reads in
 * `format_observation`. No DOM, no fetch, no rule constants: every string is
 * built from values the server already sent, so the same functions run in
 * the browser (window.TW2KParity) and under Node in the pytest suite.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.TW2KParity = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  const SHORT = { fuel_ore: "Fuel", organics: "Org", equipment: "Equip", colonists: "Colonists" };
  const fmt = (n) => (n === null || n === undefined || n === "" ? "-" : Number(n).toLocaleString("en-US"));
  const has = (v) => v !== null && v !== undefined && v !== "";

  function pools(d) {
    const e = Object.entries(d || {});
    return e.length ? e.map(([k, n]) => `${SHORT[k] || k} ${fmt(n)}`).join(" · ") : "";
  }

  // CP1 - empire planet tape (G6-G9): id, origin, colonists per pool + total,
  // stockpile, growth runway. Enough to size a ferry without Raw obs.
  function planetRow(p) {
    const cit = `citadel L${p.citadel_level}${p.citadel_target > p.citadel_level ? ` → L${p.citadel_target} day ${p.citadel_complete_day}` : ""}`;
    const col = pools(p.colonists);
    const metas = [
      `id ${p.id}`,
      `sector ${p.sector_id}`,
      has(p.origin) ? `origin ${p.origin}` : null,
      cit,
      `colonists ${fmt(p.colonists_total)}${col ? ` (${col})` : ""}`,
      `stockpile ${pools(p.stockpile) || "empty"}`,
      p.production ? `makes/day ${pools(p.production) || "nothing"}` : null,
      has(p.organics_consumption_per_day) ? `eats ${fmt(p.organics_consumption_per_day)} Org/day` : null,
      has(p.growth_active) ? (p.growth_active ? "growing" : "NOT growing (no organics)") : null,
      has(p.organics_days_left) ? `organics last ${fmt(p.organics_days_left)} day(s)` : null,
      `${fmt(p.fighters)} fighters`,
      `${fmt(p.shields)} shields`,
    ];
    return { title: `${p.name} [${p.class}]`, metas: metas.filter(has), cls: p.growth_active === false ? "warn" : "" };
  }

  function orphanRow(p) {
    return {
      title: `${p.name} [${p.class}]`,
      metas: [`id ${p.id}`, `sector ${p.sector_id}`, `citadel L${p.citadel_level}`, `${fmt(p.fighters)} fighters`,
        has(p.shields) ? `${fmt(p.shields)} shields` : null, `was ${p.former_owner_id}`].filter(has),
      cls: "",
    };
  }

  // CP2 - every fog-visible other player (G4-G5, G25). Non-corpmates carry
  // only what the engine chose to reveal (sector + hull when co-located).
  function otherPlayerRow(o, hereId) {
    const located = has(o.sector_id);
    const metas = [
      o.alive === false ? "DESTROYED" : null,
      o.is_corpmate ? "corpmate" : "not in your corp",
      has(o.corp_ticker) ? `corp ${o.corp_ticker}` : null,
      located ? `sector ${o.sector_id}${o.sector_id === hereId ? " (here)" : ""}` : "location hidden (not in your sector)",
      has(o.ship_class) ? o.ship_class : null,
      has(o.credits) ? `${fmt(o.credits)} cr` : null,
      has(o.fighters) ? `${fmt(o.fighters)} fighters` : null,
      has(o.alignment) ? `alignment ${o.alignment}` : null,
    ];
    return {
      title: `${o.is_corpmate ? "Corpmate" : "Commander"} ${o.name} (${o.id})`,
      metas: metas.filter(has),
      cls: o.alive === false ? "stale" : o.is_corpmate ? "" : located ? "warn" : "",
    };
  }

  function occupantLabel(id, others) {
    const o = (others || []).find((x) => x.id === id);
    if (!o) return id;
    return `${id} ${o.name}${has(o.ship_class) ? ` · ${o.ship_class}` : ""}${o.is_corpmate ? " · corpmate" : ""}`;
  }

  // CP3 - operator directive meta + dialogue transcript (G2-G3). Same last-8
  // slice format_observation ships to API seats.
  const DIALOGUE_TAIL = 8;
  function directiveMeta(obs) {
    if (!obs.operator_directive) return "";
    const d = obs.operator_directive_updated_day;
    const t = obs.operator_directive_updated_tick;
    return has(d) ? ` (set day ${d}${has(t) ? "." + t : ""})` : "";
  }
  function dialogueLines(obs) {
    return (obs.operator_dialogue || []).slice(-DIALOGUE_TAIL).map((m) => ({
      role: m.role === "ai" ? "AI" : "Operator",
      when: has(m.day) ? `D${m.day}${has(m.tick) ? "." + m.tick : ""}` : "",
      text: String(m.message || ""),
    }));
  }

  // CP4 - prompt twins (G1, G12). The API prompt is JSON; parse it rather
  // than recomputing stage_hint in the browser.
  function parseTwin(msg) {
    if (!msg || typeof msg !== "string") return null;
    try { return JSON.parse(msg); } catch { return null; }
  }
  function stageText(sh) {
    if (!sh || !sh.stage) return "";
    return `${sh.stage} ${sh.label || ""}`.trim();
  }
  function stageDetail(sh) {
    if (!sh || !sh.stage) return "";
    return [sh.reason, sh.next_milestone ? `next: ${sh.next_milestone}` : ""].filter(Boolean).join(" · ");
  }

  // CP5 - thoughts / usage are off by default. The server already limits
  // agent_thought and llm_usage to their actor; the client adds the seat
  // check so a toggle can only ever reveal this seat's own lines.
  const HIDDEN_BY_DEFAULT = { agent_thought: "thoughts", llm_usage: "usage" };
  function eventShown(e, opts) {
    const o = opts || {};
    const gate = HIDDEN_BY_DEFAULT[e.kind];
    if (!gate) return true;
    if (e.actor_id && o.seat && e.actor_id !== o.seat) return false;
    return !!o[gate];
  }

  return {
    planetRow, orphanRow, otherPlayerRow, occupantLabel,
    directiveMeta, dialogueLines, DIALOGUE_TAIL,
    parseTwin, stageText, stageDetail,
    eventShown, HIDDEN_BY_DEFAULT,
  };
});
