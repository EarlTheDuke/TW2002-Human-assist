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
                                 id="post-defense">
                                <h1><a href="/post/defense"
                                       rel="bookmark"
                                       title="Defense">Defense</a></h1>
                                <div class="by">by <span class="author">System</span> on 2026-01-25 | Categories: Files&nbsp;
                                    <!--button class="toggle-visibility-btn"
                                            data-post-id="defense"
                                            title="Toggle visibility">
                                        👁️
                                    </button-->
                                </div>

                                <div class="post-content">
                                    <div id="post-content-defense"
                                         data-markdown>## 1. Base Location Selection

### 1.1 Bubbles and Dead‑End Sectors
- **Bubble** – a contiguous region of at least 100 sectors with a single entrance/exit.  
- **Dead‑End Bubble** – a bubble whose interior sectors have no exits other than the entrance sector.  
- Building bases in small dead‑end bubbles limits the number of sectors an opponent can search, increasing concealment.

### 1.2 Tunnel Sectors (2‑Warp Chains)
- **Tunnel** – a linear chain of sectors (1 – 20 sectors) where each sector has exactly two warp exits; the chain is not part of a larger bubble.  
- Tunnels provide isolation from high‑traffic routes while still allowing the owner quick two‑warp ingress/egress.

### 1.3 Avoidance of High‑Traffic Areas
Do not place bases adjacent to:
| High‑Traffic Feature | Reason |
|----------------------|--------|
| Major Space Lanes (MSL) | Frequent traffic raises discovery risk |
| Stardock (Class 9 port) | Constant scanner activity |
| Class 0 ports (equipment hubs) | High‑volume trade draws attention |

### 1.4 Port‑Less Bases vs. SDT Port Integration
| Situation | Advantage | Consideration |
|----------|-----------|----------------|
| Base in a sector without a port | Maximum stealth; opponents cannot locate via blocked‑port detection | Requires independent resupply of fuel and colonists |
| Base on a sector that hosts an SDT (Sell‑Steal‑Transport) port | Red corps can steal upgrade commodities directly; beamer installation reduces relocation turns | Port becomes a focal point for opponents and may attract blockades |

---

## 2. Planet Types, Production, and Fighter Ratios

### 2.1 Production Tables

| Class | Category | Ratio | Max Colonists | Max Daily Fuel | Max Daily Org | Max Daily Equ | Max on Planet (Fuel) | Max on Planet (Org) | Max on Planet (Equ) |
|-------|----------|-------|---------------|----------------|---------------|----------------|----------------------|---------------------|----------------------|
| **M** | Fuel Ore | 3 | 30,000 | 15,000 | – | – | 100,000 | – | – |
|       | Organics | 7 | 30,000 | – | 15,000 | – | – | 100,000 | – |
|       | Equipment | 13 | 30,000 | – | – | 15,000 | – | – | 100,000 |
| **K** | Fuel Ore | 2 | 40,000 | 20,000 | – | – | 200,000 | – | – |
|       | Organics | 100 | 40,000 | – | 20,000 | – | – | 50,000 | – |
|       | Equipment | 500 | 40,000 | – | – | 20,000 | – | – | 10,000 |
| **O** | Fuel Ore | 20 | 200,000 | 100,000 | – | – | 100,000 | – | – |
|       | Organics | 2 | 200,000 | – | 100,000 | – | – | 1,000,000 | – |
|       | Equipment | 100 | 200,000 | – | – | 100,000 | – | – | 50,000 |
| **L** | Fuel Ore | 2 | 40,000 | 20,000 | – | – | 200,000 | – | – |
|       | Organics | 5 | 40,000 | – | 20,000 | – | – | 200,000 | – |
|       | Equipment | 20 | 40,000 | – | – | 20,000 | – | – | 200,000 |
| **C** | Fuel Ore | 50 | 100,000 | 50,000 | – | – | 20,000 | – | – |
|       | Organics | 100 | 100,000 | – | 50,000 | – | – | 50,000 | – |
|       | Equipment | 500 | 100,000 | – | – | 50,000 | – | – | 10,000 |
| **H** | Fuel Ore | 1 | 100,000 | 50,000 | – | – | 1,000,000 | – | – |
|       | Equipment | 500 | 100,000 | – | – | 50,000 | – | – | 100,000 |
| **U** | (No production) | – | 3,000 | 0 | 0 | 0 | 10,000 | 10,000 | 10,000 |

&gt; **Note:** Daily production follows a bell curve; maximum output occurs at 50 % of the maximum colonist level.

### 2.2 Fighter Production Ratios
Fighter output is a fixed fraction of the daily FOE production for each class:

| Class | Fighter Ratio |
|-------|---------------|
| M | `n/10` |
| K | `n/15` |
| O | `n/15` |
| L | `n/12` |
| C | `n/25` |
| H | `n/50` |
| U | — (no fighters) |

&gt; **Formula Example** (Class M, 1,500 colonists on Fuel Ore):  
&gt; </div>
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