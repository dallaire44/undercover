# Accessibility: color blindness

How the UnderCover dashboard works for claims handlers with color blindness. About 1 in 12 men and 1 in 200 women have some color blindness. Most of it is red-green (the protan and deutan types). Blue-yellow (tritan) is rare.

## What already holds

- Color is never the only signal. Every claim-state and decision chip carries its word, such as "Waiting" or "Declined", and the counts on the queue page have labels.
- The brand colors stay distinguishable under all three types of color blindness (see the results below). The weakest pair is Approved (Sea Green) against Declined (Coral) for protanopia.
- Two brand chips have text below the WCAG AA contrast of 4.5:1 for text of their size: white on Cerulean (Waiting) is 3.96:1, and white on Raspberry (payment on hold) is 3.62:1. These colors come from `docs/BRAND.md`, so changing them is for UnderCover's brand owners to decide. The color-blind mode below fixes both.

## How we tested

Each color is converted to how people with each type of color blindness see it, using the model of Machado, Oliveira and Fernandes (2009) at full severity, applied in linear RGB. We then measure the color difference ΔE (CIE76, in CIELAB) between every pair in a set and report the smallest. A difference under about 10 is hard to tell apart. Text contrast uses the WCAG 2 formula.

The smallest difference between any two of the four claim-state colors:

| Colors | Protanopia | Deuteranopia | Tritanopia |
|---|---|---|---|
| Brand: Cerulean, Coral, Marigold, Sea Green | 17.2 | 28.9 | 26.2 |
| Okabe-Ito: blue, vermilion, yellow, bluish green (the color-blind mode) | 37.2 | 33.6 | 17.0 |
| Paul Tol bright: blue, green, yellow, red | 29.8 | 19.1 | 13.1 |

Approved against Declined, the pair where a mix-up matters most:

| Colors | Protanopia | Deuteranopia | Tritanopia |
|---|---|---|---|
| Brand: Sea Green and Coral | 17.2 | 28.9 | 101.8 |
| Okabe-Ito: bluish green and vermilion (the color-blind mode) | 37.2 | 53.4 | 108.2 |

The color-blind mode roughly doubles the margin for the red-green types, which make up nearly all color blindness. Two pairs come closer than in the brand, and both stay above the threshold: Waiting and Decided for tritanopia (17.0, against 26.2 in the brand), and Approved against the payment-on-hold box for deuteranopia (17.9). Both chips and the box also carry their words.

## Color-blind palettes, for reference

- **Okabe-Ito**, from Okabe and Ito's Color Universal Design and republished by Wong in Nature Methods (2011): orange `#E69F00`, sky blue `#56B4E9`, bluish green `#009E73`, yellow `#F0E442`, blue `#0072B2`, vermilion `#D55E00`, reddish purple `#CC79A7`, black `#000000`.
- **Paul Tol, bright**: `#4477AA` `#EE6677` `#228833` `#CCBB44` `#66CCEE` `#AA3377` `#BBBBBB`.
- **Paul Tol, vibrant**: `#EE7733` `#0077BB` `#33BBEE` `#EE3377` `#CC3311` `#009988` `#BBBBBB`.
- **Paul Tol, high-contrast**: `#004488` `#DDAA33` `#BB5566`.
- **IBM Design Language v1, color-blind safe**: `#648FFF` `#785EF0` `#DC267F` `#FE6100` `#FFB000`.
- **viridis and cividis**: for scales from low to high, such as a heat map, rather than for categories.

Sources: Okabe and Ito at https://jfly.uni-koeln.de/color/, Paul Tol's notes at https://sronpersonalpages.nl/~pault/, and the IBM Design Language v1 color library.

## The color-blind mode

A "Color-blind mode" slider in the header, drawn like the "Dark mode" one (see `docs/SPEC.md`): the dot at the left is off and at the right is on. It is off by default, so the dashboard looks as `docs/BRAND.md` describes. When a handler turns it on:

| What | Brand | Color-blind mode | Text on it |
|---|---|---|---|
| Waiting | Cerulean `#118AB2` | blue `#0072B2` | white, 5.2:1 |
| In progress | Coral `#F78C6B` | vermilion `#D55E00` | black, 5.4:1 |
| Waiting for sign-off | Marigold `#FFC145` | yellow `#F0E442` | black, 15.9:1 |
| Decided | Sea Green `#06D6A0` | bluish green `#009E73` | black, 6.1:1 |
| Approved | Sea Green | bluish green `#009E73`, with a check | black, 6.1:1 |
| Declined | Coral | vermilion `#D55E00`, with a cross | black, 5.4:1 |
| Referred | Marigold | yellow `#F0E442`, with an arrow | black, 15.9:1 |
| Payment on hold | Raspberry `#EF476F` | reddish purple `#CC79A7` | black, 6.9:1 |

- The claim-state colors apply to the chips and to the dots on the count tiles.
- The symbols on the decision chips give Approved and Declined different shapes as well as colors. They are small inline SVG drawings, not emoji characters, and screen readers skip them, since the chip's word already says it.
- Nothing else changes: not the layout, the fonts, the text and link colors, or light and dark mode. The mode works in both.
- The choice is remembered per browser, like the dark mode switch.

## Browser recoloring

Some browser features repaint every page in their own dark colors, such as Chrome's "Auto Dark Mode for Web Contents" (`chrome://flags/#enable-force-dark`) and extensions like Dark Reader. They change the dashboard's colors after it has drawn them, including the color-blind palette. In Chrome 151, for example, the sign-off yellow `#F0E442` becomes a dark olive, even in the dashboard's own dark mode. The page cannot opt out: Chrome ignored `<meta name="color-scheme">`, `color-scheme: light dark` and `color-scheme: only light` in our tests. Handlers who rely on the color-blind colors should turn these features off for the dashboard and use its own "Dark mode" and "Color-blind mode" switches.

## The switch, and alternatives considered

- **A switch next to "Dark mode" (recommended).** Browsers and operating systems have no color-blindness setting that a page can read, unlike dark mode, so the mode can't start from the computer's setting. A switch the handler turns on once is the simplest control, and it matches the one already in the header.
- **A "Display" menu holding both switches.** Tidier if more display options arrive later, but not needed for two.
- **Approved in blue.** Blue against vermilion scores even higher for protanopia (91.9), but blue already means Waiting. With the symbols added, bluish green is enough.

## How it will be built

The mode is an attribute on `<html>`, `data-colors="color-blind"`, set before the page draws by the same lines in `dashboard/index.html` that set dark mode. The chip colors move into CSS variables in `dashboard/src/styles.css`, and the color-blind values override them. The symbols are always in the page and hidden by CSS unless the mode is on. `ThemeSwitch` in `dashboard/src/ThemeSwitch.tsx` becomes one small reusable switch used for both modes. The backend and the agent are not touched.
