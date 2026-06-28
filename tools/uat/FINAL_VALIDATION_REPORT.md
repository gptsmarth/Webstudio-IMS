# WEBSTUDIO IMS — Final Validation Report

## XML Summary
- Company: WEBSTUDIO - (from 1-Apr-2022) - (from 1-Apr-25) - (from 1-Apr-26)
- Vouchers: 7
- Voucher types: {'Sales': 4, 'NEW SALE': 3}
- Inventory lines: 8

## Product Models Created
- A325-45-V2: 0f46f413-0177-4ecb-9f7c-288156edd2f6
- L27-4C: c9087db8-9353-4188-bafd-d5f75fead47c
- E1504FA-BQ2113WS: 67fdfae6-0245-4489-b0af-636ae5b6bedd
- ADAPTER-45W: 0da03565-a4bd-41b2-9242-47addabf7ac1
- L3350: 5c7510b1-bb4d-481b-bbcd-0d29445a7e1f
- MD102: 2f80386c-bc71-4ab2-89bb-54f93dbd5f27
- X1502ZA-EJ541WS: 96aef052-1534-478a-80ed-935af462ad63

## Inventory Serials
- SCBMCP0036075P5: 210efd38-d72a-41b4-a542-4c549e09876a
- SCENARIO-DUP-MODEL-001: 3045abb3-4343-433e-96bf-e66eb9580a77
- SCENARIO-NEW-MODEL-001: 99e11e44-72b8-4fae-8455-89e40609a201
- SCENARIO-NEW-MODEL-002: 70b65239-b4c8-4da1-a620-01565de8bc79
- SCENARIO-NEW-MODEL-003: 988e15b8-c10c-470a-863f-a218c1c8d257
- T7BCXB003887STA: 86177c3c-1cd7-4245-abb4-dce8d5e85908
- TEST001: 20c84b84-350c-43a3-9c52-ce7444431310
- TEST002: 990fad14-73e8-4e53-98f7-bb56ca05b803
- TEST003: a46eca90-3eea-4907-b29e-45cffcf29ee0
- UN36FSI00B613004C20700: 73998303-4a3d-4037-8319-b9fe3224be4b
- UT10082A: 2c01be52-42f4-49a6-aa53-74a05d007b75
- W3N0CV09678412A: 0006d60d-9c58-4baa-aa97-95dc075270f0
- XFAL007602: 8469b3c1-2c2f-43b9-9e41-ebf8f2fc1129

## Gemini
- Success: 2
- Skipped (existing): 3
- Failed/graceful: 4

## Sync Duration
- Run 1: 0.15s
- Run 2: 0.06s

## PASS Summary
- ✓ Phase 1 analysis saved to /Users/smarthsingh/Desktop/WEBSTUDIO IMS/tools/uat/phase1_analysis.txt
- ✓ First-time setup completed via API (ARVIND SINGH / admin)
- ✓ Locations ready: Warehouse=2, WEBSTUDIO=3, AES=4
- ✓ Tally settings patched via API
- ✓ Gemini enrichment succeeded for A325-45-V2
- ✓ Created product model A325-45-V2
- ✓ Created inventory UN36FSI00B613004C20700 at Warehouse
- ✓ Created inventory TEST001 at Warehouse
- ✓ Created inventory TEST002 at Warehouse
- ✓ Created inventory TEST003 at Warehouse
- ✓ Created product model L27-4C
- ✓ Created inventory UT10082A at Warehouse
- ✓ Gemini enrichment succeeded for E1504FA-BQ2113WS
- ✓ Created product model E1504FA-BQ2113WS
- ✓ Created inventory W3N0CV09678412A at Warehouse
- ✓ Created product model ADAPTER-45W
- ✓ Created inventory T7BCXB003887STA at Warehouse
- ✓ Created product model L3350
- ✓ Created inventory XFAL007602 at Warehouse
- ✓ Created product model MD102
- ✓ Created inventory SCBMCP0036075P5 at Warehouse
- ✓ Reused existing product model E1504FA-BQ2113WS
- ✓ Created inventory SCENARIO-DUP-MODEL-001 at Warehouse
- ✓ Scenario: reusing product model without duplication — PASS
- ✓ Reused existing product model X1502ZA-EJ541WS
- ✓ Created inventory SCENARIO-NEW-MODEL-001 at Warehouse
- ✓ Created inventory SCENARIO-NEW-MODEL-002 at Warehouse
- ✓ Reused existing product model X1502ZA-EJ541WS
- ✓ Created inventory SCENARIO-NEW-MODEL-003 at Warehouse
- ✓ Edit laptop — PASS
- ✓ Transfer laptop — PASS
- ✓ Archive laptop — PASS
- ✓ Restore laptop — PASS
- ✓ Search & pagination — PASS
- ✓ Inventory report XLSX export — PASS
- ✓ Inventory report PDF export — PASS
- ✓ Tally integration enabled in settings
- ✓ Phase 5 first XML replay: vouchers=7 sales=6 dupes=0 missing_serials=0
- ✓ Sales imported: 6
- ✓ Tally dashboard updated — PASS
- ✓ Phase 7 duplicate XML replay: vouchers=7 sales=0 dupes=0 missing_serials=0
- ✓ Duplicate protection on second replay — PASS
- ✓ User sunaina (admin) ready
- ✓ Login test sunaina — PASS
- ✓ User hemant (salesperson) ready
- ✓ Login test hemant — PASS
- ✓ Admin role — inventory access PASS
- ✓ Admin role — user management blocked PASS
- ✓ Salesperson — inventory access PASS
- ✓ Salesperson — user management blocked PASS
- ✓ Salesperson — settings blocked PASS
- ✓ Audit logs present (55 entries)
- ✓ Dashboard loads — PASS
- ✓ Notifications — 4 entries
- ✓ Report preview inventory — PASS
- ✓ Report preview sales — PASS
- ✓ Report preview audit — PASS
- ✓ Report preview notifications — PASS

## Warnings
- ⚠ Gemini enrichment unavailable for L27-4C: 500
- ⚠ Inventory serial already exists: TEST001
- ⚠ Inventory serial already exists: TEST002
- ⚠ Inventory serial already exists: TEST003
- ⚠ Inventory serial already exists: TEST001
- ⚠ Inventory serial already exists: TEST002
- ⚠ Inventory serial already exists: TEST003
- ⚠ Gemini enrichment unavailable for ADAPTER-45W: 500
- ⚠ Gemini enrichment unavailable for L3350: 429
- ⚠ Gemini enrichment unavailable for MD102: 500
- ⚠ Inventory serial already exists: W3N0CV09678412A
- ⚠ Inventory serial already exists: SCENARIO-NEW-MODEL-001

## Failures
- None

## Test Credentials

| Name | Username | Password | Role | Login Tested |
|------|----------|----------|------|--------------|
| ARVIND SINGH | admin | WsiUat#Admin2026!Arv | main_admin | Yes |
| Sunaina | sunaina | WsiUat#Sunaina2026! | admin | Yes |
| Hemant | hemant | WsiUat#Hemant2026! | salesperson | Yes |
