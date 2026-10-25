/* COMMS feed filter.
 *
 * The COMMS card is player channels only: Fed Comm, sub-space radio, a private
 * hail, and a corporation memo. Engine action outcomes (TRADE_FAILED, a haggle
 * miss, port / planet / combat notices, and any other non-chat event) stay on
 * the activity log and on lastResult / verdict. This does not look at who is
 * sitting the ship, so an AI seat is not clamped or muted.
 */
(function (root) {
  "use strict";

  const CHAT_KINDS = {
    fed: true,
    fedcomm: true,
    radio: true,
    hail: true,
    corp: true,
    corp_memo: true,
    broadcast: true,
  };

  function kindOf(row) {
    return String((row && row.kind) || "").toLowerCase();
  }

  function lineOf(row) {
    if (!row) return "";
    if (row.line) return String(row.line);
    return String(row.summary || row.message || "");
  }

  function looksLikeChat(row) {
    const line = lineOf(row);
    if (/^Federation comm-link,/i.test(line)) return true;
    if (/^Sub-space radio \[/i.test(line)) return true;
    if (/ hails you:/i.test(line)) return true;
    if (/^Corporate memo \(/i.test(line)) return true;
    if (/^Your hail to .+ fell on deaf ears\./i.test(line)) return true;
    return false;
  }

  function isChat(row) {
    if (!row || typeof row !== "object") return false;
    const kind = kindOf(row);
    if (CHAT_KINDS[kind]) return true;
    if (kind) return false;
    return looksLikeChat(row);
  }

  function isActionOutcome(row) {
    if (!row || typeof row !== "object") return false;
    if (isChat(row)) return false;
    return kindOf(row) !== "" || lineOf(row) !== "";
  }

  function commsFeed(rows) {
    return (rows || []).filter(isChat);
  }

  function activityFeed(rows) {
    return (rows || []).filter((row) => row && !isChat(row));
  }

  function commsLines(turnLog, events, selfId) {
    const fromLog = Array.isArray(turnLog) ? commsFeed(turnLog) : [];
    const seen = new Set();
    fromLog.forEach((row) => {
      const line = lineOf(row);
      if (line) seen.add(line);
    });
    const extra = [];
    (events || []).forEach((ev) => {
      if (!isChat(ev)) return;
      const line = lineOf(ev);
      if (!line || seen.has(line)) return;
      // v3.11 already hands other traders' lines through the turn log, and
      // that log expires. Only the sender's own copy is missing from it.
      // With no turn log (legacy), the event feed is the chat record.
      if (Array.isArray(turnLog)) {
        if (!selfId || ev.actor_id !== selfId) return;
      }
      seen.add(line);
      extra.push(ev);
    });
    return fromLog.concat(extra);
  }

  root.TW2KCommsFeed = {
    isChat: isChat,
    isActionOutcome: isActionOutcome,
    commsFeed: commsFeed,
    activityFeed: activityFeed,
    commsLines: commsLines,
    lineOf: lineOf,
  };
})(typeof window !== "undefined" ? window : globalThis);
