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
                                 id="post-economy">
                                <h1><a href="/post/economy"
                                       rel="bookmark"
                                       title="Economy">Economy</a></h1>
                                <div class="by">by <span class="author">System</span> on 2026-01-26 | Categories: Files&nbsp;
                                    <!--button class="toggle-visibility-btn"
                                            data-post-id="economy"
                                            title="Toggle visibility">
                                        👁️
                                    </button-->
                                </div>

                                <div class="post-content">
                                    <div id="post-content-economy"
                                         data-markdown># Economic Overview

## Turn Efficiency Theory

| Strategy               | Profit per Turn (credits) | Alignment Shift per Turn |
| ---------------------- | ------------------------- | ------------------------ |
| **SST (Solo, furbed)** | 14,035                    | –15                      |
| **Team SST (furbed)**  | 14,139                    | –15                      |
| **SDT (Solo, furbed)** | 15,921                    | –21.18                   |
| **Team SDT (furbed)**  | 17,271                    | –21.18                   |
| **Mega‑Rob**           | 39,728                    | N/A                      |

*Profits assume use of –65 MCIC ports and incorporate the average bust frequency of ≈ 1 in 50.*

---

## Red Cashing Methods

### Robbing and Stealing

When a Red player&#39;s alignment is **–100** or lower a new port‑menu option **R** (Rob) appears.

| Menu option | Description |
|-------------|-------------|
| `A` | Attack this port |
| `R` | **Rob** this port |
| `T` | Trade at this port |
| `Q` | Quit |

Selecting **R** opens a sub‑menu:

| Sub‑option | Action |
|------------|--------|
| `R` | **Rob** the port’s cash |
| `S` | **Steal** product from the dock |
| `Q` | Quit |

* **Robbing** extracts the port’s internal cash. The actual amount received equals the displayed amount **+ 11 %**.  
* **Stealing** extracts cargo that is physically **On Dock**.  

Experience‑based limits apply (see “Rob/Steal Settings” below). Bust chance for any rob/steal attempt is **≈ 1 in 50**.

#### Rob/Steal Settings

| Mode                     | Minimum experience to steal a full 250‑hold ship |
|--------------------------|---------------------------------------------------|
| **MBBS**                 | 5,251 exp                                          |
| **Gold / Classic**       | 7,501 exp                                          |

#### Example Port Inventory

| Commodity | Trade Action | On Dock | On‑Board |
|-----------|--------------|---------|----------|
| Fuel Ore  | Selling      | 2,550   | 100      |
| Organics  | Buying       | 2,010   | 0        |
| Equipment| Buying       | 2,640   | 0        |

*The example shows an SBB (class 2) port with &gt; 2 k units of each commodity on the dock.*

### Busting Penalties

| Action          | Penalty                                                                                     |
|-----------------|---------------------------------------------------------------------------------------------|
| **Rob bust**   | Lose 10 % of experience and holds equal to **1 %** of the credits attempted to rob.          |
| **Steal bust** | Lose 10 % of experience and holds equal to **9 %** of the equipment holds attempted to steal. |
| **Fake bust** (rob/steal same port twice consecutively) | Same base bust chance; each extra hold or each 1,000 credits above the experience limit increases bust odds exponentially. |

*Holds never drop below one; staying within experience‑based limits keeps bust chance at the base ≈ 1 in 50.*

---

## Red Money‑Making Tactics

### Sell‑Steal‑Move (**SSM**)

1. Locate an **evil pair** of ports (one sells Equipment, the other buys it).  
2. Upgrade the Equipment on the first port to match your ship’s hold capacity plus a safety margin.  
3. **Port** to the first port, **sell** any Equipment you carry.  
4. **Steal** the freshly upgraded Equipment.  
5. **Warp** to the second port and **sell** the stolen Equipment.  
6. **Steal** Equipment back from the second port.  
7. Repeat steps 3‑6 until a bust occurs.

*SSM provides a modest edge over basic paired‑port trading (PPT) and serves as a stepping‑stone to SST.*

### Sell‑Steal‑Transport (**SST**)

| Step | Action                                   | Turns |
|------|------------------------------------------|-------|
| 1    | Position two COLT ships (initial setup)  | – |
| 2    | Verify and upgrade port equipment as needed | 0 |
| 3    | **Port** and **Sell** Equipment (ship 1) | 1 |
| 4    | **Port** and **Steal** Equipment (ship 1) | 1 |
| 5    | **Transport** to ship 2 (planetary transporter) | 1 |
| 6    | Verify and upgrade second port equipment | 0 |
| 7    | **Port** and **Sell** Equipment (ship 2) | 1 |
| 8    | **Port** and **Steal** Equipment (ship 2) | 1 |
| 9    | **Transport** back to ship 1               | 1 |
| 10   | Repeat steps 2‑9 until busted            | – |
| **Total per cycle** |                              | **6** |

The cycle yields roughly **10 million credits per 1,000 turns**.

### Steal‑Dump‑Transport (**SDT**)

| Step | Action                                                   | Turns |
|------|----------------------------------------------------------|-------|
| 1    | Position COLTs and establish planets (if needed)         | – |
| 2    | Verify and upgrade port equipment                        | 0 |
| 3    | **Port** and **Steal** Equipment (ship 1)                | 1 |
| 4    | **Land** on a planet and **dump** Equipment               | 0 |
| 5    | **Transport** to ship 2                                   | 1 |
| 6    | Verify and upgrade second port equipment                  | 0 |
| 7    | **Port** and **Steal** Equipment (ship 2)                | 1 |
| 8    | **Land** on a planet and **dump** Equipment               | 0 |
| 9    | **Transport** back to ship 1                              | 1 |
|10‑14| Repeat steps 2‑9 (≈ 8 cycles typical)                    | 32 |
|15    | **Sell** Equipment at port 2 (usually a Blue ship handles) | 1 |
|16    | **Transport** to ship 1                                   | 1 |
|17    | **Sell** Equipment at port 1                              | 1 |
| **Total for 8 cycles** |                                    | **35** |

Average turns per cycle ≈ 4.375, faster than SST.

### Rob‑Transport‑Rob (**RTR**)

| Cycle step | Action                               | Turns |
|------------|--------------------------------------|-------|
| 1          | **Rob** port A                        | 1 |
| 2          | **Transport** to ship 2 (planetary transporter) | 1 |
| 3          | **Rob** port B                        | 1 |
| 4          | **Transport** back to ship 1           | 1 |
| **Total**  |                                      | **4** |

Profit is limited by the cash available on the ports and the experience‑based rob limit.

### Steal‑Dump‑Flee (**SDF**)

| Step | Action | Turns |
|------|--------|-------|
| 1    | Position COLTs, place planets, and station a non‑corp fighter | – |
| 2    | Verify and upgrade port equipment | 0 |
| 3    | **Port** and **Steal** Equipment | 1 |
| 4    | **Land** on planet and **dump** Equipment | 0 |
| 5    | Non‑corp attacks with 1 fighter (triggers flee) | 0 |
| 6    | **Flee** to second sector (0 or 1 turn) | 0 or 1 |
| 7‑11| Repeat steps 2‑6 for the second port | – |
| 12   | **Sell** Equipment at port 2 (usually a Blue) | 0 |
| 13   | Non‑corp attacks again (maintains flee) | 0 |
| 14   | **Flee** back to first sector (0 or 1 turn) | 0 or 1 |
| 15   | **Sell** Equipment at port 1 | 0 |
| **Total for 8 cycles** | | **24 average** |

Average cycle ≈ 3 turns (including any flee penalties), roughly twice the profitability of SST.

### Megga‑Rob (**MR**) – MBBS Only

| Step | Action | Turns |
|------|--------|-------|
| 1    | Upgrade **Buy** port (max equipment, optional organics/fuel) | – |
| 2    | Upgrade **Sell** port (max equipment, partial organics/fuel) | – |
| 3    | Move mobile planet under **Buy** port | 0 |
| 4    | **Buy‑down** equipment until ≥ 3.3 million credits spent (reverse haggle) | 131 or more |
| 5    | **Port** and **Rob** the cash spent back | 1 |
| 6    | Move mobile planet under **Sell** port | 0 |
| 7    | **Port** and **Negotiate** sale of equipment | 1 |
| 8    | Move to next XSS port and repeat | – |
| **Total Turns** | | **≥ 133** |

Effective turn cost ≈ 1.01 turn per cycle when executed optimally.

### Buy‑Dump‑Rob‑Transport‑Rob (**D/RTR**) – “Poor man’s Megga‑Rob”

| Requirement | Details |
|-------------|---------|
| Ports | Two **SXS** ports within 5 sectors (maximum transport distance for a **Merf**) |
| Upgrades | ≈ 2.5 k fuel ore and 5‑10 k equipment on each port |
| Ships | Typically a **COLT**, a **Havoc**, and optionally a **Merf** |
| Procedure | 1️⃣ **Buy‑dump** all fuel and equipment at first port (best‑price haggle).&lt;br&gt;2️⃣ Warp to second port, repeat **buy‑dump**.&lt;br&gt;3️⃣ Park ships under each port and execute **RTR** cycle.&lt;br&gt;4️⃣ **Sell** equipment at an **XXB** port. |

Average turn cost ≈ 1.2 turns per cycle (≈ 20 k exp minimum recommended).

---

## Planet Farming for Cash

Class (O) **Oceanic** planets provide the highest cash flow:

| Planet Class | Peak Daily Production (FOE) | Maximum Daily Org at 50 % population | Approx. Daily Credit Profit* |
|--------------|------------------------------|--------------------------------------|------------------------------|
| O (Oceanic)  | Fuel Ore 5,000 | Organics 50,000 | 2.2 – 2.5 million credits (ports limited to 65,530 units) |
| M (Earth)    | Fuel Ore 5,000 | Organics 2,142 | 0.1 – 0.15 million credits (equipment) |
| L (Mountainous) | Fuel Ore 10,000 | Organics 4,000 | Comparable to O for fuel‑heavy strategies |
| H (Volcanic) | Fuel Ore 50,000 | Organics 0 | Excellent fuel source, but citadel build time is long (≈ 2.5 weeks to level 3, &gt; 7 weeks to level 6). |

\*Profit assumes ports purchase at the 50 % bell‑curve optimum and that the port’s daily intake limit is not exceeded.

**Key points**

* Oceanic planets reach peak production at **100,000 colonists**, delivering **50,000** organics per day.
* A port can accept at most **65,530** units per day; selling at the 50 % price point yields the highest revenue.
* Fuel‑rich Class H planets are ideal for defensive fuel reserves but are slow to develop citadels.

---

## Planet Farming for Fighters

Fighter output is a fraction of daily FOE production. The “2 produce 1” column on the Planet menu shows the number of colonists required for one fighter at the current production level.

| Planet Class | Fuel Ratio | “2 produce 1” at optimal population | Fighters per day (example) |
|--------------|------------|--------------------------------------|-----------------------------|
| M (Earth)    | 3/7/13     | 30 colonists                         | 50 fighters per day (with 1,500 colonists on Fuel) |
| L (Mountainous) | 2/5/20   | 24 colonists                         | 1,666 fighters per day (with 20,000 colonists) |
| O (Oceanic)  | 20/2/100   | 15 colonists (n/15)                  | &gt; 5,000 fighters per day at full colonization |
| C (Glacial)  | 50/100/500| 25 colonists (n/25)                  | 64 fighters per day (max) |
| H (Volcanic) | 1/–/500    | 50 colonists (n/50)                  | 1,002 fighters per day (max) |
| U (Vaporous) | –/–/–      | —                                    | 0 fighters (no production) |

Higher fighter output is achieved by allocating colonists to the **Fuel** production line on planets with favorable ratios (L and O classes).  

---

## Colonizing &amp; Transport Mechanics

### Fast Colonization Loop

1. **Buy** fuel at a nearby port and **drop** it on the target planet.  
2. **TransWarp** to Terra, acquire colonists, and **TransWarp** back.  
3. **Land** on the planet and **dump** the fuel; the planet consumes 10 fuel per sector per transporter jump.  
4. Repeat until the planet reaches Citadel Level 1.

*Using a ship with a TransWarp drive (e.g., **Imperial StarShip** or **Corporate Flagship**) dramatically reduces turn cost compared with manual movement.*

### Planetary Transporter System

- **First hop cost:** 50,000 credits (paid from ship’s cash, not the planetary Treasury).  
- **Each additional hop:** 25,000 credits.  
- **Fuel consumption:** 10 units of Fuel Ore per sector jumped.  
- **Turn cost:** 1 turn per use, regardless of distance.  

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