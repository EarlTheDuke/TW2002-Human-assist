<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">
    <title>The Stardock - TradeWars 2002 Archives</title>
    <meta name="description"
          content="TradeWars 2002 Game Server hosting and community">

    <!-- Open Graph Meta Tags for Facebook Sharing -->
    <meta property="og:title"
          content="The Stardock - TradeWars 2002 Archives">
    <meta property="og:type"
          content="website">
    <meta property="og:image"
          content="/static/img/stardock_logo.png">
    <meta property="og:url"
          content="https://www.thestardock.com">
    <meta property="og:description"
          content="TradeWars 2002 Game Server hosting and community">
    <meta property="og:site_name"
          content="The Stardock">

    <link rel="stylesheet"
          href="/static/css/style.css"
          type="text/css"
          media="screen">
    <link rel="icon"
          href="/static/favicon.ico"
          type="image/x-icon">

    <script src="/static/js/marked.min.js"></script>
    <!-- Load highlight.js for syntax highlighting -->
    <link rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"></script>
</head>

<body>
    <div id="wrap">
        <div id="container">
            <div id="navigator">
                <ul>
                    <li class="home"><a href="/"
                           title="Home">Home</a></li>
                    <li class="page_item page-item-2"><a href="/about">About</a></li>
                    <li class="home"><a href="/files">Files</a></li>
                    <li class="home"><a href="/files/Site%20Caps/">Website Archives</a></li>
                </ul>
            </div>

            <div id="body-content">
                <div id="content">
                    <div id="header">
                        <pre id="stardock-logo"
                             class="stardusk"
                             data-category=""></pre>
                        
                        
                    </div>

                    <div id="post-entry">
                        <div id="post">
                            
                            <div class="post-meta"
                                 id="post-combat">
                                <h1><a href="/post/combat"
                                       rel="bookmark"
                                       title="Combat">Combat</a></h1>
                                <div class="by">by <span class="author">System</span> on 2026-01-25 | Categories: Files&nbsp;
                                    <!--button class="toggle-visibility-btn"
                                            data-post-id="combat"
                                            title="Toggle visibility">
                                        👁️
                                    </button-->
                                </div>

                                <div class="post-content">
                                    <div id="post-content-combat"
                                         data-markdown>## Combat Overview

Combat follows a deterministic sequence that does not depend on cargo, turn order, or ship class.

### Attack Sequence (General)

1. **Empty ships** – Appear at the bottom of the sector display but attack first.  
2. **Player ships** – Attack in the order players first signed on to the sector.  
3. **Fighters** – Handled according to the *Fighter Accounting* rules (see below).  

&gt; Note: Turn consumption, cargo load, or ship type do not affect this order.

---

## Entering a Hostile Sector – Order of Events (No Photon)

1. Nav Hazard check – apply any navigation‑hazard damage.  
2. Limpet Mine attachment – a single Limpet Mine attaches to the hull (replacing any previously attached Limpet).  
3. Armid Mine detonation – each Armid Mine detonates with a 50 % chance (rounded down).  
4. **Sector Q‑Cannon fire** – planets fire in numerical order; if the ship is destroyed, subsequent cannons do not fire.  
5. Fighter encounter – one of three scenarios:  

   * **Sector Offensive Fighters** – attack at **1:1** odds, sending `1.25 × (max shields + max figs)` fighters.  
   * **Sector Defensive Fighters** – challenge at **1:1** odds; the player may *attack*, *retreat*, or *surrender*.  
   * **Tolled Fighters** – act as a toll; the player may *pay* 5 credits per fighter or fight at **1:1** odds.  

6. Post‑combat mine prompt – if mines remain, the game asks whether to avoid the sector; the prompt returns to the command line regardless of the answer.

---

## Landing on a Hostile Planet – Order of Events (No Photon)

1. **Atmospheric Q‑Cannon** fires (if the planet has one).  
2. Ship attacks planetary shields.  
3. **Second atmospheric Q‑Cannon** fire – occurs only after shields are destroyed.  
4. **Planetary Offensive Fighters** – fire at **2:1** odds, sending `1.25 × (max shields + max figs)` fighters (only when no shields remain).  
5. **Planetary Defensive Fighters** – fire at **3:1** odds after offensive figs are resolved.  
6. Ownership prompt – press **O** to claim the planet after all fighters are cleared.  

&gt; **Warning:** Planetary shields must be reduced below **200 planetary shields** (equivalent to 2,000 ship shields) before photons become effective.

---

## Fighter Accounting

| Source of Fighters                     | Counted in `V` Screen |
|---------------------------------------|------------------------|
| Sector fighters (ships that carry fighters) | Yes |
| Player‑owned planet fighters          | Yes |
| Fighters on a ship docked on a planet | Yes |
| Fighters on empty ships               | No |

---

## Combat Odds Table

| Context                | Odds |
|------------------------|------|
| Tolled Fig             | 1:1 |
| Defensive Fig          | 1:1 |
| Offensive Fig*         | 1:1 |
| Planet Defensive Fig   | 3:1 |
| Planet Offensive Fig** | 2:1 |
| Planet Shield          | 20:1 |

*Version 0.55* offensive figs calculate the number required to destroy the ship using **max** shields + figs, then send `1.25 × that amount`. If the ship’s odds are **1:1.3** or better, it survives.  

**\***Planet Offensive figs also send `1.25 × required figs` but use **2:1** odds; without a photon the ship is podded unless its odds are ≥ 1:1.3.

---

## Q‑Cannon Damage Formulas

### MBBS (and Classic Gold) Q‑Cannon

| Situation   | Formula                                   |
|-------------|-------------------------------------------|
| Sector      | `Damage = (TotalOre * SectPct) / 3`        |
| Atmospheric| `Damage = TotalOre * AtmoPct * 2`          |

### Classic (Gold) Q‑Cannon

| Situation   | Formula                                   |
|-------------|-------------------------------------------|
| Sector      | `Damage = (TotalOre * SectPct) / 3`        |
| Atmospheric| `Damage = TotalOre * AtmoPct * 0.5`        |

*Variables*  
- `TotalOre` – total Fuel ore present on the planet.  
- `SectPct` – sector‑fire percentage setting (0‑100).  
- `AtmoPct` – atmospheric‑fire percentage setting (0‑100).

**Example (Class H Volcanic planet, 200,000 Fuel, 20 % atmospheric, 10 % sector):**  

- Sector damage: `(200,000 * 10) / 3 = 6,666` points.  
- Atmospheric damage (MBBS): `200,000 * 20 * 2 = 72,000` points.  
- Atmospheric damage (Classic): `200,000 * 20 * 0.5 = 2,000` points.

---

## Sector Quasar Cannon Damage – Ore‑After‑Blast Calculations

</div>
                                </div>
                            </div>
                            <div class="clear-fix"></div>
                            

                            
                        </div>

                        <div id="sidebar">
                            <!-- Sidebar will be loaded dynamically via JavaScript -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="/static/js/app.js"></script>
    <script src="/static/js/stars.js"></script>
</body>

</html>