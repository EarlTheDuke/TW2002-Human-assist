# cockpit-custom-layout-v1

COMMANDER NOTE 113. The redesign cockpit panels can be resized, shown, hidden, and rearranged, and the map can be made much larger. No engine change, so no new switch. `COCKPIT_LAYOUT` stays legacy unless the page is the redesign. `/bot` (`web/bot.html`, `web/bot.js`, `web/bot-parity.js`) is not edited.

Trade Wars 2002 is one text column. A classic client with draggable panels is unverified. This customizes the redesign deck that is already on screen.

## What was already there

NOTE 81 (pull request 18) saved the deck in this browser and added the font and zoom controls. Those controls are still the only font and zoom controls. This slice does not add another pair. The splitter drag and the arrow-key nudge on a focused splitter are unchanged. With nothing saved, the stylesheet grid is left alone.

## What this slice adds

Each panel has a Panel menu, and the Layout menu repeats the same items: Move up, Move down, Hide, and Show. The words stay put so a keyboard user or a computer-use player can find them. Move up and Move down swap grid slots on a wide screen. On a narrow screen they stay labeled and do nothing, because the stack order is the stylesheet's. Hide and Show work at every width. The last visible panel cannot be hidden. A hidden panel is shown again from the Layout menu, which stays in the header.

Larger map and Smaller map grow or shrink the nav panel. On a wide screen that adds weight to the map's column and row, up to four steps. On a narrow screen the same control raises the map's height, up to most of the screen. The existing Enlarge button still fills the screen. It is a separate control.

Reset layout deletes this browser's saved deck and clears the inline sizes, the font, the zoom, and the map step.

## Save

`localStorage` key `tw2k-deck-v1:<game>:<seat>`, the same key as NOTE 81. `<game>` is the `/g/<id>` path segment, or `lobby` on the harness. The value adds `mapBoost` (0 to 4) beside the order, hidden list, column weights, row weights, font, and zoom. Another seat in the same browser keeps its own layout. Reset removes the key.
