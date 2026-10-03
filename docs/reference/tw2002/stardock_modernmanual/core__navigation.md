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
                                 id="post-navigation">
                                <h1><a href="/post/navigation"
                                       rel="bookmark"
                                       title="Navigation">Navigation</a></h1>
                                <div class="by">by <span class="author">System</span> on 2026-01-25 | Categories: Files&nbsp;
                                    <!--button class="toggle-visibility-btn"
                                            data-post-id="navigation"
                                            title="Toggle visibility">
                                        👁️
                                    </button-->
                                </div>

                                <div class="post-content">
                                    <div id="post-content-navigation"
                                         data-markdown>## Navigation and Movement

### Topology Overview
The universe is composed of **sectors** linked by warp routes that form distinct topological structures.

| Feature | Minimum Size | Typical Size Range | Key Characteristics |
|---------|--------------|--------------------|-----------------------|
| **Bubble** | 100 sectors | Varies with universe size and GameOp settings | A large, contiguous region with limited ingress/egress points. All tunnels inside a bubble return to a single entry sector. |
| **Tunnel** | 1 sector (dead‑end) | Up to 20+ sectors | A linear chain of sectors with exactly two consecutive warps (2‑warp chain). The entrance sector is called the **mouth**; exits may be one‑way (back doors) that allow leaving but not re‑entering. |
| **Dead‑End** | 1 sector | — | No outward ports; often used for concealed planet placement. |

&gt; **Note:** When Gold extensions are enabled, the GameOp can disable the automatic bubble flag and manually create multiple bubbles, breaking a large universe into smaller, isolated regions.

#### Tunnel Verification
To ensure a tunnel is safe for hidden base construction:

1. Mark the tunnel’s entrance sector as an **avoid** sector using the Computer menu.  
2. Use the Computer’s **[F]ind Route** function to plot a course **into** the tunnel.  
3. If the computer cannot find an alternate path, the tunnel is **verified** (no hidden entrances).  
4. Repeat the verification from several external sectors to rule out rare routing anomalies in games with short maximum course lengths.

### Major Space Lanes (MSL) Summary
The MSL network serves as the low‑risk backbone for inter‑sector travel. All lanes reside in Fedspace except the **Sol ↔ Stardock** segment, which passes through the MBBS zone.

| Lane                     | Endpoint A                     | Endpoint B                     |
|--------------------------|--------------------------------|--------------------------------|
| Sol ↔ Stardock           | Sector 1 (SOL)                 | Stardock (Fedspace)            |
| Stardock ↔ Rylos         | Stardock                       | Rylos (MSL)                    |
| Stardock ↔ Alpha Centauri| Stardock                       | Alpha Centauri (MSL)           |
| Rylos ↔ Alpha Centauri   | Rylos (MSL)                    | Alpha Centauri (MSL)           |
| Rylos ↔ Sol              | Rylos (MSL)                    | Sector 1 (SOL)                 |
| Alpha Centauri ↔ Sol     | Alpha Centauri (MSL)           | Sector 1 (SOL)                 |

### Backdoor Sectors
Backdoor sectors provide a **one‑way warp** into **Class 0 ports** (Alpha Centauri and Rylos), the safest Fedspace locations for good‑aligned traders.

| Characteristic | Detail |
|----------------|--------|
| **Entry**          | Single warp from a non‑Class 0 sector into the Class 0 port |
| **Exits from port**| Six outward warps |
| **Inbound warps**  | Seven or more inbound warps |
| **Practical use**  | Move into Fedspace without traversing high‑risk Stardock sectors |

### Overnight Fedspace Survival
Good‑aligned players can remain in Fedspace overnight with minimal risk if two limits are observed:

| Limit | Threshold |
|-------|------------|
| **Ships per Fedspace sector** | Must not exceed the value shown on the V‑screen; exceeding triggers an automatic tow during the Extern cleanup. |
| **Fighters aboard a ship** | 99 fighters or more forces a tow. |

&gt; **Warning:** Continuously monitor the V‑screen for the current ship‑per‑sector limit and keep fighter counts below 99.

### Blind Warp Mechanics
A **blind warp** is a warp to a sector without prior confirmation that the sector is empty.

- **Success condition:** Destination sector contains **no ships, fighters, mines, limpet mines, or anomalies**.  
- **Failure condition:** Presence of any object triggers **Atomic Fusion**; the ship is destroyed and the player reappears in a pod in the origin sector.

*Limpet mines are invisible on holoscans or E‑PROBE scans, and other players may move into the destination after the warp command is issued, increasing the hazard.*

### Blind TWARP Procedure
Safe execution of a blind TWARP requires a quick probe check.

1. Deploy an **E‑probe** to the target sector.  
2. Verify that the probe reports **no ships, fighters, mines, or anomalies**.  
3. Issue the `TWARP` command **immediately** after receiving the probe response.  

If any hidden object is detected, abort the warp; the player pods in the origin sector.

### TWARP Drive
The **TWARP** drive enables sector‑to‑sector jumps within a ship’s warp range.

| Item   | Purchase Cost | Fuel Consumption per sector |
|--------|----------------|----------------------------|
| TWARP 1| 50,000 credits (Stardock Hardware Emporium) | 3 fuel units |
| TWARP 2*| 40,000 credits after TWARP 1 (or 80,000 credits if bought together) | 3 fuel units |
| *TWARP 2 adds TWARP‑Tow capability. |

#### Safety Rules
1. A TWARP is safe if the destination sector contains **at least one of your own personal or corporate fighters**, **or** if the sector is **completely empty**.  
2. If **any object** occupies the destination sector **and you have no fighter present**, the ship fuses and you appear in a pod in the origin sector.  
3. **Blind TWARPs** (without fighter presence or probe verification) are not recommended because hidden limpets and other players can cause fusion.

### Photon Torpedoes (GTORPs) and Sector Overload
GTORPs can be used to disable sector defenses and subsequently overload a sector.

- **Sector overload:** Any sector **except sector 1** can be overloaded by repeatedly firing GTORPs.  
- **Effect:** Photons disable sector defenses, allowing continued GTORP fire without first destroying those defenses.  
- **Result:** Overloading can destroy a high‑level planet with relatively low expense.  
- **Additional effect:** Firing a photon into a sector where a player is **in a citadel** forces the player’s remaining turns to drop to 0 (turns regenerate at the top of the hour). Photons also force cloaked traders to **decloak**, exposing them to attack.

### Limpet Mines
Limpet mines attach to any ship that enters the sector where they are deployed.

| Property               | Detail |
|------------------------|--------|
| **Attachment**             | Ships entering a sector with limpets automatically acquire them (if not already present). |
| **Removal fee**            | SD removes limpets for **5,000 credits** (ownership unknown). |
| **Trade‑in impact**        | Attached limpets **reduce the ship’s trade‑in value**. |
| **Detection**              | Appear as an **anomaly** with a density reading of **2** per mine. |
| **Disruption**             | Mine disrupters **cannot** remove deployed limpets. |
| **Clearing method**        | Repeatedly entering and leaving the sector eventually clears limpets from the ship. |
| **Deployment restriction** | Limpet mines **cannot be deployed in Fedspace** and are removed from Major Space Lanes. |
| **Interaction limit**      | If any limpets (or armid mines) already occupy a sector, you cannot deploy additional limpets or armid mines there. |

### Cloaking Devices
Cloaking devices hide a ship from standard scans but are subject to a configurable failure rate.

| Attribute | Detail |
|-----------|--------|
| **Failure rate** | Sysop‑configurable; if set above 0 % a cloak can fail twice (once during Extern cleanup and once during combat). |
| **Zero‑percent setting** | When the failure rate is **0 %**, cloaking never fails; this setting is not displayed on the V‑screen. |
| **Combat interaction** | A cloaked ship cannot be directly attacked, but it appears as an **anomaly** on density scans. |
| **Decloaking** | Firing a **photon** into the sector decloaks the ship. Limpet mines also generate anomalies; attempting to lay a mine where a cloaked ship is present fails unless a visible mine already exists. |

### Zero‑Turn Actions (ZTM) for Stardock Discovery
`ZTM` (Zero‑Turn Movement) lists sectors based on warp connectivity without consuming a turn.

1. Issue `ZTM` from any sector.  
2. Identify sectors that have **6 outward warps and 7 or more inbound warps**.  
3. Stardock will be among those sectors.

&gt; **Note:** ZTM does not guarantee Stardock’s identity; cross‑reference sector numbers with known Stardock locations.

### Base Discovery and Invasion

#### Finding a Base
Early‑game base detection relies on **ZTM**, **ether probes**, and **avoid lists**.

| Step | Action |
|------|--------|
| 1 | Perform a **complete ZTM** on day 1 to identify all sectors with **6 outward / 7+ inbound warps** (potential dead‑ends). |
| 2 | Compile a list of these **dead‑end sectors**. |
| 3 | Send **ether probes** to each dead‑end. Record sectors where the probe is destroyed and mark them with **avoid** entries. |
| 4 | Re‑probe any avoided sector after 1‑2 turns; if a path appears within *x* hops, remove the avoid. |
| 5 | For remaining unexplored dead‑ends, use a **macro** to clear enemy fighters before probing: `m&lt;sector&gt;**any9999**fz1*zcd^m` (where `*` denotes an Enter). |
| 6 | Drop **at least one fighter** in every sector traversed during probe runs; this blocks opponents from probing the same path and expands your own fighter network. |
| 7 | Prioritize sectors with **few inbound warps** (e.g., 2‑warp‑in over 5‑warp‑in) when expanding the search beyond dead‑ends. |
| 8 | Continuously run a **CIM script** to capture visible ports; ports that become **blocked** often indicate a newly built enemy base. |

#### Invasion Methods
Three core methods exist for denying an opponent the use of a discovered base.

| Method | Description | Typical Cost | Reliability |
|--------|-------------|--------------|-------------|
| **Direct Planet Capture** | Enter the sector, land on and claim each level 0‑1 planet after neutralizing shields and cannons. | High (fighters, fuel, possible photon usage) | Highest – guarantees ownership of captured planets. |
| **Extern Collision** | Overpopulate the sector with planets **above the maximum limit** and wait for the **extern** run. Each planet beyond the limit has a **10 %** collision chance; ten excess planets guarantee a collision. | Moderate (planet building, transport) | Variable – depends on luck and opponent’s warp‑ability. |
| **Blockade with Fighters/Planets** | Station personal or corporate fighters, or place shielded planets, to prevent the opponent from entering the sector. | Moderate (fighters, planet construction) | Risky – opponent may break the block if they possess sufficient resources. |

#### Sector Quasar Cannon Damage
When a sector’s planets are **shielded**, their atmospheric cannons fire during entry attempts. Damage is calculated as:

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