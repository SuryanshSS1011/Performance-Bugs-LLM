# Average Code Changes per Performance Bug Category

Statistics on file size and edit footprint for each bug category, computed across
the 490-bug curated dataset.

| Bug Type | Avg. Code Lines | Replaced Lines | Generated Lines |
|----------|-----------------|----------------|-----------------|
| Algorithmic Inefficiency | 268 | 27 | 31 |
| Memory Usage             | 272 | 19 | 23 |
| Redundant Computation    | 251 | 14 | 16 |
| CPU Overhead             | 259 | 18 | 21 |
| I/O Inefficiency         | 290 | 22 | 25 |
| **Overall Average**      | **268** | **21** | **24** |

## Observations

- **I/O Inefficiency** bugs appear in the largest files (avg. 290 lines), suggesting
  they often arise inside complex modules with multi-step resource handling.
- **Algorithmic Inefficiency** fixes require the most edits (27 replaced, 31 generated),
  indicating these typically involve substantial logic restructuring rather than
  localized changes.
- Across all categories, **generated lines slightly outnumber replaced lines**,
  reinforcing that clearer, more optimized code often expands modestly.
- **Redundant Computation** has the smallest edit footprint (14 replaced, 16
  generated) — these issues are more localized and easier to fix.
