# haggle-detail-v1

`HAGGLE_LIVE_MODE` stays `legacy`. The older haggle window is unchanged while this is off.

Live, a sale at or under +3% of the opening quote is taken. From there through +12% the port counters at +1% of the opening quote (the low end of the measured +0.2% to +3% band; the 745 to 754 example is that band, not a second formula). An offer at or under that counter is taken, and so is a later offer still inside +12%. Past +12% the trade ends with "Swine, go peddle your wares". At +37% it ends with "Get lost creep".

A buy at or above -12% is taken. From there through -23% the port counters at -4% (the middle of the measured -3% to -5%). Worse than -23% ends the trade. No buy-side insult was measured.

+13% to +16% on a sale, and -13% to -15% on a buy, were not measured. A sale in that gap ends, because the next measured sale outcome is an ended trade. A buy in that gap counters, because the next measured buy outcome is a counter.

A refused haggle ends the visit. The next trade costs a turn. A counter does not.

QC: five tests, plus the older haggle tests. pb1 dropped the +3% accept (the offer became a counter). pb2 left the visit open after a refusal. Both restored. Bank pin 9b607d3dae940c0b1a69f6d7. 10-day digests 24863a3d and 98a47c8a, rejected 0/0.
