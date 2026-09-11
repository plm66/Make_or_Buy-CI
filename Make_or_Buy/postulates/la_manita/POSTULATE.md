# LA MANITA — NORMATIVE POSTULATE v1.6.0

> Lecture humaine du postulat. La source normative est `la_manita.postulate.json` ;
> en cas d'écart, c'est lui qui fait foi. Historique des révisions sous `deltas/`.

## Core invariant

La Manita is a fixed-price mix-and-match system.

The customer selects exactly:
- 1 SNACK
- 1 COLD_DRINK
- 1 GARNITURE
- 1 DESSERT
- 1 HOT_DRINK

The customer receives 5 items for EUR 5.00.

Target catalog density: 10 references per family.
At target density, theoretical choice space = 100,000 combinations.

## Primary design rule

Customer simplicity is invariant.

Customer-visible logic:

    5 choices
    5 items
    EUR 5.00

System-hidden logic:

    cost
    sourcing
    MAKE / BUY / HYBRID
    stock
    shelf life
    dietary constraints
    allergens
    traceability
    supplier reliability
    waste
    labor
    signature value

## Matrix doctrine

Preferred mode: FULL_MATRIX.

Every visible reference should be freely combinable with every visible reference from the other families.

Validation must compute:

    worst_case_bundle_cost

If:

    worst_case_bundle_cost > configured_max_bundle_cost

then the catalog is invalid unless references are removed/substituted or the system explicitly switches to CONSTRAINED_MATRIX.

CONSTRAINED_MATRIX is a fallback because it increases customer complexity.

## Product doctrine

La Manita does not own product master data.
It references the canonical product catalog and inherits:
- sourcing mode
- doctrine class
- dietary evidence
- allergens
- stock
- conservation
- supplier data
- cost data
- signature value

## Portfolio doctrine

A family is not optimized only for minimum cost.

Allowed economic roles:
- MARGIN_PROTECTOR
- PERCEIVED_VALUE_DRIVER
- SIGNATURE_PRODUCT
- STOCK_ABSORBER
- WASTE_RECOVERY
- SUPPLIER_EFFICIENCY

## Dietary completeness

A dietary bundle is valid only if one eligible product exists in every required family.

If a family blocks completion:

    status = NO_VALID_BUNDLE
    blocking_family = <family_id>

No dietary claim may be completed by inference.

## Dynamic slots

Dynamic rows are allowed.

Example:

    Dessert du jour

A dynamic slot must resolve to an eligible canonical product at runtime.

## UX invariant

The customer flow remains:

1. choose Snack
2. choose Cold Drink
3. choose Complement
4. choose Dessert
5. choose Hot Drink
6. pay EUR 5.00

No cost reasoning is exposed to the customer.
