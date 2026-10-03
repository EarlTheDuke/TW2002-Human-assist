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
                                 id="post-twgs-settings">
                                <h1><a href="/post/twgs-settings"
                                       rel="bookmark"
                                       title="Twgs Settings">Twgs Settings</a></h1>
                                <div class="by">by <span class="author">System</span> on 2026-01-25 | Categories: Files&nbsp;
                                    <!--button class="toggle-visibility-btn"
                                            data-post-id="twgs-settings"
                                            title="Toggle visibility">
                                        👁️
                                    </button-->
                                </div>

                                <div class="post-content">
                                    <div id="post-content-twgs-settings"
                                         data-markdown># TWGS Settings Guide

## Big‑Bang Settings

| Option | Description | Default | Valid Range | Recommended |
|--------|-------------|---------|-------------|------------|
| **R** | Random seed. Must be randomized each big‑bang to avoid identical sector maps. | — | — | Always randomize |
| **A** | Number of sectors. Values above 1,000 require Gold settings (**J**) to be enabled. | — | — | — |
| **B** | Max course length – maximum distance between two sectors. | 45 | 20 – 255 | — |
| **C** | Maximum ports – percent of total sectors that become ports. | 40 % | 10 % – 80 % | 50 % – 60 % |
| **D** | Initial ports – percent of the total ports built at universe creation. | 95 % | 10 % – 100 % | Keep default; adjust total ports via **C** |
| **E** | Maximum number of planets – percent of total sectors that contain planets. | 20 % | 2 % – 40 % | 40 % |
| **F** | Total number of two‑way warps – percent of total sectors. | 30 % | 10 % – 200 % | Default |
| **G** | Total number of one‑way warps – percent of total sectors. | 3 % | 1 % – 100 % | 5 % |
| **H** | Max number of players. | 200 | 10 – 500 | — |
| **I** | Max number of ships – 4 × players, capped at 2,000. | 4 × players (max 2,000) | — | Set to 2,000 for versions ≤ .47; otherwise default is sufficient |
| **J** | Enable Gold settings – required for &gt; 1,000 sectors and custom ships, planets, aliens. | No | Yes/No | Yes if available |
| **K** | Enable bubbles – buggy under version .55; not recommended until fixed. | No | Yes/No | No |
| **P** | Turns on MBBS compatibility mode – activates MBBS‑style combat penalties. | Off | On/Off | Turn on for “reds” |

## Post Big‑Bang Editor Settings

### General Editor One (Section G)

| Setting | Description | Value |
|---------|-------------|-------|
| **A** | Turns per day | 1 – unlimited |
| **B** | Initial fighters | — |
| **C** | Initial credits | — |
| **D** | Initial holds | — |
| **E** | Days until an inactive user is deleted | 30 |
| **G** | Ferrengi regeneration percentage (of max 1,100) | 20 % (≈ 220) |
| **H** | Terran colonist reproduction rate | 750 colonists per day |
| **I** | Daily log limit (lines) | 800 |
| **J** | StarShip *Intrepid* location | Sector 7 |
| **K** | StarShip *Valiant* location | Sector 3,148 |
| **L** | StarShip *Lexington* location | Sector 3,959 |
| **M** | Maximum number of planets in a sector | 5 |
| **N** | Maximum number of traders per corporation | 5 |
| **O** | Underground password phrase | “BEWARE OF KAL DURAK” |
| **P** | Age of game (days) | 22 |
| **R** | Tournament mode | Off |
| **S** | Days to allow entry | Unlimited |
| **T** | Maximum times blown up | Unlimited |

### General Editor Two (Section H)

| Setting | Description | Value |
|---------|-------------|-------|
| **A** | TriCron champion | None |
| **B** | TriCron jackpot | 0 |
| **C** | TriCron high score | 0 |
| **D** | Ferrengi home base | — |
| **E** | Stardock sector | — |
| **F** | Rylos sector | — |
| **G** | Alpha Centauri sector | — |
| **H** | Ferrengi move chance | 1 in 20 |
| **I** | Alien move chance | 1 in 20 |
| **J** | Gfiles scores directory | None used |
| **K** | Sysop security level | 32,000 |
| **L** | Allow aliases | Yes |
| **M** | Display Stardock | Yes |
| **O** | FedSpace ship limit | 5 |
| **P** | Photon wave duration | 1 second |
| **R** | DESQview pacing | 20 |
| **T** | Local display | Yes |
| **U** | Cloaking fail rate | 3 % |
| **V** | Navigation hazard dispersion | 100 % |
| **W** | New‑player planets | No |
| **Y** | Ship delay mode | None |
| **S** | Max commands per cycle | Unlimited |
| **1** | Processing interval | 1 second |
| **2** | Inactivity timeout | 14,400 seconds |
| **3** | Steal from buy port | Yes |
| **4** | Planetary trade offers | 100 % (normal) |
| **5** | Online verification interval | 300 seconds |
| **6** | Clear busts every | 1 day |
| **7** | Port regeneration rate | 1 % per day |
| **8** | Max regeneration per visit | 100 % |
| **9** | Local beeper | Yes |
| **0** | International alien processing | Disabled |
| **N** | International Ferrengi processing | Disabled |
| **Z** | Alien server offline mode | Active |
| **X** | Gold editor expert mode | Disabled |
| **[** | Closed game | No |
| **]** | Password required | No |
| **\\** | Global TEDIT password | No |
| **$** | Local TEDIT password | No |
| **;** | Ether probe move delay | None |
| **:** | Maximum course length | 45 |
| **/** | Daily game time | Unlimited |
| **|** | Output segmentation | None |
| **#** | Invincible Ferrengal | No |

### General Editor Three (Section I)

| Setting | Description | Cost |
|---------|-------------|------|
| **A** | Transport unit | 12,500 credits |
| **B** | Transport upgrade | 6,250 credits |
| **C** | Tavern announcement | 100 credits |
| **D** | Limpet removal | 1,250 credits |
| **E** | Ship re‑registration | 5,000 credits |
| **F** | Genesis torpedo | 80,000 credits |
| **G** | Armid mine | 4,000 credits |
| **H** | Limpet mine | 40,000 credits |
| **I** | Beacon | 100 credits |
| **J** | Type I TWarp | 12,500 credits |
| **K** | Type II TWarp | 20,000 credits |
| **L** | TWarp upgrade | 9,000 credits |
| **M** | Psychic probe | 2,500 credits |
| **N** | Planet scanner | 7,500 credits |
| **O** | Atomic detonator | 60,000 credits |
| **P** | Corbomite | 1,000 credits |
| **R** | Ether probe | 12,000 credits |
| **S** | Photon missile | 160,000 credits |
| **T** | Cloaking device | 6,250 credits |
| **U** | Mine disruptor | 1,500 credits |
| **V** | Holographic scanner | 6,250 credits |
| **W** | Density scanner | 500 credits |
| **X** | Radiation lifetime | 1 day |
| **Y** | Rob factor (standard) | 50 % |
| **Z** | Steal factor (standard) | 70 % |
| **1** | Max Terran colonists | 100,000 |
| **2** | Combat penalty mode | MBBS |
| **3** | Max port production | 32,760 |
| **4** | Rob/steal delay | No |
| **5** | Secure local access | No |
| **6** | Fighter lock decay | 1,440 minutes |
| **7** | Death delay | Yes |
| **8** | Multiple photon fire | No |
| **9** | Show who’s online | Yes |
| **0** | FedSpace photons | No |

## Summary of Key Recommendations

* Randomize **Option R** each big‑bang.  
* Set **Option C** (max ports) between 50 %–60 % for robust port availability.  
* Use the maximum planet percentage (**Option E**) of 40 % to increase denial difficulty.  
* Raise one‑way warps (**Option G**) to about 5 % for greater map flexibility.  
* Enable Gold settings (**Option J**) when planning a universe larger than 1,000 sectors.  
* Keep bubble support (**Option K**) disabled until the underlying bug is resolved.  
* Activate MBBS compatibility (**Option P**) only when “reds” are desired.  

All values, ranges, and recommendations are taken directly from the official configuration reference.</div>
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