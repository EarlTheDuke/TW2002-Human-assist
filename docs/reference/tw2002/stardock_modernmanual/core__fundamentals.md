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
                                 id="post-fundamentals">
                                <h1><a href="/post/fundamentals"
                                       rel="bookmark"
                                       title="Fundamentals">Fundamentals</a></h1>
                                <div class="by">by <span class="author">System</span> on 2026-01-25 | Categories: Files&nbsp;
                                    <!--button class="toggle-visibility-btn"
                                            data-post-id="fundamentals"
                                            title="Toggle visibility">
                                        👁️
                                    </button-->
                                </div>

                                <div class="post-content">
                                    <div id="post-content-fundamentals"
                                         data-markdown>## Universe Overview

The galaxy consists of numbered **sectors**. A sector may contain any combination of the following entities:

- Planets  
- Ports  
- Other players  
- Empty ships  
- Aliens (Ferrengi, Federation Starships, etc.)  
- Mines  
- Message beacons  
- Fighters (your own, other players’, rogue mercenaries’, or Ferrengi‑controlled)

## Starting Ship and Defenses

- Every new player begins with a ship that carries **30 fighters**.  
- These fighters are available immediately for defense.

## Alignment, Ranks, and Commission

**Alignment points** determine a player’s standing with the Federation and unlock advanced assets.

| Rank | Title                | Experience Required |
|------|----------------------|----------------------|
| 1    | Private              | 2                    |
| 2    | Private 1st Class    | 4                    |
| 3    | Lance Corporal       | 8                    |
| 4    | Corporal             | 16                   |
| 5    | Sergeant             | 32                   |
| 6    | Staff Sergeant       | 64                   |
| 7    | Gunnery Sergeant     | 128                  |
| 8    | 1st Sergeant         | 256                  |
| 9    | Sergeant Major       | 512                  |
| 10   | Warrant Officer      | 1,024                |
| 11   | Chief Warrant Officer| 2,048                |
| 12   | Ensign               | 4,096                |
| 13   | Lieutenant J.G.      | 8,192                |
| 14   | Lieutenant           | 16,384               |
| 15   | Lieutenant Commander | 32,768               |
| 16   | Commander            | 65,536               |
| 17   | Captain              | 131,072              |
| 18   | Commodore            | 262,144              |
| 19   | Rear Admiral         | 524,288              |
| 20   | Vice Admiral         | 1,048,576            |
| 21   | Admiral              | 2,097,152            |
| 22   | Fleet Admiral        | 4,194,304            |

**Commission**  
- A player becomes *commissioned* at **1,000 alignment**.  
- The **Imperial Star Ship (ISS)** becomes purchasable at **1,000 alignment**.

**Alignment‑gain methods (credits per point)**  

| Method                               | Credits per alignment point |
|--------------------------------------|----------------------------|
| Posting rewards on evil players       | 1,000                      |
| Cross‑pod with an evil partner       | 0 (no credit cost)         |
| Paying taxes                         | 1,500 (most expensive)    |
| Building planets                      | 2,000 (slow)               |
| Killing evil traders/aliens (‑250 align, 200 figs) | ≈ 400 |
| Upgrading ports                      | 5,000 (high upfront)       |

&gt; **Note:** Posting rewards is cheaper than paying taxes for alignment.

## Alignment‑Related Night‑Time Survival

- With **good alignment** and **&lt; 1,000 experience**, you may stay overnight in Federation space if the **ships‑per‑sector limit** is not exceeded and you carry **fewer than 99 fighters**.  
- Exceeding either limit triggers an automatic tow at Extern.  
- **Cloaking devices** provide an alternative safe haven: cloaked ships cannot be attacked directly, but cloaks may fail after 24 hours (appearing as a density anomaly). Photon torpedoes decloak them.

## Home Sectors and Base Placement

- Choose an **out‑of‑the‑way sector** (often a dead‑end) for early bases to reduce exposure to traffic and hostile ports.  
- Avoid building bases directly between **Class 0** and **Class 9** ports.

### Bubbles and Tunnels

- **Bubbles** are clusters of interconnected tunnels that have a single entry point.  
- **Tunnels** are linear chains allowing **2‑warp** movement.  
- For expansion, locate a bubble or tunnel and develop a **dead‑end sector** (no port) to place new planets.  
- Good‑aligned corporations typically develop bubbles containing **H**, **O**, and **L** planets to maximize daily credit generation and fighter production.

## Planet Mechanics

### Planet Types, Ratios, and Production Limits

| Class | Ratio (Fuel/Org/Equ) | Max Colonists | Max Daily Fuel | Max Daily Org | Max Daily Equ | Max Daily Fighters |
|-------|-----------------------|---------------|----------------|---------------|----------------|--------------------|
| M (Earth)      | 3 / 7 / 13 | 30,000 | 5,000 | 2,142 | 1,153 | 829 |
| K (Desert)     | 2 / 100 / 500 | 40,000 | 10,000 | 200 | 40 | 682 |
| O (Oceanic)    | 20 / 2 / 100 | 200,000 | 5,000 | 50,000 | 1,000 | 3,733 |
| L (Mountain)  | 2 / 5 / 20 | 40,000 | 10,000 | 4,000 | 1,000 | 1,250 |
| C (Glacial)    | 50 / 100 / 500 | 100,000 | 1,000 | 500 | 100 | 64 |
| H (Volcanic)  | 1 / ‑ / 500 | 100,000 | 50,000 | 0 | 100 | 1,002 |
| U (Vapour/Gas) | ‑ / ‑ / ‑ | 3,000 | 0 | 0 | 0 | 0 |

- The **daily production** of FOE products follows a bell curve; maximum output occurs at **50 %** of the maximum colonist count.  
- Colonist counts **below 50 %** tend to increase, while those **above 50 %** tend to die off proportionally.  
- **Maximum planet population** is **twice** the optimal colonist count; excess colonists reduce production efficiency.

### Fighter Production Factors

Fighters are generated indirectly from the daily FOE production. Each planet class defines a **Fig factor** – the number of colonists required to produce one fighter for a given commodity.

| Class | Fuel Fig Factor | Organics Fig Factor | Equipment Fig Factor |
|-------|-----------------|---------------------|----------------------|
| M | 30 | 70 | 130 |
| K | 30 | 1,500 | 7,500 |
| O | 300 | 30 | 1,500 |
| L | 24 | 60 | 240 |
| C | 1,250 | 2,500 | 12,500 |
| H | 50 | 0 | 25,000 |
| U | ‑ | ‑ | ‑ |

**Formula (illustrative)**  

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