# hold-endpoint-rules-v1

`POST /hold` keeps a seat's slot, or ends it without spending a turn. A normal action ends the slot even when it spends 0 turns. `accepted: true` only means the move was queued. `ok` means the engine applied it. `rejected` means the engine refused it.

`HOLD_RULES_MODE` defaults to `legacy`. The prompt, the action hint, and the action answer stay as they are, so the pin and the scripted games stay put.

`live` adds that sentence to the system prompt, the action hint, and the `wording` field on `POST /action` and `POST /hold`. The engine does not change.

Do not turn the switch on until Ben says so.
