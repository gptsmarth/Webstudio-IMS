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
report. The claims table and Excel export show **NOV T2 DBP**, **Supported SRP**,
**Supported DBP**, **Support on SRP**, and **CN/Unit (expected)**. The pricing
columns are informational. IMS reads the published CN per unit and rounds to
two decimal places. Older imports may have blank pricing columns until the
original workbook is uploaded through **Replace the workbook**.

## Manage active and previous schemes

Open **Manage active scheme** or select **Manage scheme** in **Activation scheme
history**. A scheme remains editable for six calendar months after its end date.
The history keeps the filenames, date changes, and rate decisions.

- **Edit dates** changes which invoices qualify. The updated period must fit
  between existing schemes. Supplemental rates stay within the dates selected
  for them and are clipped to the new period when it is shortened.
- **Replace the workbook** supplies a new set of rates for the whole period.
  Earlier workbook and model-wide rates are superseded when the replacement is
  applied. Individual sale corrections still apply to eligible claims.
- **Add another workbook** adds new models and previews conflicts. For each
  conflicting model, retain the existing rates, use the new rate for the full
  period, or select inclusive custom dates for the new rate. Review the preview
  and choose **Apply scheme changes** to recalculate claims.

Use **Edit expected CN** on a claim to correct a single unit or the model within
an editable scheme. Add a reason before saving. An individual correction takes
precedence over the model's rate and can be removed using **Restore scheme amount**.

Scheme changes and corrections recalculate the current expected CN and check it
against the actual recorded receipt. A changed variance can reopen a resolved
discrepancy. A receipt whose sale no longer qualifies remains visible with its
original scheme reference and received amount.

## Record or import receipts

- **Mark received** opens a dialog for the actual CN amount before GST and an
  optional note. Use **Save** or **Cancel** in the dialog.
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
Use **Search all months** to look up a serial or IMEI, invoice number, or model.
**Search results Excel** exports the results for the selected status.

## Data retention and deployment

The backend reads saved Sales and Tally records without writing to billing.
The original activation workbook expires after the final sale date and five
full following days. Maintenance removes expired workbook bytes. Uploading a
new scheme also runs cleanup. Replacement and supplemental uploads are parsed
without saving the file bytes. Business backups retain the compact rules, scheme
history, corrections and receipts. Receipt imports keep record provenance.

Apply Alembic migration `0060_asus_activation_edits` with the updated backend and use
the corresponding Desktop client. See the
[database schema](../../../database/schemas/asus_activation.md) and
[API contract](../../api/openapi/webstudio-ims-api-v1.yaml).
