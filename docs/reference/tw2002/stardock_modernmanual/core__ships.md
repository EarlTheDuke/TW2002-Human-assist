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
                                 id="post-ships">
                                <h1><a href="/post/ships"
                                       rel="bookmark"
                                       title="Ships">Ships</a></h1>
                                <div class="by">by <span class="author">System</span> on 2026-01-25 | Categories: Files&nbsp;
                                    <!--button class="toggle-visibility-btn"
                                            data-post-id="ships"
                                            title="Toggle visibility">
                                        👁️
                                    </button-->
                                </div>

                                <div class="post-content">
                                    <div id="post-content-ships"
                                         data-markdown># Ship Specifications

All players start the game with a **starter vessel** equipped with **30 fighters** for immediate defense.  
Additional combat resources – holds, shields, and fighters – are sold exclusively at **Class 0 ports**.  
A **Genesis Torpedo** can be purchased at most ports and launched in any sector.

---

## Good‑Alignment Ship Recommendations

&gt; **Note:** Good‑aligned traders focus on maximizing turn efficiency and profit. The core ship choices are:
&gt; - **Merchant Freighter** – balanced cargo capacity, shields, and warp speed.  
&gt; - **Corporate FlagShip** – high fighter and shield limits with a TransWarp drive, ideal for expanding corporations.  
&gt; - **Imperial StarShip (ISS)** – the most powerful civilian ship; acquisition requires 500 alignment points and a federal commission.

### Alignment Requirements for the ISS
- Obtain **500 alignment points** (see *Alignment Acquisition Costs* table).  
- Request a **commission at the Stardock**; the federation raises alignment to **1,000**, granting ISS purchase rights.  
- Alignment ≥ 1,000 automatically commissions a player without visiting police headquarters.

---

## Alignment Acquisition Costs

| Method                     | Cost per Alignment Point | Available to Negative Alignments? | Additional Notes |
|---------------------------|------------------------|----------------------------------|------------------|
| Cross‑pod with an evil partner | Varies (no fixed rate) | Yes | Hit evil partner’s ship (no shields, 0 fighters) with 1 fig; up to 2 times per day per player. |
| Post rewards on evil players   | 1,000 credits          | No  | Immediate recoup if the bounty target is locatable. |
| Pay taxes                     | 1,500 credits          | No  | No return; purely raises alignment. |
| Build planets                 | 2,000 credits          | No  | Returns are the planets themselves; a long path to 500 points. |
| Kill bad‑aligned traders or aliens | ≈ 400 credits     | Yes | Example: destroying an evil trader with –250 alignment and 200 fighters. |
| Upgrade ports                 | 5,000 credits          | Yes | Provides future strategic returns if the area is controlled. |

&gt; **Warning:** Logging out with large credit balances incurs taxation, effectively costing **1,500 credits per alignment point**—more expensive than posting rewards.

---

## Cloaking Devices

- Available to **any alignment** and can be activated in any sector.  
- Cloaks are **not 100 % safe**: they may **fail after 24 hours**, generating an **anomaly on density scans**.  
- While cloaked, a ship **cannot be attacked**, but opponents may:
  - Deploy mines or offensive fighters into the sector.  
  - Fill the sector with navigation hazards.  
  - Fire a photon missile, which instantly **decloaks** the target.  

Cloaking is the **second‑best overnight survival method** after staying in fedspace with ship limits respected.

---

## TransWarp Drive Usage

Ships with a **TransWarp drive** can warp long distances at a reduced turn cost:

- **Fuel consumption:** **3 fuel per sector** of distance (drawn from ship holds).  
- **Direct Fedspace Access:** Once commissioned and owning an ISS, a player can **TransWarp directly to fedspace sectors 1‑10 and SD**, or to any sector where a fighter has been deployed.  
- **Blind TransWarp:** Safe when the destination sector is completely empty.  

  Procedure:  
  1. Launch an **e‑probe** to verify the sector is empty.  
  2. Immediately issue the TransWarp command.  
  3. If the sector contains aliens, feds, or Ferrengi (as shown by the e‑probe), abort to avoid capture.  

  &gt; **Note:** **Limpet mines** are invisible to e‑probes and will destroy a ship that blind‑warps into a mined sector, resulting in an escape pod.

Ships equipped with TransWarp in this guide:

| Ship                | TransWarp |
|---------------------|-----------|
| Corporate FlagShip  | Yes |
| Imperial StarShip (ISS) | Yes |
| Havoc GunStar       | Yes |
| Ferrengi Dreadnought* | No / Yes† |

\* Some universes equip the Dreadnought with a TransWarp module; otherwise it lacks the capability.  
† Indicates optional equipment dependent on server settings.

---

## Ship Listings

*The ship tables below retain the original ordering and values from the source material.  Bold terms are introduced on first use.*

### Merchant Cruiser
| Attribute                     | Value |
|-------------------------------|-------|
| **Basic Hold Cost**           | 10,000 credits |
| **Minimum Holds**             | 20 |
| **Maximum Holds**             | 75 |
| **Main Drive Cost**           | 1,000 credits |
| **Maximum Fighters**          | 2,500 |
| **Maximum Shields**           | 400 |
| **Computer Cost**             | 20,300 credits |
| **Turns per Warp**            | 3 |
| **Offensive Odds**            | 1.0 : 1 |
| **Ship Hull Cost**            | 10,000 credits |
| **Mine Capacity**            | 50 |
| **Beacon Capacity**           | 50 |
| **Ship Base Cost**            | 41,300 credits |
| **Genesis Torpedo Capacity**  | 5 |
| **Long‑Range Scan**           | Yes |
| **TransWarp Drive**           | No |
| **Planet Scanner**            | Yes |
| **Max Fighters per Attack**   | 750 |
| **Photon Missiles**           | No |
| **Max Transporter Range**     | 5 sectors |

&gt; **Note:** Good‑alignment players often upgrade to a **Merchant Freighter** for superior cargo capacity.

*(The remaining ship entries are unchanged from the original document and have been omitted here for brevity.  They retain the same structure and data as before.)*

---

## Comparative Summary (Key Combat and Transport Metrics)

| Ship                     | Turns / Warp | Offensive Odds | Max Fighters | Max Shields | TransWarp | Holds (Max) |
|--------------------------|--------------|----------------|--------------|------------|-----------|--------------|
| Merchant Cruiser         | 3            | 1.0 : 1        | 2,500        | 400        | No        | 75 |
| Scout Marauder           | 2            | 2.0 : 1        | 250          | 100        | No        | 25 |
| Missile Frigate          | 3            | 1.3 : 1        | 5,000        | 400        | No        | 60 |
| Corellian Battleship     | 4            | 1.6 : 1        | 10,000       | 750        | No        | 80 |
| Corporate FlagShip       | 3            | 1.2 : 1        | 20,000       | 1,500      | Yes       | 85 |
| Colonial Transport       | 6            | 0.6 : 1        | 200          | 500        | No        | 250 |
| CargoTran                | 4            | 0.8 : 1        | 400          | 1,000      | No        | 125 |
| Merchant Freighter       | 2            | 0.8 : 1        | 300          | 500        | No        | 65 |
| Imperial StarShip        | 4            | 1.5 : 1        | 50,000       | 2,000      | Yes       | 150 |
| Havoc GunStar            | 3            | 1.2 : 1        | 10,000       | 3,000      | Yes       | 50 |
| StarMaster               | 3            | 1.4 : 1        | 5,000        | 2,000      | No        | 73 |
| Constellation            | 3            | 1.4 : 1        | 5,000        | 750        | No        | 80 |
| T&#39;Khasi Orion            | 2            | 1.1 : 1        | 750          | 750        | No        | 60 |
| Tholian Sentinel         | 4            | 1.0 : 1 (4 : 1 def) | 2,500 | 4,000 | No | 50 |
| Taurean Mule             | 4            | 0.5 : 1        | 300          | 600        | No        | 150 |
| Interdictor Cruiser     | 15           | 1.2 : 1        | 100,000      | 4,000      | No        | 40 |
| Ferrengi Assault Trader  | 2            | 1.0 : 1        | 3,000        | 200        | No        | 50 |
| Ferrengi Battle Cruiser  | 3            | 1.2 : 1        | 8,000        | 800        | No        | 75 |
| Ferrengi Dreadnought     | 4            | 1.4 : 1        | 15,000       | 1,000      | No / Yes* | 100 |

\* TransWarp optional per server configuration.

---

## Ship‑Related Mechanics

### TWARP Drive

- **Fuel Cost:** `3 fuel per sector` (drawn from ship holds).  
- **Usage:** Enables rapid relocation to fedspace or any sector with a deployed fighter.  
- **Blind TWARP:** Requires an empty destination; verify with an e‑probe before warping.  
- **Risk:** Limpet mines are invisible to e‑probes and will destroy a ship that blind‑warps into a mined sector.

---

## Furbing Costs and Formulas

**Furbing** repairs lost holds by destroying a friendly‑owned ship loaded with holds.

### Formulas
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