/* COMMS activity stream. Player channels stay. Action outcomes do not.

The redesign cockpit paints recent_events under the COMMS header. A refused
trade (TRADE_FAILED, including NOTE 71 "You only have N empty holds.") and the
same class of refusal (warp blocked, invalid action) already print on the
verdict and the last-result line. They are not Fed Comm, sub-space radio, a
private hail, or a corporation memo.

This helper only decides which rows that activity stream may show. It does not
remove the event from the observation, the verdict, or lastResult.
*/
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.TW2KCommsStream = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  // Fed Comm and sub-space radio are both broadcast events. The link says which.
  const CHANNEL_KINDS = { hail: true, broadcast: true, corp_memo: true };
  // Refusals the command line already speaks. Same set the server skips when
  // it would otherwise emit a second AGENT_ERROR for a trade or a warp.
  const OUTCOME_KINDS = { trade_failed: true, warp_blocked: true, agent_error: true };

  function linkOf(ev) {
    const facts = (ev && ev.facts) || {};
    const payload = (ev && ev.payload) || {};
    return String(facts.link || payload.link || "");
  }

  function isChannelMessage(ev) {
    if (!ev || typeof ev !== "object") return false;
    const kind = String(ev.kind || "");
    if (CHANNEL_KINDS[kind]) return true;
    const link = linkOf(ev);
    if (link === "fed" || link === "radio" || link === "hail" || link === "corp") return true;
    const summary = String(ev.summary || "");
    if (/^Federation comm-link,/i.test(summary)) return true;
    if (/^Sub-space radio\b/i.test(summary)) return true;
    if (/\bhails you:/i.test(summary)) return true;
    if (/^Corporate memo\b/i.test(summary)) return true;
    return false;
  }

  // A lastResult twin: the engine's refusal sentence, not a world event.
  function isActionOutcome(ev) {
    if (!ev || typeof ev !== "object") return false;
    if (isChannelMessage(ev)) return false;
    const kind = String(ev.kind || "");
    if (OUTCOME_KINDS[kind]) return true;
    const summary = String(ev.summary || "");
    if (/\btrade failed\b/i.test(summary)) return true;
    if (/\bplanetary trade refused\b/i.test(summary)) return true;
    if (/\bport countered at\b/i.test(summary)) return true;
    if (/\binvalid action\b/i.test(summary)) return true;
    if (/\bagent error:/i.test(summary)) return true;
    if (/\btried to warp to\b/i.test(summary)) return true;
    return false;
  }

  function forCommsActivity(events) {
    const out = [];
    const list = events || [];
    for (let i = 0; i < list.length; i++) {
      if (isActionOutcome(list[i])) continue;
      out.push(list[i]);
    }
    return out;
  }

  return {
    isChannelMessage: isChannelMessage,
    isActionOutcome: isActionOutcome,
    forCommsActivity: forCommsActivity,
  };
});
