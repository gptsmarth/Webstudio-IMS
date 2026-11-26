# Laptop comparison research cache

Revision 0058_laptop_comparison_cache creates webstudio.laptop_comparison_cache.
This table contains external laptop and processor research. It has no foreign
key to stock or sales.

| Column           | Type         | Purpose                                                         |
| ---------------- | ------------ | --------------------------------------------------------------- |
| normalized_brand | varchar(80)  | Case-insensitive manufacturer key or the reserved `:cpu:` value |
| normalized_model | varchar(160) | Full laptop SKU or exact processor identifier                   |
| payload          | jsonb        | Validated laptop fields or an array of processor specifications |
| created_at       | timestamptz  | Time of successful research                                     |
| expires_at       | timestamptz  | Exactly 30 days after successful research                       |

The primary key is (normalized_brand, normalized_model). The expiry index
supports cleanup by the maintenance scheduler. The API checks expiry on every
lookup. A per-key PostgreSQL advisory transaction lock serializes refreshes
across server processes. Optional processor lookups skip the refresh when
another request already holds that processor's lock. Backup archives exclude
the transient research rows.
