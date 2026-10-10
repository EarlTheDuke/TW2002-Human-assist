# port-open-full-v1

Live TWGS Big Bang opens ports at 100% of max and puts about 5% of that max back each day. Game 5 saw ports at about 3-500 units against a max around 3,000-4,000, because the clone opens at 0%.

`PORT_OPEN_STOCK_MODE` is `"legacy"` or `"full"`. Legacy is the default, so existing games and the pin stay as they are.

- legacy: opening stock is `maximum * PORT_START_STOCK_PERCENT` (0). Each day adds `round(productivity * 0.05)`.
- full: opening stock is the maximum. Each day adds `round(maximum * 0.05)`, and stock never goes past the maximum.

The old 35-95% random draw is still taken and thrown away, so the rest of the map does not shift.

Deliberate: the flag is off. Turning it on is a Ben choice, because it changes every trade on day 1. Nothing else about prices moved in this slice.
