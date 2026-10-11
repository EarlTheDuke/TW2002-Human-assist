# discovery-exp-daily-bonus-v1

`DISCOVERY_EXP_MODE` stays `legacy`.

Off, the first trader at a port still gets one experience point, and the midnight point of experience and alignment still follows the rank switch for every living player.

On, each player gets one experience point the first time they trade at a port, including a port someone else has already used. A second trade at that port does not pay it again. The midnight point of experience and one alignment is paid only to a player who spent a turn that day. A player who spent none does not get it. The two points are not added on top of the rank switch; the live rule replaces that grant for the day.

QC: five tests. pb1 paid the discovery point only when nobody had traded there. pb2 paid the midnight point to a player who spent no turn. Both restored. Bank pin 9b607d3dae940c0b1a69f6d7. 10-day digests 24863a3d and 98a47c8a, rejected 0/0.
