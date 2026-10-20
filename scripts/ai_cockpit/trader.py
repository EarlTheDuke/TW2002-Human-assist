"""Rule trader. Every fact it uses is text on the seat page."""

from __future__ import annotations

import re

from ai_cockpit.actions import Action

_GOODS = ("Fuel Ore", "Organics", "Equipment")
_PORT_CODE = re.compile(r"Class\s+\d+\s+([BSX]{3})", re.I)
_NUMBER = re.compile(r"[\d,]+")
_WARP = re.compile(r"^\d+:(\d+)")
_CATALOG = re.compile(r"\b(?:armid|limpet|atomic)\s+mines\b|\bmine disruptor\b", re.I)
_OWN_FIGHTERS = re.compile(r"your fighters here:[^.]*\.", re.I)
_DANGER = re.compile(r"ferrengi|hostile fighters|\boffensive\b|\bmines\b", re.I)
_DAY_END = re.compile(r"ends your day", re.I)


def _int(text: object) -> int:
    match = _NUMBER.search(str(text or ""))
    if match is None:
        return 0
    return int(match.group(0).replace(",", ""))


def _holds(text: str) -> dict[str, int]:
    cargo: dict[str, int] = {}
    for name in _GOODS:
        match = re.search(re.escape(name) + r"\s+([\d,]+)", text or "", re.I)
        cargo[name] = int(match.group(1).replace(",", "")) if match else 0
    return cargo


def _room(ship: str, cargo: dict[str, int]) -> int:
    match = re.search(r"Holds\s+([\d,]+)\s*/\s*([\d,]+)", ship or "", re.I)
    if match is None:
        return 1 if sum(cargo.values()) == 0 else 0
    used = int(match.group(1).replace(",", ""))
    cap = int(match.group(2).replace(",", ""))
    return max(0, cap - used)


class ScriptedTrader:
    """Reads the sector, port and holds, then trades, buys gear, and spends the day."""

    def __init__(self) -> None:
        self.ports: dict[int, dict[str, dict[str, int]]] = {}
        self.codes: dict[int, str] = {}
        self.danger: set[int] = set()
        self.visited: set[int] = set()
        self.previous = 0
        self.day = 0
        self.bought: set[str] = set()
        self.gear: dict[str, str] | None = None
        self.dock_waits = 0
        self.plan_note = ""
        self.last_usage = None

    def decide(self, view) -> Action:
        if not view.manual_read:
            self.plan_note = "read the manual"
            return Action("click", label="Manual")
        if not view.screen:
            return self._bare(view)
        return self.play(view)

    def _bare(self, view) -> Action:
        """A label list with no scraped screen still sells, then waits."""
        labels = [row.strip() for row in view.labels if row and row.strip()]
        upper = [row.upper() for row in labels]
        if any(row == "CONFIRM" for row in upper):
            self.plan_note = "confirm"
            return Action("click", label="CONFIRM")
        if any(row.startswith("SELL") for row in upper):
            self.plan_note = "sell"
            return Action("click", label="SELL")
        self.plan_note = "wait"
        return Action("press", key=".")

    def play(self, view) -> Action:
        screen = view.screen or {}
        labels = [row.strip() for row in (screen.get("labels") or view.labels or []) if row and row.strip()]
        sector = _int(screen.get("sector"))
        day = _int(screen.get("day"))
        turns = _int(screen.get("turns"))
        credits = _int(screen.get("credits"))
        if day and day != self.day:
            self.day = day
            self.bought.clear()
            self.gear = None
            self.dock_waits = 0
        cargo = _holds(str(screen.get("holds") or ""))
        self._remember(sector, screen, cargo)
        action = (
            self._modal(screen, labels, turns)
            or self._form(screen, labels)
            or self._leave_surface(labels)
            or self._leave_danger(sector, screen, cargo)
            or self._sell(screen, cargo)
            or self._buy(screen, cargo)
            or self._stardock(screen, labels, credits)
            or self._warp(screen, sector, cargo)
            or self._spend(screen, turns)
        )
        if sector:
            self.previous = sector
            self.visited.add(sector)
        return action

    def _remember(self, sector: int, screen: dict, cargo: dict[str, int]) -> None:
        if not sector:
            return
        if self._threatened(screen):
            self.danger.add(sector)
        book = self.ports.setdefault(sector, {})
        for row in screen.get("rows") or []:
            cells = [str(cell) for cell in (row.get("cells") or [])]
            if len(cells) < 4:
                continue
            name = next((good for good in _GOODS if good.lower() in cells[0].lower()), "")
            if not name:
                continue
            price_at = 4 if len(cells) > 4 and str(cells[3]).endswith("%") else 3
            price = _int(cells[price_at] if price_at < len(cells) else "")
            status = cells[1].lower()
            slot = book.setdefault(name, {})
            if status.startswith("buying"):
                slot["bid"] = price
            elif status.startswith("selling"):
                slot["ask"] = price
        code = _PORT_CODE.search(str(screen.get("port") or ""))
        if code:
            self.codes[sector] = code.group(1).upper()
        del cargo

    def _threatened(self, screen: dict) -> bool:
        """Ferrengi, hostile fighters, and deployed mines. A gear list is not a threat."""
        here = str(screen.get("here") or "")
        form = str(screen.get("formText") or "")
        if form:
            here = here.replace(form, " ")
        notes = _OWN_FIGHTERS.sub(" ", _CATALOG.sub(" ", here))
        notes += "\n" + str(screen.get("threat") or "")
        return _DANGER.search(notes) is not None

    def _at_dock(self, screen: dict) -> bool:
        blob = " ".join(
            str(screen.get(key) or "") for key in ("port", "here", "sector")
        ).lower()
        return _int(screen.get("sector")) == 1 or "stardock" in blob

    def _gear_pending(self) -> bool:
        return "holds" not in self.bought or "fighters" not in self.bought

    def _known_bid(self, good: str) -> int:
        best = 0
        for book in self.ports.values():
            slot = book.get(good) or {}
            if isinstance(slot, dict):
                best = max(best, int(slot.get("bid") or 0))
        return best

    def _modal(self, screen: dict, labels: list[str], turns: int) -> Action | None:
        if not screen.get("menuOpen"):
            return None
        text = str(screen.get("menuText") or "")
        if screen.get("formOpen"):
            return None
        if _DAY_END.search(text) and turns < 3 and any(row.upper() == "CONFIRM" for row in labels):
            self.plan_note = "spend the last turns"
            return Action("click", label="CONFIRM")
        self.plan_note = "close the dialog"
        return Action("press", key="Escape")

    def _form(self, screen: dict, labels: list[str]) -> Action | None:
        if not screen.get("formOpen"):
            self.gear = None if self.gear and self.gear.get("phase") == "confirm" else self.gear
            return None
        fields = dict(screen.get("fields") or {})
        if screen.get("gearNote"):
            fields["note"] = str(screen.get("gearNote") or "")
        text = str(screen.get("formText") or "") + " " + str(screen.get("haggle") or "")
        if self.gear and "item" in fields:
            return self._gear_step(fields)
        if "BUY EQUIP" in text.upper() and "item" in fields:
            item = "fighters" if "holds" in self.bought else "holds"
            self.gear = {"item": item, "phase": "select", "qty": "1" if item == "holds" else "5"}
            return self._gear_step(fields)
        trade = "TRADE" in text.upper() or "port counter" in text.lower() or "unit_price" in fields
        if trade and any(row.upper() == "CONFIRM" for row in labels):
            self.plan_note = "accept the port's price"
            return Action("click", label="CONFIRM")
        if any(row.upper() == "ESC" for row in labels):
            self.plan_note = "leave the form"
            return Action("click", label="ESC")
        self.plan_note = "close the form"
        return Action("press", key="Escape")

    def _gear_step(self, fields: dict) -> Action:
        assert self.gear is not None
        phase = self.gear["phase"]
        item = self.gear["item"]
        if phase == "select":
            self.gear["phase"] = "qty"
            self.plan_note = f"choose {item}"
            return Action("type", selector='[data-n="item"]', text=item)
        if phase == "qty":
            qty = self.gear["qty"]
            note = str(fields.get("note") or "")
            cap = _int(note.split("up to")[-1]) if "up to" in note.lower() else 0
            if cap and int(qty) > cap:
                qty = str(cap)
            self.gear["phase"] = "confirm"
            self.plan_note = f"qty {qty} {item}"
            return Action("type", selector='[data-n="qty"]', text=qty)
        self.bought.add(item)
        self.gear = None
        self.plan_note = f"buy {item}"
        return Action("click", label="CONFIRM")

    def _leave_surface(self, labels: list[str]) -> Action | None:
        for label in labels:
            if "lift off" in label.lower():
                self.plan_note = "lift off"
                return Action("click", label=label)
        return None

    def _leave_danger(self, sector: int, screen: dict, cargo: dict[str, int]) -> Action | None:
        if sector not in self.danger:
            return None
        action = self._warp(screen, sector, cargo, flee=True)
        if action is not None:
            self.plan_note = "leave danger"
        return action

    def _sell(self, screen: dict, cargo: dict[str, int]) -> Action | None:
        best: tuple[int, str] | None = None
        for row in screen.get("rows") or []:
            button = str(row.get("button") or "")
            if not button.upper().startswith("SELL"):
                continue
            cells = [str(cell) for cell in (row.get("cells") or [])]
            name = next((good for good in _GOODS if cells and good.lower() in cells[0].lower()), "")
            if name and cargo.get(name, 0) <= 0:
                continue
            price_at = 4 if len(cells) > 4 and str(cells[3]).endswith("%") else 3
            price = _int(cells[price_at] if price_at < len(cells) else "")
            if best is None or price > best[0]:
                best = (price, button)
        if best is None:
            return None
        self.plan_note = "sell " + best[1]
        return Action("click", label=best[1])

    def _buy(self, screen: dict, cargo: dict[str, int]) -> Action | None:
        if _room(str(screen.get("ship") or ""), cargo) <= 0:
            return None
        best: tuple[int, str] | None = None
        for row in screen.get("rows") or []:
            button = str(row.get("button") or "")
            if not button.upper().startswith("BUY"):
                continue
            cells = [str(cell) for cell in (row.get("cells") or [])]
            name = next((good for good in _GOODS if cells and good.lower() in cells[0].lower()), "")
            if not name:
                continue
            price_at = 4 if len(cells) > 4 and str(cells[3]).endswith("%") else 3
            ask = _int(cells[price_at] if price_at < len(cells) else "")
            bid = self._known_bid(name)
            if bid <= ask or ask <= 0:
                continue
            spread = bid - ask
            if best is None or spread > best[0]:
                best = (spread, button)
        if best is None:
            return None
        self.plan_note = "buy " + best[1]
        return Action("click", label=best[1])

    def _stardock(self, screen: dict, labels: list[str], credits: int) -> Action | None:
        if credits < 500 or screen.get("formOpen"):
            return None
        if self.gear and self.gear.get("phase") != "select":
            return None
        if not self._gear_pending():
            return None
        label = next((row for row in labels if row.lower().startswith("stardock: buy gear")), "")
        if not label:
            # The button can sit out for one refresh after a purchase. Stay.
            if self._at_dock(screen) and self.dock_waits < 2:
                self.dock_waits += 1
                self.plan_note = "stay for gear"
                return Action("wait", ms=400)
            return None
        self.dock_waits = 0
        item = "fighters" if "holds" in self.bought else "holds"
        self.gear = {"item": item, "phase": "select", "qty": "1" if item == "holds" else "5"}
        self.plan_note = "open stardock"
        return Action("click", label=label)

    def _warp(self, screen: dict, sector: int, cargo: dict[str, int], *, flee: bool = False) -> Action | None:
        options: list[tuple[int, str]] = []
        for label in screen.get("warps") or []:
            match = _WARP.match(str(label).strip())
            if match is None:
                continue
            dest = int(match.group(1))
            if dest in self.danger and not (flee and dest != sector):
                continue
            if dest in self.danger:
                continue
            options.append((dest, str(label).strip()))
        if not options and flee:
            for label in screen.get("warps") or []:
                match = _WARP.match(str(label).strip())
                if match is None:
                    continue
                dest = int(match.group(1))
                if dest != sector:
                    options.append((dest, str(label).strip()))
        if not options:
            return None

        def score(item: tuple[int, str]) -> int:
            dest = item[0]
            value = 0
            if dest == self.previous:
                value -= 5
            if dest not in self.visited:
                value += 2
            info = self.ports.get(dest) or {}
            code = self.codes.get(dest, "")
            for index, (name, qty) in enumerate(cargo.items()):
                slot = info.get(name) or {}
                if qty and isinstance(slot, dict) and slot.get("bid"):
                    value += 8
                elif qty and index < len(code) and code[index] == "B":
                    value += 4
            if not any(cargo.values()):
                for name, slot in info.items():
                    if not isinstance(slot, dict) or slot.get("ask") is None:
                        continue
                    if self._known_bid(name) > int(slot["ask"]):
                        value += 6
            return value

        _dest, label = max(options, key=score)
        if not flee:
            self.plan_note = "warp " + label
        return Action("click", label=label)

    def _spend(self, screen: dict, turns: int) -> Action:
        chip = str(screen.get("chip") or "")
        if "NO TURNS" in chip or "GAME OVER" in chip or turns <= 0:
            self.plan_note = "wait for the day"
            return Action("wait", ms=500)
        self.plan_note = "spend a turn"
        return Action("press", key=".")
