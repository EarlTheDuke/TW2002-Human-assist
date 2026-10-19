# Live TWGS test queue

Items whose numbers are not settled by a v3.11 source. Run each one on Ben's server with a new test character. Record the screen text. The constant column is what a later slice may set.

| item | current value | what to do | what to record | constant |
|---|---|---|---|---|
| Port rating and barrage, classes 0-5 and 7-9 | unset. Class 6 stays rating 98, barrage 598 | Attack one port of each class with a ship that can survive a return shot. Read the defensive rating before the shot | The rating, the return-shot number, the fighters you sent, whether the port was destroyed, and the port's size or productivity on that same screen | `PORT_DEFENSE_RATING`, `PORT_LASER_BARRAGE` |
| Port fighters from the port's size | no formula | On that same attack, note anything the screen calls the port's fighters or firepower | The words and the numbers, next to the port's productivity | a new constant, only if the screen prints a formula or a fighter count |
| Class 0 and StarDock blow | the cabal 22 formula is not used | Blow one Class 0 port and StarDock only if the game can spare them. The cabal rule of thumb is about 248,000 fighters and 32,000 shields on an Interdictor the first time | Fighters sent, shields lost, the rating before and after, and whether the other special ports' ratings rose | `PORT_DEFENSE_RATING` for classes 0 and 9 |
| Port capture | not implemented. A blown port stays in the sector | After a destroy, try to claim or capture the port | Whether any command captures a port, or the only result is the destroyed port | none until a screen shows a capture |
| Alien kill alignment share | `ALIEN_KILL_ALIGN_SHARE` 0.5, subtracted from the alien's alignment. Experience is already half if opposite and a quarter if the same | Kill one alien of the other alignment and one of the same alignment. Note your alignment before and after, and the alien's alignment and experience | The alignment change next to the alien's alignment and its experience, so the half-experience reading can be kept or dropped | `ALIEN_KILL_ALIGN_SHARE` |
