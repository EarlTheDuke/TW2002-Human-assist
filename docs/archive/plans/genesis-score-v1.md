# genesis-score-v1

Game 5 scored a brand-new genesis planet at about 308,000 credits. A class U planet's level-1 goods are 1,200 fuel, 400 organics, and 2,500 equipment. At the tw2002 bases that is 1,200*26 + 400*56 + 2,500*102 = 308,600. The torpedo creates those goods, and the score treats them as if the player had earned them. Spamming planets wins a day-cap game.

`GENESIS_SCORE_MODE` is `"legacy"` or `"fair"`. Legacy is the default, so existing scores and the pin stay as they are.

fair: while the planet came from genesis and the citadel is still level 0, the seeded level-1 goods do not add to net worth. Colonists still count. Goods produced above the seed still count. Once the citadel is level 1, the goods count again (the citadel spent them, or what remains is new stock).

Deliberate: the flag is off. Turning it on changes who wins a day-cap game, so Ben chooses that.

Suite on 381dbd4: 2474 passed, 3 failed, 1 skipped, 2920s. Two failures are the known flakes (WinError 10048 and the spectator-feed timeout). The third was the cockpit turn-timer test, a browser timeout, and it passed alone in 8s. The five new tests passed. The fair-mode hide was re-broken and restored.
