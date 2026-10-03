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
                                 id="post-pod-mechanics">
                                <h1><a href="/post/pod-mechanics"
                                       rel="bookmark"
                                       title="Pod Mechanics">Pod Mechanics</a></h1>
                                <div class="by">by <span class="author">System</span> on 2026-01-25 | Categories: Files&nbsp;
                                    <!--button class="toggle-visibility-btn"
                                            data-post-id="pod-mechanics"
                                            title="Toggle visibility">
                                        👁️
                                    </button-->
                                </div>

                                <div class="post-content">
                                    <div id="post-content-pod-mechanics"
                                         data-markdown># Pod Mechanics

## Overview
When a ship is destroyed, the game places the pilot’s escape pod in a sector determined by two distinct rules:

1. **Self‑destruction** – the pod is sent to the ship’s **previous sector**.  
2. **Killed by another player** – the pod follows the **safe‑path algorithm**.

Understanding both mechanisms enables precise control of pod placement during invasions, retreats, and other risky maneuvers.

---

## Previous Sector

The game tracks a *previous‑sector* field that is updated whenever the ship changes location. The value stored is used as the pod destination if the pilot kills himself (e.g., by blowing up on a quasar, hitting a naval hazard, or any other self‑inflicted fatal event).

| Movement Type | Effect on Previous Sector |
|---------------|---------------------------|
| Manual warp or retreat (e.g., `1234 → 2345`) | Set to the sector departed from (`1234`). |
| Transport from ship A to ship B (`1234 → 2345`) | Set to the origin sector (`1234`). |
| Transport between two ships located in the same sector (`2345 → 2345`) | Set to that sector (`2345`). |
| **P‑warp** (`1234 → 2345`) | Historically set to sector 1; recent versions leave it unchanged. |
| Teammate‑p‑warp you into the same sector (`1234 → 2345`) | Updated to the destination sector (`2345`). |
| **T‑warp** (`1234 → 2345`) | Updated to the destination sector (`2345`). |
| **B‑warp** (`1234 → 2345`) | **Does not change** the previous‑sector field. |
| **B‑warp fusion** (failed b‑warp while pod is active) | Pod is placed in the sector from which the b‑warp was attempted, **ignoring** the stored previous sector. |

*Note:* The previous sector is only relevant for self‑destruction. If another player eliminates you, the safe‑path algorithm overrides this value.

---

## Safe‑Path Algorithm

When killed by another player, the pod searches for a *safe* sector to flee to. A sector qualifies as **safe** if it contains only your own fighters, belongs to your corporation, or is empty.

The algorithm proceeds as follows:

1. **Select Random Targets** – generate a set of candidate sectors 3 to 20 hops away (exact range may vary by version).  
2. **Path Planning** – compute a route from the current sector to each candidate.  
3. **Safe Advancement** – follow each route as far as possible, stopping when the next hop would enter an unsafe sector.  

The pod then materializes at the farthest reachable safe sector along the chosen route. If **all** routes encounter unsafe sectors immediately, the pod remains in the sector where it was destroyed.

### Typical Outcomes
- **At least one adjacent safe sector** – the pod will move at least one hop away, often traveling many sectors if you own multiple contiguous sectors.  
- **Surrounded by enemy fighters** – no safe adjacent sector exists; the pod stays in the death sector, making it vulnerable to immediate capture.  
- **Dead‑end or gate** – if the current sector is a dead‑end surrounded by unsafe sectors, the pod cannot escape and remains in place (example diagram below).

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