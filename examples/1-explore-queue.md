# 1 · Explore Queue  (input)

The 20 products the factory will **explore** — it generates and vision-scores **two ad concepts per product**, unattended, for ~2 credits an image. Nothing here needs a human yet.

| # | Product | Category | Price | Tagline |
|:--:|---|---|--:|---|
| 1 | Summit Tumbler 20oz | Drinkware | $34 | Hot at 9am, hot at 2pm. |
| 2 | Trail Flask 24oz | Drinkware | $39 | The bottle that outlasts the hike. |
| 3 | Daybreak Mug | Drinkware | $22 | A morning ritual you can hold. |
| 4 | Helix Pour-Over | Brew | $42 | Precision, one cup at a time. |
| 5 | Clarity Carafe | Brew | $36 | See every drop. |
| 6 | Torque Hand Grinder | Brew | $78 | Grind like you mean it. |
| 7 | Onyx Kettle | Brew | $119 | A steady pour, every time. |
| 8 | Feather Scale | Brew | $54 | The gram that matters. |
| 9 | Press No.4 | Brew | $48 | Bold, the old way. |
| 10 | Slow Cold Brew | Brew | $44 | Patience, bottled. |
| 11 | Whisk Frother | Accessories | $24 | Cafe foam, at home. |
| 12 | Vault Canister | Accessories | $32 | Freshness, locked in. |
| 13 | Commuter 12oz | Drinkware | $29 | Leakproof. Truly. |
| 14 | Demi Espresso Set | Drinkware | $28 | Small cup, big morning. |
| 15 | Verdant Infuser | Drinkware | $31 | Loose leaf, anywhere. |
| 16 | Sphere Ice Press | Accessories | $62 | One perfect sphere. |
| 17 | Terra Coasters | Accessories | $26 | Rings, retired. |
| 18 | Nomad Growler 64oz | Drinkware | $59 | Cold all day, all trail. |
| 19 | Pebble Cup 8oz | Drinkware | $19 | The reusable you'll actually reuse. |
| 20 | Aera Brewer | Brew | $46 | Pressure, on demand. |

_20 products queued → the explore workflow fans out a worker pool and fills the review queue with scored concepts._