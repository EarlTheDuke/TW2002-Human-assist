# Lobby AI opponents (NOTE 100)

Match setup for Galaxy War Command. Not a game rule. No v3.11 helper. Rows 143-144 are held for NOTE 101.

## Switch

`LOBBY_AI_SEAT_MODE` in `src/tw2k/engine/constants.py` is stored `"off"`. `lobby_ai_seat_on()` is true only when that value is `"on"`. `V311_PROFILE` does not turn it on, and the helper is not in `V311_PROFILE_HELPERS`.

The lobby process also reads the environment variable `LOBBY_AI_SEAT_MODE`. `on` or `off` replaces the constant for that process. Any other value is ignored, so an empty variable leaves the stored default.

With the switch off, the new-game form does not offer AI seats, the parser rejects `ai_opponents`, `ai_brain`, `ai_key`, and `ai_endpoint` as unknown fields, and the worker command is the same command it builds today.

With the switch on, the form adds 0-4 AI opponents next to the code-bot count. One brain choice applies to every AI seat in that game: Heuristic (free), the default, or LLM (your key).

## Seats

AI seats are external seats. They sit after the human seats (`P1`… then the AI seats, then the code bots). The lobby holds their harness tokens and runs the NOTE 95 cockpit seat over the four routes (`reference`, `status`, `observation`, `events`) and `action`. The seat is not given the universe. Code bots stay engine heuristic agents. AI seats are not join links.

Their trader name is `AI (heuristic)` or `AI (LLM)`. Rankings, the end screen, and the cockpit trader list already print that name. The lobby card and the created page print the same label. The day clock and the seat timer are the ones every external seat already uses. The cockpit client waits out HTTP 429.

`run(..., lobby=True)` is allowed only while this switch is on. It does not turn `AI_COCKPIT_SEAT_MODE` on. A lobby seat passes its key as an argument. An empty key does not read `TW2K_COCKPIT_LLM_KEY`.

## Keys

Bring your own key. The server never pays for a model and never ships a key.

The creator pastes an API key and an http or https endpoint. Both stay in process memory on the lobby, keyed by game id. They are not written to sqlite settings, saves, tokens, logs, events, the spectator feed, error pages, or the admin page. A log line is `key ****` plus the last four characters. After submit, neither value is put back into HTML or JSON. Validation errors do not echo them.

The memory entry is dropped when the game finishes, when the game is stopped, and when the lobby process stops. A restart therefore has no key. The seat plays the heuristic brain and posts one public broadcast: `Playing the heuristic brain. No key is on the server.` The cockpit already shows broadcast summaries. That is not a new Observation field.

The same fallback happens when the per-game call cap is hit or the endpoint errors. A minute that is already full skips that one call and tries again later. The cap is `LOBBY_AI_CALL_CAP` (400, UNVERIFIED hosting guard). The per-minute limit is `LOBBY_AI_CALLS_PER_MINUTE` (6, UNVERIFIED hosting guard).

The key is used only for that game's LLM seats. Heuristic seats do not call an endpoint.

## Pace estimate

The form shows an estimate of model calls per game day. Heuristic is 0. An LLM seat is one call per turn, times the number of LLM seats, times turns per day. UNVERIFIED: a refused turn that is chosen again can spend another call.

## Tests

Tests generate a key at runtime and point the seat at a local fake endpoint. No key is stored in the repo.
