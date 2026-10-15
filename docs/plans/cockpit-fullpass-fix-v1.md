# Cockpit full pass

Checked on 643b79d before this slice.

Already covered, left alone: day-1 port stock and the lumped trade sentence (NOTE 26), the landed planet panel, the waiting-key queue, the map trail, the phone warp row, and the plotted-course sentence (NOTE 25). The haggle counter itself is already `HAGGLE_LIVE_MODE` (default legacy). This slice only shows that counter and keeps the trade form open. No new engine flag, and no new observation key. `/bot` stays the old page.

The bank form is drawn in the cockpit from the balance, room, and max the seat already has, with deposit and withdraw. A blank trade price is left off the action so the engine uses the listed price, and the form prefills that price. A refusal starts with REFUSED or FAILED, drops the seat tag, and says the credit numbers in words. Computer R and K draw the known ports and known warps already on the seat. V and G draw the status and the fighters the seat can see. B, J, and Q in space ask for a confirm and say the game has no such command. A scan with more than one legal tier asks which one, and a holo scan adds the adjacent port prices the seat just learned. Wait writes its own line. At 1366 the top bar stays on one row.
