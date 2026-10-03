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
                                 id="post-planets">
                                <h1><a href="/post/planets"
                                       rel="bookmark"
                                       title="Planets">Planets</a></h1>
                                <div class="by">by <span class="author">System</span> on 2026-01-25 | Categories: Files&nbsp;
                                    <!--button class="toggle-visibility-btn"
                                            data-post-id="planets"
                                            title="Toggle visibility">
                                        👁️
                                    </button-->
                                </div>

                                <div class="post-content">
                                    <div id="post-content-planets"
                                         data-markdown># Planetary Mechanics

## Planet Types &amp; Descriptions
**Class M – Earth Type**  
Thick Oxygen/Nitrogen atmosphere, gravity 0.7‑1.3 g. Fertile soil, good for Organics and Equipment, chemical elements favor Fuel Ore. Population grows well; over‑population can cause unrest.

**Class K – Desert Wasteland**  
Thin atmosphere, gravity 0.5‑1.5 g. Hot, dry climate; excellent Fuel Ore, very poor Organics and Equipment. Requires specialized colonists; higher fatality rate.

**Class O – Oceanic**  
Dense atmosphere, gravity 1.1‑1.8 g. No land mass; excellent Organics, poor Equipment, moderate Fuel Ore. Entire surface habitable with proper gear.

**Class L – Mountainous**  
Thin atmosphere, gravity 1.0‑2.2 g. Wet climate; excellent Fuel Ore and Organics, limited Equipment. Requires colonist specialization.

**Class C – Glacial**  
Extremely thin atmosphere, gravity 0.5‑1.7 g. Violent weather; low Organics, modest Fuel Ore and Equipment. Often used as prison colonies.

**Class H – Volcanic**  
Extremely thin atmosphere, gravity 0.8‑2.6 g. Very hot, no soil; no Organics, excellent Fuel Ore, modest Equipment. High risk of colony loss.

**Class U – Vaporous/Gaseous**  
Heavy to very thin atmosphere of helium/hydrogen, gravity 0.2‑8.0 g. Production impossible; only thin‑air colonies survive.

## Production Statistics

| Class | Fuel Ratio | Org Ratio | Eq Ratio | Max Colonists | Max Daily Fuel | Max Daily Org | Max Daily Eq | Max Fuel Planet | Max Org Planet | Max Eq Planet | Fighter Formula |
|-------|------------|-----------|----------|----------------|----------------|----------------|--------------|-----------------|----------------|----------------|-----------------|
| M (Earth) | 3   | 7   | 13 | 30,000 | 5,000 | 2,142 | 1,153 | 100,000 | 100,000 | 100,000 | n/10 |
| K (Desert) | 2   | 100 | 500 | 40,000 | 10,000 | 200   | 40   | 200,000 | 50,000  | 10,000  | n/15 |
| O (Oceanic) | 20  | 2   | 100 | 200,000| 5,000 | 50,000| 1,000| 100,000 | 1,000,000| 50,000 | n/15 |
| L (Mountain) | 2   | 5   | 20  | 40,000 | 10,000| 4,000 | 1,000| 200,000 | 200,000 | 200,000| n/12 |
| C (Glacial) | 50  | 100 | 500 | 100,000| 1,000 | 500   | 100  | 20,000  | 50,000  | 10,000 | n/25 |
| H (Volcanic) | 1   | –   | 500 | 100,000| 50,000| 0     | 100  | 1,000,000| 10,000 | 100,000| n/50 |
| U (Vap/Gas) | –   | –   | –   | 3,000   | 0     | 0     | 0    | 10,000  | 10,000  | 10,000 | — |

*Maximum daily production occurs at **50 %** of the maximum colonist count.*  
**Fighter Formula** expresses the number of colonists required to generate one fighter (e.g., **n/10** means 10 colonists → 1 fighter).

### Fig Factor Definition
The *Fig Factor* is the number of colonists needed to produce one fighter for each commodity type. It is derived directly from the “n/ x” values in the *Fighter Formula* column.

## Citadel Advancement Requirements
Citadel levels progress from 0 (no defenses) to 6 (Interdictor Generator). The tables list total colonists, required product amounts, and turn cost for each level. Values correspond to default settings (Gold extensions disabled).

### Class M – Earth Type

| Level | Total Colonists | Fuel (F/O) | Org (Org) | Eq (Equ) | Days |
|-------|-----------------|-----------|-----------|----------|------|
| 1 | 1,000 | 300 | 200 | 250 | 4 |
| 2 | 2,000 | 200 | 50  | 250 | 4 |
| 3 | 4,000 | 500 | 250 | 500 | 5 |
| 4 | 6,000 | 1,000 | 1,200 | 1,000 | 10 |
| 5 | 6,000 | 300 | 400 | 1,000 | 5 |
| 6 | 6,000 | 1,000 | 1,200 | 2,000 | 15 |

### Class K – Desert Wasteland

| Level | Total Colonists | Fuel (F/O) | Org (Org) | Eq (Equ) | Days |
|-------|-----------------|-----------|-----------|----------|------|
| 1 | 1,000 | 400 | 300 | 600 | 6 |
| 2 | 2,400 | 300 | 80  | 400 | 5 |
| 3 | 4,400 | 600 | 400 | 650 | 8 |
| 4 | 7,000 | 700 | 900 | 800 | 5 |
| 5 | 8,000 | 800 | 400 | 1,000 | 4 |
| 6 | 7,000 | 700 | 900 | 1,600 | 8 |

### Class O – Oceanic

| Level | Total Colonists | Fuel (F/O) | Org (Org) | Eq (Equ) | Days |
|-------|-----------------|-----------|-----------|----------|------|
| 1 | 1,400 | 500 | 200 | 400 | 6 |
| 2 | 2,400 | 200 | 50  | 300 | 5 |
| 3 | 4,400 | 600 | 400 | 650 | 8 |
| 4 | 7,000 | 700 | 900 | 800 | 5 |
| 5 | 8,000 | 300 | 400 | 1,000 | 4 |
| 6 | 7,000 | 700 | 900 | 1,600 | 8 |

### Class L – Mountainous

| Level | Total Colonists | Fuel (F/O) | Org (Org) | Eq (Equ) | Days |
|-------|-----------------|-----------|-----------|----------|------|
| 1 | 400  | 150 | 100 | 150 | 2 |
| 2 | 1,400| 200 | 50  | 250 | 5 |
| 3 | 3,600| 600 | 250 | 700 | 5 |
| 4 | 5,600| 1,000| 1,200| 1,000| 8 |
| 5 | 7,000| 300 | 400 | 1,000| 5 |
| 6 | 5,600| 1,000| 1,200| 2,000| 12 |

### Class C – Glacial

| Level | Total Colonists | Fuel (F/O) | Org (Org) | Eq (Equ) | Days |
|-------|-----------------|-----------|-----------|----------|------|
| 1 | 1,000 | 400 | 300 | 600 | 5 |
| 2 | 2,400 | 300 | 80  | 400 | 5 |
| 3 | 4,400 | 600 | 400 | 650 | 7 |
| 4 | 6,600 | 700 | 900 | 700 | 5 |
| 5 | 9,000 | 300 | 400 | 1,000| 4 |
| 6 | 6,600 | 700 | 900 | 1,400| 8 |

### Class H – Volcanic

| Level | Total Colonists | Fuel (F/O) | Org (Org) | Eq (Equ) | Days |
|-------|-----------------|-----------|-----------|----------|------|
| 1 | 800  | 500 | 300 | 600 | 4 |
| 2 | 1,600| 300 | 100 | 400 | 5 |
| 3 | 4,400| 1,200| 400 | 1,500| 8 |
| 4 | 7,000| 2,000| 2,000| 2,500|12 |
| 5 |10,000| 3,000| 1,200| 2,000| 5 |
| 6 | 7,000| 2,000| 2,000| 5,000|18 |

### Class U – Vaporous/Gaseous

| Level | Total Colonists | Fuel (F/O) | Org (Org) | Eq (Equ) | Days |
|-------|-----------------|-----------|-----------|----------|------|
| 1 | 3,000 | 1,200 | 400 | 2,500 | 8 |
| 2 | 3,000 | 300   | 100 | 400   | 4 |
| 3 | 8,000 | 500   | 500 | 2,000 | 5 |
| 4 | 6,000 | 500   | 200 | 600   | 5 |
| 5 | 8,000 | 200   | 200 | 600   | 4 |
| 6 | 6,000 | 500   | 200 | 1,200 | 8 |

&gt; **Note:** Citadel construction proceeds sequentially; each level builds on the previous one and adds the listed defenses.

## Fighter Production Formula
*(The source material does not define an additional formula beyond the “n/ x” values already presented in the production tables.)*

## Base Discovery

**Key Concepts**

- **Zero‑Turn Mapping (ZTM)** – Perform a comprehensive ZTM on day 1 to acquire an accurate map of all warps.
- **Dead‑End Identification** – Extract sectors with no outgoing warps from the ZTM; these are the most likely base locations.
- **Ether Probes** – Deploy ether probes to each dead end. Record which probes are destroyed; add those sectors to an *avoid list* and re‑probe after updating the list.
- **Avoid List Sharing** – Exchange avoid lists with allies to prevent redundant probe loss.
- **CIM Port Scan** – After probing, run a CIM script to capture visible ports for later reference.

**Typical Discovery Workflow**

1. Execute a full ZTM on the first turn.  
2. Generate a list of dead‑end sectors (`dead_ends.txt`).  
3. Within 3–4 days, send ether probes to every sector in `dead_ends.txt`.  
4. For each destroyed probe, add the sector to `avoid.txt` and re‑probe the target dead end.  
5. If a probe cannot find a path within **X** hops, log the sector for manual inspection later.  
6. Once all dead ends are probed, optionally probe all remaining unexplored sectors if credits allow.  
7. Run a CIM script to save the current port visibility (`ports_snapshot.txt`).  

**Macro for Automated Fighter Clearing**

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