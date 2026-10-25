"""COMMS is player channels. Action outcomes stay on the log and on lastResult.

Ben saw `Guest 1 trade failed: You only have 15 empty holds.` under the COMMS
header. That line is an engine TRADE_FAILED event. Fed, radio, hail, and corp
memo lines still belong on the COMMS card. The filter does not look at the seat,
so an AI trader is not clamped.
"""

from __future__ import annotations

import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "web" / "comms-feed.js"
PAGE = ROOT / "web" / "redesign.html"
REDESIGN = ROOT / "web" / "redesign.js"

NODE = r"""
const fs = require("fs");
const vm = require("vm");
const s = {};
s.window = s;
vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"), s, { filename: process.argv[1] });
const feed = s.TW2KCommsFeed;
if (!feed) throw new Error("missing TW2KCommsFeed");

const fail = {
  seq: 9, kind: "trade_failed", actor_id: "P2",
  summary: "Guest 1 trade failed: You only have 15 empty holds.",
};
const haggle = {
  seq: 10, kind: "trade_failed", actor_id: "P2",
  summary: "Guest 1 port countered at 42",
};
const patience = {
  seq: 11, kind: "trade_failed", actor_id: "P2",
  summary: "Guest 1 trade failed: the port lost patience",
};
const combat = { seq: 12, kind: "combat", actor_id: "P2", summary: "Guest 1 attacked in 7" };
const planet = { seq: 13, kind: "land_planet", actor_id: "P2", summary: "Guest 1 landed on Earth" };
const blocked = { seq: 14, kind: "warp_blocked", actor_id: "P2", summary: "no path to 80" };
const poisoned = {
  seq: 15, kind: "trade_failed", actor_id: "P2",
  summary: "Ann hails you: this is still a failed trade",
};
const aiFail = {
  seq: 16, kind: "trade_failed", actor_id: "bot-7",
  summary: "Guest 1 trade failed: You only have 15 empty holds.",
  facts: { seat: "ai" },
};
const fed = { kind: "fedcomm", line: "Federation comm-link, Ann: all hands" };
const radio = { kind: "radio", line: "Sub-space radio [4] Ann: quiet" };
const hail = { kind: "hail", line: "Ann hails you: near" };
const corp = { kind: "corp", line: "Corporate memo (ZZ) Ann: members" };
const deaf = { kind: "hail", line: "Your hail to Bo fell on deaf ears." };
const bare = { line: "Federation comm-link, Ann: bare" };
const own = {
  seq: 20, kind: "broadcast", actor_id: "P1",
  summary: "Federation comm-link, Ann: I sent this",
};
const other = {
  seq: 21, kind: "broadcast", actor_id: "P2",
  summary: "Federation comm-link, Bo: hello",
};
const memo = {
  seq: 22, kind: "corp_memo", actor_id: "P1",
  summary: "Corporate memo (ZZ) Ann: members",
};

function kinds(rows) { return rows.map((row) => row.kind || ""); }
function lines(rows) { return rows.map((row) => feed.lineOf(row)); }

[fail, haggle, patience, combat, planet, blocked, poisoned, aiFail].forEach((row) => {
  if (feed.isChat(row) || !feed.isActionOutcome(row)) {
    throw new Error("action outcome leaked into chat: " + feed.lineOf(row));
  }
});
[fed, radio, hail, corp, deaf, bare, own, memo].forEach((row) => {
  if (!feed.isChat(row) || feed.isActionOutcome(row)) {
    throw new Error("chat dropped: " + feed.lineOf(row));
  }
});

const mixed = [fail, fed, combat, hail, haggle, planet, own];
if (kinds(feed.commsFeed(mixed)).indexOf("trade_failed") >= 0) throw new Error("commsFeed kept a trade fail");
if (kinds(feed.commsFeed(mixed)).indexOf("combat") >= 0) throw new Error("commsFeed kept combat");
if (lines(feed.commsFeed(mixed)).join("|") !== [fed.line, hail.line, own.summary].join("|")) {
  throw new Error("commsFeed " + lines(feed.commsFeed(mixed)).join("|"));
}
const activity = kinds(feed.activityFeed(mixed));
["trade_failed", "combat", "land_planet"].forEach((kind) => {
  if (activity.indexOf(kind) < 0) throw new Error("activity log lost " + kind);
});
if (activity.indexOf("fedcomm") >= 0 || activity.indexOf("broadcast") >= 0) {
  throw new Error("activity log kept chat");
}

const v311 = feed.commsLines([fed, corp, deaf], [fail, other, own, memo, patience], "P1");
const v311Lines = lines(v311);
if (v311Lines.indexOf(fail.summary) >= 0) throw new Error("v311 comms showed trade fail");
if (v311Lines.indexOf(other.summary) >= 0) throw new Error("v311 comms replayed someone else's line");
[fed.line, corp.line, deaf.line, own.summary, memo.summary].forEach((line) => {
  if (v311Lines.indexOf(line) < 0) throw new Error("v311 comms missed " + line);
});

const legacy = feed.commsLines(null, [fail, other, hail, combat], "P1");
const legacyLines = lines(legacy);
if (legacyLines.join("|") !== other.summary + "|" + hail.line) {
  throw new Error("legacy comms " + legacyLines.join("|"));
}

if (feed.commsLines([fed], [own], "").some((row) => row === own)) {
  throw new Error("missing seat must not echo every broadcast");
}
if (JSON.stringify(kinds(feed.activityFeed([aiFail, fed]))) !== JSON.stringify(["trade_failed"])) {
  throw new Error("AI trade fail was clamped or moved");
}

process.stdout.write("ok");
"""


class _Tree(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[dict[str, str]] = []
        self.log_inside_comms = False
        self.turn_inside_comms = False
        self.saw_comms = False
        self.saw_log = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        got = {key: value or "" for key, value in attrs}
        node = {"id": got.get("id", ""), "test": got.get("data-testid", "")}
        if node["test"] == "comms-panel":
            self.saw_comms = True
        if node["id"] == "turnLog" and any(item["test"] == "comms-panel" for item in self.stack):
            self.turn_inside_comms = True
        if node["id"] == "log":
            self.saw_log = True
            if any(item["test"] == "comms-panel" for item in self.stack):
                self.log_inside_comms = True
        self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        if self.stack:
            self.stack.pop()


def test_filter_keeps_trade_fails_off_the_comms_feed() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    out = subprocess.check_output([node, "-e", NODE, str(FEED)], text=True)
    assert out.strip() == "ok"


def test_page_splits_comms_from_the_activity_log() -> None:
    html = PAGE.read_text(encoding="utf-8")
    tree = _Tree()
    tree.feed(html)
    assert tree.saw_comms and tree.saw_log
    assert tree.turn_inside_comms
    assert tree.log_inside_comms is False
    assert html.index("/static/comms-feed.js") < html.index("/static/redesign.js")
    js = REDESIGN.read_text(encoding="utf-8")
    assert "feed.activityFeed(rows)" in js
    assert "feed.commsLines(" in js
    assert '(/trade failed|lost patience/i.test(raw) ? "FAILED" : "REFUSED")' in js
    assert "hull-meshes" not in (ROOT / "web" / "comms-feed.js").read_text(encoding="utf-8")
