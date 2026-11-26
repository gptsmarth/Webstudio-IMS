# ASUS activation

Migration `0059_asus_activation` adds three tables in `webstudio`.

- `asus_activation_schemes` stores an inclusive India business date range, upload metadata,
  SHA-256, and compact rates by exact normalized model. Each rate records Supported SRP,
  CN to two decimals, and source sheet, row, programme code and period when available.
  The service serializes writes and rejects overlapping date ranges.
- `asus_activation_workbooks` holds the original activation workbook for its scheme and
  its expiry timestamp. Maintenance and scheme uploads purge expired bytes.
  Business backups omit rows in this table and preserve the parsed scheme.
- `asus_activation_receipts` stores one settlement per recorded sale. It preserves the
  scheme and expected amount, reported CN excluding GST, provenance and release date,
  actor and recorded time, plus a separate actor, timestamp and note for variance resolution.

Claims are derived from saved sales and the uploaded rates by invoice date. This makes
historical and newly synced sales visible through the same logic. There are no writes to
Tally invoices or sales. Cancelled sales without receipts leave the claim list. A
settlement remains visible with a cancellation flag if its sale is cancelled.
