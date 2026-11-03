# hold-endpoint-rules-v1

`POST /hold` keeps a seat's slot, or ends it without spending a turn. A normal action ends the slot even when it spends 0 turns. `accepted: true` only means the move was queued. `ok` means the engine applied it. `rejected` means the engine refused it.

`HOLD_RULES_MODE` defaults to `legacy`. The prompt, the action hint, and the action answer stay as they are, so the pin and the scripted games stay put.

`live` adds that sentence to the system prompt, the action hint, and the `wording` field on `POST /action` and `POST /hold`. The engine does not change.

Do not turn the switch on until Ben says so.

Tier L on ecd000f: two tests pass, planted bugs failed the legacy and live tests and were restored, the bank pin stayed 9b607d3dae940c0b1a69f6d7, and the 10-day games stayed 24863a3d and 98a47c8a with rejected 0/0. The engine path did not change. The full suite and the 30-day games wait for the end of Batch A.
