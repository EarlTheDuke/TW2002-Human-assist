# hold-fighter-shield-price-v1

2026-10-11. `SHOP_PRICE_MODE` stays `legacy`.

Live prices the next hold at `550 + 20 * (holds - 20)`. At 20 holds that is 550. At 19 holds it is 530. The slope is the same below 20. The daily base that runs from 151 to 249 stays on the off path. Day 1 of that path is 562 at 20 holds.

Fighters and shields stay on the 160-239 wave. The live screen showed fighters 188 and shields 161 on day 1, then 190 and 159 on day 2. Those two days are not a replacement for the 87-day wave, so this switch does not move them.

Tier S on b8e1c42: four tests pass, planted bugs failed the 550 hold and the two-hold total and were restored, the bank pin stayed 9b607d3dae940c0b1a69f6d7, and the 10-day games stayed 24863a3d and 98a47c8a with rejected 0/0.
