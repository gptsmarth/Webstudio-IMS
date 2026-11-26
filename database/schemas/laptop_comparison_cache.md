# Laptop comparison research cache

Revision 0058_laptop_comparison_cache creates webstudio.laptop_comparison_cache.
This table contains external laptop research. It has no foreign key to stock
or sales.

| Column | Type | Purpose |
| --- | --- | --- |
| normalized_brand | varchar(80) | Case-insensitive manufacturer key |
| normalized_model | varchar(160) | Full model identifier, including variant punctuation |
| payload | jsonb | Validated comparison fields and an optional matching image URL |
| created_at | timestamptz | Time of successful research |
| expires_at | timestamptz | Exactly 30 days after successful research |

The primary key is (normalized_brand, normalized_model). The expiry index
supports cleanup by the maintenance scheduler. The API checks expiry on every
lookup. A per-key PostgreSQL advisory transaction lock serializes refreshes
across server processes. Backup archives exclude the transient research rows.
