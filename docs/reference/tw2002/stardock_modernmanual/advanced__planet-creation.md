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
                                 id="post-planet-creation">
                                <h1><a href="/post/planet-creation"
                                       rel="bookmark"
                                       title="Planet Creation">Planet Creation</a></h1>
                                <div class="by">by <span class="author">System</span> on 2026-01-26 | Categories: Files&nbsp;
                                    <!--button class="toggle-visibility-btn"
                                            data-post-id="planet-creation"
                                            title="Toggle visibility">
                                        👁️
                                    </button-->
                                </div>

                                <div class="post-content">
                                    <div id="post-content-planet-creation"
                                         data-markdown>## Planet Creation Mechanics

### 1. Base Creation Probabilities
- Each planet class has a **hard‑coded base probability** that determines its chance to be generated when a GTorp is launched.
- The base probabilities for the stock planet classes (L, O, H, M, U, C) together sum to **100 %**.
- Exact numeric values are defined by the game engine and are not exposed in the documentation; they are fixed per class.

### 2. Modifiers Affecting Effective Probability
Two primary modifiers adjust the base probability when a GTorp is launched:

| Modifier | Effect on Effective Probability |
|----------|-----------------------------------|
| **Sector Planet Count** | Increases the chance of generating a **U‑class** (undesirable) planet as the number of existing planets in the sector rises. At the maximum sector limit the U‑class probability can approach **≈ 98 %**. |
| **Sector Planet Count** (Gold) | Raises the chance of generating a **C‑class (Gold)** planet under the same conditions, though the base probability for Gold planets is low. |

&gt; **Note:** The modifiers apply uniformly; each additional planet in the sector shifts probability weight toward U‑class and, proportionally, toward Gold (C‑class) when the sector is being cleared.

### 3. Optimal Planet Creation Sequence
To maximize the acquisition of desirable Gold (C‑class) planets, launch GTorps **up to the sector limit** before destroying any planets. Then work backwards, destroying the least desirable planet after each launch.

#### Step‑by‑Step Procedure
1. **Launch GTorps equal to the sector’s planet limit** (e.g., 5 GTorps if the sector allows 5 planets).  
2. **Identify the worst remaining planet** (U‑class first, then M, L, O, H, finally C).  
3. **Destroy (ZDY) that planet**.  
4. **Launch an additional GTorp** to replace the destroyed planet, keeping the sector at its maximum planet count.  
5. **Repeat steps 2‑4** until all desired Gold planets are generated or resources are exhausted.

#### Example Walkthrough (5‑planet sector)

| Launch # | Planet Class after Launch | Action Taken |
|----------|---------------------------|--------------|
| 1        | M                         | – |
| 2        | M                         | – |
| 3        | U                         | ZDY U |
| 4        | H                         | – |
| 5        | C (Gold)                  | – |
| 6        | M                         | ZDY M |
| 7        | M                         | – |
| 8        | L                         | – |
| 9        | H                         | – |
|10        | C (Gold)                  | – |

After each ZDY, a new GTorp is launched to maintain the sector at five planets, progressively eliminating the lowest‑value planets and raising the odds of retaining Gold planets.

### 4. Data Collection Methodology
Players can empirically determine the exact base probabilities and modifier magnitudes by:

1. **Launching and destroying planets individually** for a large sample size (≈ 300–500 launches per class).  
2. Recording the frequency of each planet class appearance.  
3. Analyzing the data to isolate the **base probability** (observed when the sector is empty) and the **modifier effect** (observed as planet count increases).

&gt; **Caution:** This process requires a **stock game environment** (no custom planet settings) and, optionally, a separate run with a different number of Gold planets to compare modifier behavior.

### 5. Summary of Key Points
- Base probabilities are fixed per planet class and sum to 100 %.  
- Adding planets to a sector strongly favors **U‑class** generation; at full capacity U‑class can reach **≈ 98 %**.  
- Gold (C‑class) planets benefit from the same planet‑count modifier, increasing their likelihood in crowded sectors.  
- The most efficient method to harvest Gold planets is to **launch to sector capacity first**, then **systematically destroy the worst remaining planet** after each launch, preserving a “clean” sector for subsequent GTorps.  
- Accurate probability data can be obtained only through extensive empirical testing in a vanilla game setting.

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