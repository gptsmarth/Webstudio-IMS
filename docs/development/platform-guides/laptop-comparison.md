# Laptop Comparison

Open **Comparison** from the desktop sidebar. Staff with inventory view
permission can compare two laptops by default and add up to four. Use the cross
at the top of the third or fourth column to remove it. Each column has its own
selection and loading state.

- **From Inventory** searches available laptops by brand, name, and all or
  part of a model number. The server reads existing model and stock records
  with pagination. The comparison shows saved configuration and grouped
  spec notes, the saved product image when available, and the stock count.
  The sales price follows the same inventory permission and begins with
  the current Stock display preference. No Gemini or image discovery runs.
- **Outside Inventory** accepts the manufacturer and complete model number,
  including its variant. Gemini must return a grounded exact match before
  the comparison can use the result. Missing component information remains
  unavailable. An image appears when an official image URL identifies the
  exact variant. Other results display the standard laptop placeholder.
- **Customer View** opens when two or more laptops have been selected. It
  shows the selected laptops and grouped specifications with differences
  highlighted. Use **Back to editing** or Escape to return. The presentation
  labels availability and excludes internal notes and research controls.

External research uses the server's existing Gemini configuration and sends
only the submitted manufacturer and model identifier. If Google Search
grounding cannot confirm the variant, staff can edit the identifiers and
retry. Successful results are reusable for 30 days, including across server
restarts. The maintenance scheduler removes expired entries. When maintenance
is disabled, expired results are still ineligible and are replaced upon a
successful new lookup.

Apply migration `0058_laptop_comparison_cache` before deploying the updated
backend and desktop. New backup archives omit the transient cache rows.
Outside Inventory requires Gemini and a configured model with Google Search
grounding. Inventory comparison remains available independently of Gemini.
[Google Search grounding](https://ai.google.dev/gemini-api/docs/google-search)

## Implementation references

- Desktop workspace, selection controls, grouped rows, and presentation mode.
  [Comparison page](../../../apps/desktop/src/pages/workspace/ComparisonPage.tsx) · [Comparison components](../../../apps/desktop/src/components/comparison/) · [Component grouping](../../../apps/desktop/src/lib/laptopComparison.ts)
- Inventory query, Gemini lookup, validation, and cache expiry.
  [Comparison API](../../../apps/backend/src/webstudio_backend/api/routers/comparison.py) · [Comparison service](../../../apps/backend/src/webstudio_backend/services/laptop_comparison.py) · [Gemini provider](../../../apps/backend/src/webstudio_backend/services/ai/providers/gemini.py)
- Persistent cache and API payloads.
  [Alembic migration](../../../database/migrations/versions/0058_laptop_comparison_cache.py) · [Cache schema](../../../database/schemas/laptop_comparison_cache.md) · [API contract](../../api/openapi/webstudio-ims-api-v1.yaml)
- Regression coverage.
  [Backend tests](../../../apps/backend/tests/comparison/test_laptop_comparison.py) · [Desktop tests](../../../apps/desktop/tests/laptopComparison.test.tsx)
