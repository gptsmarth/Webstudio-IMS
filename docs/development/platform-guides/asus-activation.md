# Asus Activation

Open **Asus Activation** from the Desktop sidebar. Report export permission grants
access to claims and Excel downloads. Settings modify permission also grants scheme
uploads, receipt imports and discrepancy resolution.

## Upload schemes

Choose the inclusive **From date** and **To date** and upload the ASUS activation
`.xlsx`. The selected dates control eligibility in India time. The workbook's
programme text is retained for reference. The same exact file and range can be
uploaded again safely. A conflicting range is rejected so each sale has one
applicable scheme.

The importer searches worksheets with recognizable model and CN per unit
columns. **Gaming Price List** supplies the gaming rates and **Gaming T3** is
skipped. Positive rates for ASUS devices sold through IMS can apply, including
AIO, Ally and other supported model types. The system matches the full model
number from the saved sale. This also covers a model added to inventory after
the scheme was uploaded. Accessories are excluded.

A saved sale appears under its **invoice month** when a matching scheme covers
the invoice date. Uploading a scheme late adds qualifying sales already
recorded in that range, including expired periods. The upload confirmation shows
the number of matching sales and opens Pending Claims in the scheme's first month.
The displayed sale price is the unit price including
GST from the same saved sale or archived Tally line used by the ASUS weekly
report. The sale price and Supported SRP are informational. The expected claim
is the workbook's CN per unit, rounded to two decimals. The claims view refreshes
periodically and also has a Refresh button.

## Record or import receipts

- **Record received** accepts the actual CN amount before GST and an optional note.
- **Preview receipts** reads `CN Amt`, `Model_Name`, `IMEI` and `Release Date`.
  It uses the programme code in `Scheme` when both sources identify it.
  The preview shows exact matches, amount discrepancies, and rows it will
  skip. Choose **Yes, confirm receipts** to apply the preview. If a claim has
  changed since preview, refresh the preview before confirming.
- An exact amount match moves to **Received**. A difference goes to
  **Discrepancies** with both amounts. **Resolve** requires an explanatory
  note and preserves the original amount and variance.
- A duplicate or already settled record is skipped. Unmatched rows and multiple
  competing receipts for one sale require review. If the relevant sale month
  lacks a scheme, upload it and preview the receipt file again.

Choose **Pending Claims**, **Discrepancies**, **Received** or **All Claims**, then
choose **Month Excel** or **All months Excel**. The workbook includes invoice and
customer data, the exact model and serial, unit price, scheme dates, expected and
received CN, variance, the receipt file and release date, and resolution notes.

## Data retention and deployment

The backend reads saved Sales and Tally records without writing to billing.
The original activation workbook expires after the final sale date and five
full following days. Maintenance removes expired workbook bytes. Uploading a
new scheme also runs cleanup. Business backups retain compact scheme rules and
receipts. Temporary source workbooks are excluded. Receipt imports keep record
provenance, without retaining the original receipt file.

Apply Alembic migration `0059_asus_activation` with the updated backend and use
the corresponding Desktop client. See the
[database schema](../../../database/schemas/asus_activation.md) and
[API contract](../../api/openapi/webstudio-ims-api-v1.yaml).
