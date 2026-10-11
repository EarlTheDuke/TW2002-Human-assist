# offline-turn-regen-v1

`TURN_REGEN_MODE` stays `legacy`. A new day still refills every turn.

On, spent turns come back over 24 hours, in proportion to that player's daily cap. A cap of 240 returns 10 turns in one hour. A cap of 250 returns about 10. The count never goes past the cap. A new day does not refill what is still spent.

A 50,000 cap would return 1,041 turns in half an hour at this rate. The live note of 194 turns in about half an hour does not match that, and no second rate was measured, so 194 is not used.

QC: five tests. pb1 left the spent turns in place. pb2 refilled them at the new day. Both restored. Bank pin 9b607d3dae940c0b1a69f6d7. 10-day digests 24863a3d and 98a47c8a, rejected 0/0.
