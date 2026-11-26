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

Migration `0060_asus_activation_edits` adds the following fields and table.

- Schemes keep a revision, dated model-rate overrides and a compact change history.
  Rules retain workbook pricing fields and effective source metadata. The scheme
  revision protects the preview from concurrent edits. Active and historical
  schemes use the same six-calendar-month edit window measured from the end date.
- Receipts keep the original rate and scheme snapshot and bind a resolution to
  the expected amount used when it was recorded. When an edited scheme no longer
  covers the sale, the receipt is still visible with its original reference.
- `asus_activation_cn_overrides` stores one audited individual correction per sale.
  It takes precedence over the current scheme amount for eligible sales. A cleared
  correction retains its latest audit metadata. Model-wide corrections are dated
  scheme rates. Subsequent workbook and date changes can replace those rates.
  Sales and Tally rows are read only.

The financial projection uses the currently applicable rate and correction to
compute expected CN and variance. Actual receipt amounts and the expected amount
captured at receipt time stay in the receipt record. Edited workbooks retain
compact rate data and provenance. The expiring original workbook storage and
its backup exclusion still apply.
