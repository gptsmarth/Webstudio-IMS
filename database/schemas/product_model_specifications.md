# Product model specifications

Migration `0061_product_model_specs` adds supplemental laptop hardware
facts to `webstudio.product_models`. `detailed_specifications` is a JSONB array
of public component labels and details. Research timestamps track successful
exact-model lookup and the next eligible retry after an incomplete lookup.

The facts belong to the product model and are included in PostgreSQL business
backups. External comparison and processor caches remain transient. Older
backups omit the new columns and use their defaults when restored into the
upgraded schema. Changes to the saved SKU, brand, or main hardware configuration
clear supplemental facts so they can be fetched for the updated model.
