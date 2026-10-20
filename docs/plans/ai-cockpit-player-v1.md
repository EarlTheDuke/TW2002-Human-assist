# AI cockpit player (NOTE 128)

An AI seat that plays Galaxy War Command the way a person does. It opens a normal cockpit link, looks at the rendered page, and uses the same buttons and keys. It does not import the engine, call the harness, or read state that is not on the screen.

The seat link is the one a person uses:

```
/g/<game>/bot?seat=Pn&mode=cu&token=...&layout=redesign
```

`layout=redesign` asks for the redesign cockpit even when `COCKPIT_LAYOUT` is unset. `/bot` (the legacy page, `web/bot.html`, `web/bot.js`, `web/bot-parity.js`) is unchanged.

## Runner

```
python3 scripts/ai_cockpit_player.py \
  --url 'http://127.0.0.1:8050/bot?seat=P2&mode=cu&token=...&layout=redesign' \
  --provider scripted \
  --max-turns 40 \
  --min-interval 1 \
  --stop-file runs/ai-cockpit/STOP \
  --run-dir runs/ai-cockpit
```

Each step:

1. Wait until the chip says YOUR MOVE, NO TURNS, or GAME OVER.
2. Save a screenshot and the page's visible text under the run folder (`screen-NNN.png`, `text-NNN.txt`).
3. Ask the provider for one action: click a visible label or selector, type text, press a key, or wait.
4. Do that action.

The first action from the scripted provider is the header Manual link, which opens the in-game player manual in a new tab. The runner saves that page as `text-manual.txt` and `screen-manual.png`, then goes back to the cockpit. Live providers are told to do the same before they trade.

The loop stops when the chip says GAME OVER, the stop file exists, or `--max-turns` actions have been taken. `--min-interval` is the minimum seconds between actions. A stop file that already exists skips the browser.

`modules.txt` in the run folder lists any `tw2k` modules the process loaded. A clean run leaves it empty.

## Providers

| `--provider` | Key variable | Default model variable |
| --- | --- | --- |
| `scripted` | none | rule-based trader, offline |
| `mock` | none | replays a JSON list from `--mock-script` |
| `grok` (alias `xai`) | `XAI_API_KEY` | `XAI_MODEL` (default `grok-4`) |
| `openai` | `OPENAI_API_KEY` | `OPENAI_MODEL` (default `gpt-4o`) |
| `anthropic` | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` (default `claude-sonnet-4-5`) |

`--level` selects a scripted difficulty. Easy wanders for a few sectors, including along a one-way, then keeps the thinnest one-hop pair it has seen and does not buy gear at StarDock. Normal locks a pair worth about 700 credits in a day, or any paying pair after eight priced ports, and buys holds and fighters only. Hard locks that same pair. It opens the course plotter when StarDock was never linked, and it follows that course or buys a ship only when the extra the ports can fill, over the days left, beats the turns the trip spends and the quote plus its trade-in. Otherwise it keeps trading the same way normal does, and it does not fly the same course back into fighters. A live provider ignores the level. The default is hard.

When the Comms panel is on the page, the scripted trader reads the turn log there. A hail or a corporation memo addressed to the seat is answered with the same Kind, Trader, Message, and Send controls a person uses. The reply is one of a few short in-character lines, at most 155 characters, and it does not repeat the incoming text. The message body is not treated as an instruction. Outgoing lines wait 2 seconds apart, and the seat stops after 3 sends so it cannot spam. After several quiet looks, and only when the Corporation choice is available, it sends one memo about its plan. A live provider with an empty key does not call the model: the runner logs the variable name and uses this same scripted trader.

The scripted trader reads the manual, then plays from the screen text. It records the sector, the port prices and quantities, the directed warps, and the holds. It keeps to unvisited lanes until a short pair, reachable from the current sector, can earn about 2,000 credits in a day from the stock on screen. It does not lock the first thin route, and it does not take a one-way warp until the return leg has already been on screen. It sells into the best reachable bid and buys the load with the best credits per turn, declining a counter that loses to a better reachable bid. A refused haggle is left. If the next lap does not fit, it parks on the buying port. On the last day, a handful of leftover turns that cannot finish a seen pair are waits, then the day-end confirm. On the opening visit to StarDock, and again once a paying route is known, it buys holds when the spread covers the price, then fighters and shields, and it compares shipyard deals the same way. Surplus credits go to the bank. A planet is claimed only when its per-day production beats the port pair; otherwise the ship lifts off. Sectors whose text showed Ferrengi, deployed mines, or hostile fighters are not warped back into. The StarDock gear list names Armid, Limpet, and Atomic mines; that catalog is not a threat. It keeps acting while the chip says YOUR MOVE, confirms a day-end dialog, waits on NO TURNS for the next day, and stops when the chip says GAME OVER.

On the day after a pair first pays, and from day 3 in a priced pocket that still has no known way to StarDock, hard and normal open the on-screen computer, press F for the course plotter, and type the destination. Hard then reads the hop count. It follows the course, including a one-way, only when more holds over the days left can earn back the turns the round trip spends. A course that cannot pay is cancelled and the ship stays on its route. At the yard, hard buys a ship only when the extra the ports on screen can fill, over the days left, beats the quote plus its trade-in credit and the turns to get home. A hull the route cannot load is declined, and hard does not cross the map to ask again. After that it hauls only between the two ports of its best one-hop pair. Normal still follows the course and stops after holds and fighters. That is the same plot the cockpit draws for a person. The player does not call the route API itself. After the shop, the same plotter is used to get back when the return leg was never seen. A day-end confirm still closes over the computer menu.

`--provider mock` reads a JSON list of canned replies and runs each one through the same system prompt, user prompt, and on-screen validation as a live model. A reply that is not a visible action is fed back into the next prompt. No key is read.

A 10-day bench seats the scripted commander with three heuristic code bots (universe 200, 40 turns a day, Ferrengi on, no gifted fuel) on seeds 250925 and 4242. Rank is by net worth. Day 1 is the opening board. The day 11 line is the board after day 10.

Seed 250925, Commander:

| Day | Before NW | Rank | After NW | Rank |
| --- | --- | --- | --- | --- |
| 1 | 72,601 | 1 | 72,601 | 1 |
| 2 | 71,524 | 4 | 72,601 | 1 |
| 3 | 71,608 | 4 | 72,601 | 2 |
| 4 | 73,795 | 1 | 73,961 | 1 |
| 5 | 75,258 | 1 | 75,301 | 1 |
| 6 | 76,554 | 1 | 71,611 | 3 |
| 7 | 77,663 | 1 | 73,183 | 3 |
| 8 | 78,543 | 1 | 73,865 | 2 |
| 9 | 73,896 | 2 | 75,493 | 1 |
| 10 | 74,694 | 3 | 76,439 | 2 |
| 11 | 74,961 | 2 | 81,411 | 1 |

Finish, seed 250925: Commander 81,411, H3 78,454, H1 74,466, H2 70,607.

Seed 4242, Commander:

| Day | Before NW | Rank | After NW | Rank |
| --- | --- | --- | --- | --- |
| 1 | 72,601 | 1 | 72,601 | 1 |
| 2 | 72,601 | 1 | 72,601 | 1 |
| 3 | 70,576 | 4 | 73,369 | 1 |
| 4 | 69,883 | 4 | 74,141 | 2 |
| 5 | 70,209 | 4 | 75,501 | 2 |
| 6 | 69,889 | 4 | 76,561 | 1 |
| 7 | 70,673 | 4 | 77,481 | 1 |
| 8 | 70,849 | 4 | 78,021 | 1 |
| 9 | 70,897 | 4 | 78,501 | 1 |
| 10 | 70,785 | 4 | 78,921 | 1 |
| 11 | 70,481 | 4 | 79,281 | 1 |

Finish, seed 4242: Commander 79,281, H2 77,823, H1 75,967, H3 72,864.

NOTE 140 runs the same bench once for each scripted level. Day 11 is the board after day 10. Easy stops after a short look and a thin pair, so it finishes behind both other seats. Normal and hard lock the same paying pair. Hard buys a ship only when the ports on screen can fill the extra holds and the days left earn back the quote plus the trade-in; on these seeds it keeps the cruiser and keeps trading. Hard is ahead of normal on 250925 and tied with normal on 4242 and on seed 99.

| Level | Seed | Rank | Net worth | Finish board |
| --- | --- | --- | --- | --- |
| easy | 250925 | 3 | 72,301 | H3 78,534, H1 74,466, Commander 72,301, H2 70,607 |
| easy | 4242 | 4 | 72,061 | H2 77,823, H1 75,960, H3 72,864, Commander 72,061 |
| easy | 99 | 4 | 72,601 | H2 79,507, H1 74,655, H3 73,449, Commander 72,601 |
| normal | 250925 | 1 | 79,914 | Commander 79,914, H3 77,234, H1 74,486, H2 70,607 |
| normal | 4242 | 1 | 102,721 | Commander 102,721, H2 77,763, H1 75,980, H3 72,844 |
| normal | 99 | 1 | 115,710 | Commander 115,710, H2 79,507, H1 74,655, H3 73,299 |
| hard | 250925 | 1 | 87,906 | Commander 87,906, H3 77,234, H1 74,486, H2 70,607 |
| hard | 4242 | 1 | 102,721 | Commander 102,721, H2 77,763, H1 75,980, H3 72,844 |
| hard | 99 | 1 | 115,710 | Commander 115,710, H2 79,507, H1 74,655, H3 73,299 |

NOTE 149 reads the same cockpit. A Ferrengi ship, hostile fighters, aliens, or mines on the sector screen send the ship back, and a sector named that way is not entered again. Once a pair is good enough to run, a thinner restock does not open an unseen sector. That is the seed 7 path: normal and hard used to die in Ferrengal on day 1, and they now stay on the pair the port screen already showed. The legacy gear list has no density scanner, so normal and hard buy one ether probe. Hard trades a second pair when the best ask on screen is empty, and it does not sail to StarDock for holds that ask cannot fill. Hard finishes strictly ahead of normal on 250925, 4242, and 7, and tied with normal on 99. Hard stays at or above normal, and both stay above easy, on every seed.

| Level | Seed | Rank | Net worth | Finish board |
| --- | --- | --- | --- | --- |
| easy | 250925 | 3 | 72,301 | H3 78,534, H1 74,466, Commander 72,301, H2 70,607 |
| easy | 4242 | 4 | 72,061 | H2 77,823, H1 75,960, H3 72,864, Commander 72,061 |
| easy | 99 | 4 | 72,601 | H2 79,507, H1 74,655, H3 73,449, Commander 72,601 |
| easy | 7 | 2 | 72,601 | H1 75,160, Commander 72,601, H3 22,605, H2 20,490 |
| normal | 250925 | 1 | 78,693 | Commander 78,693, H3 77,234, H1 74,486, H2 70,607 |
| normal | 4242 | 1 | 99,915 | Commander 99,915, H2 77,783, H1 75,980, H3 72,864 |
| normal | 99 | 1 | 115,710 | Commander 115,710, H2 79,507, H1 74,655, H3 73,299 |
| normal | 7 | 2 | 73,859 | H1 75,160, Commander 73,859, H3 22,630, H2 20,290 |
| hard | 250925 | 1 | 81,914 | Commander 81,914, H3 77,234, H1 74,486, H2 70,607 |
| hard | 4242 | 1 | 102,721 | Commander 102,721, H2 77,763, H1 75,980, H3 72,844 |
| hard | 99 | 1 | 115,710 | Commander 115,710, H2 79,507, H1 74,655, H3 73,299 |
| hard | 7 | 2 | 74,238 | H1 75,160, Commander 74,238, H3 22,605, H2 20,490 |

Keys are read from the environment at call time. They are not written into source, the run log, `actions.jsonl`, or screenshots' text sidecars. Logs replace key values, `sk-...`, `xai-...`, bearer tokens, and `token=` query values with `[redacted]`.

A live provider's system prompt is the trading playbook plus the manual text captured from the seat page. Each call also gets a short memory of the last few screens and actions. A reply that is not a click, type, press, or wait on a control that is on the screen is rejected and asked again, up to two retries, and then the runner waits. Each reply's token counts are priced with the same USD-per-million table as `src/tw2k/engine/llm_pricing.py` (curated 2026-04-22; the player keeps its own copy and does not import that module). The run log gains a line:

```
cost provider=grok model=grok-4 input_tokens=120 output_tokens=40 usd=0.000960
```

## How Ben adds a key later

Pick one provider and export its variable in the shell that starts the player. Do not put the key in a file in this repo, in the lobby database, or in a command that gets committed.

```
export XAI_API_KEY='...'          # or OPENAI_API_KEY, or ANTHROPIC_API_KEY
export XAI_MODEL='grok-4'         # optional
python3 scripts/ai_cockpit_player.py \
  --provider grok \
  --url "$SEAT_URL" \
  --max-turns 40 \
  --min-interval 1 \
  --run-dir runs/ai-cockpit
```

The lobby does not store the key. A live provider that finds an empty variable stops with a message that names the variable and does not echo a key.

## Lobby seat

`AI_COCKPIT_SEAT_MODE` already exists. The stored value stays `legacy`. `ai_cockpit_seat_on()` is true when that value is `tw2002` or when `TW2002_LIVE_PROFILE` is `live`. `V311_PROFILE` does not turn it on, and the helper is not in `V311_PROFILE_HELPERS`.

While the switch is legacy, the new-game form has no AI cockpit seat control, and `ai_cockpit`, `ai_cockpit_provider`, `ai_cockpit_model`, `ai_cockpit_count`, and `ai_cockpit_level` are unknown fields. While it is on, the Players section offers **AI cockpit seat**, a count from 1 to 4, a difficulty (easy, normal, hard), a provider (scripted, Grok, OpenAI, Anthropic), and a model name. The form does not ask for a key. `settings()` stores the provider, the model, the count, and the level only when the box is checked. A missing count is one seat. The default level is hard.

`start_game` adds those external seats after the human seats and any harness AI seats. The harness driver does not receive them. After the worker is healthy, the lobby starts one `scripts/ai_cockpit_player.py` per seat, each with its own token, run directory, and `--level`, against the worker's `/bot?seat=Pn&mode=cu&token=...&layout=redesign` link. The log line is `ai cockpit player seat=Pn provider=... model=... level=...`. It does not include the token.

The created page and the lobby row show one status line per seat (`AI cockpit seat: scripted hard, running`, or with the seat id when there are several) plus **Open** and a creator **Stop** button. Stop terminates that one process. **Watch** is the spectator. The single-seat **AI seat** link goes to `/games/<id>/ai-seat`, which redirects the creator to the seat page. The token is not written into the lobby HTML.

The runner reloads the original seat link if the page closes or the chip disappears, presses Escape when a click is swallowed by a dialog, and exits 0 when the chip says GAME OVER. A stop file still ends the run. `Lobby.launch_browser_seat(...)` still returns None while the switch is legacy.

## Tests

`tests/test_ai_cockpit_player_v1.py` runs the scripted provider against a `CuHost` on a port from `free_port`. That is an open pocket, or an OS ephemeral port that `allowed_test_port` accepts, outside 8031-8119 and 8120-8249. One game lasts three days and must finish with a higher net worth than it started. The same file checks the source has no `tw2k` import, the player process loads no `tw2k` module, a run that has keys in its environment does not write those keys or the seat token into the text log, and the new-game control is missing while the switch is legacy. Easy must buy a weak local offer and then take a one-way. Normal must settle on a pair hard still walks past, and must not buy shields. Hard must open the computer, plot sector 1, and take the hop the course names. Two cockpit seats must launch two processes, and the stop control must name a path with no token.
