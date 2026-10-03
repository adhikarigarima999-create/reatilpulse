# A/B Test Log — Discount Promo on Repeat Purchase

## Hypothesis
H0: A 10% discount promo has no effect on repeat-purchase rate.
H1: A 10% discount promo increases repeat-purchase rate.

## Sample balance
- t=0.618, p=0.537 on avg_order_value pre-treatment (balanced)

## Result
- Treatment repeat rate: 0.0695
- Control repeat rate: 0.0300
- Absolute lift: 3.94 percentage points
- z=27.722, one-sided p=0.0000

## Business recommendation
DO NOT SHIP as-is: either the lift is not statistically significant (p=0.0000) or the modeled discount cost (R$745,136) exceeds the modeled incremental revenue (R$305,095). Recommend testing a smaller discount or targeting only high-value segments.
