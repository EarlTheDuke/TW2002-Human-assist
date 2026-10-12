# dashboard-spectator-controls-v1

A spectator link showed Pause, the speed buttons, and New Match. One click could pause or restart a live match.

When `TW2K_SPECTATOR_TOKEN` is set, those three controls are hidden and every `/control/*` route answers 403. The cockpit link and the help button stay. When the token is unset, the controls stay and pause still works, so local games are unchanged.

The engine pin is not on this path. Do not turn a live game's spectator token off to get the buttons back.
