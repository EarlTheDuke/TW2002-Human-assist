# fedspace-deploy-v1

Dropping fighters in FedSpace is refused today. On the live server the drop is annihilated by a Federation starship. The ship loses 10 percent of its fighters and 10 percent of its holds. A half rounds up. The measured ships went from 30 fighters to 27, from 20 fighters to 18, and from 35 holds to 31. The fighters you tried to drop do not stay in the sector, and they are not taken off the ship on top of that 10 percent. Alignment does not change.

`FEDSPACE_DEPLOY_MODE` defaults to `legacy`. The drop is still refused, so the pin and the scripted digests stay put.

`live` annihilates the drop and takes that 10 percent. If the new hold count is smaller than the cargo, cargo is trimmed until it fits. The measured ship was empty, so that trim order was not on the screen. The live screen did not show a turn count. This copy spends the same turn a normal drop spends.

Do not turn the switch on until Ben says so.

Suite on 7fc31e6: 2503 passed, 2 failed, 1 skipped, 3097s. Both failures are the known flakes. Three new tests passed. pb1 and pb2 re-broken and restored. With the flag off, 10-day seed 250925 digest 24863a3d and seed 4242 digest 98a47c8a, rejected 0/0, same as e0c1ad5. 30-day seed 250925 digest 86a15277, N1 one engine reject. 30-day seed 4242 digest b274e3d1, rejected 0/0.
