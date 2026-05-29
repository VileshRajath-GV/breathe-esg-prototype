# DECISIONS.md: Ambiguity Resolution & Product Decisions

This document chronicles every technical and product ambiguity encountered while building the Breathe ESG prototype, how they were resolved, and the rationale behind those choices.

---

## 1. Data Source Modeling Decisions

### A. SAP Fuel & Procurement Ingestion
* **Ambiguity**: SAP can export via OData APIs, XML IDocs, BAPIs, or flat files. Real-world enterprise SAP environments are notoriously custom, expensive, and tightly secured, making real-time API integrations a high-friction process for new client onboarding.
* **Resolution**: We chose to handle a **Flat CSV Transaction Log** export (reflecting a typical SAP ECC `BSEG` or `MSEG` table export). 
* **Subset Handled**: 
  * Columns with German SAP technical headers (`WERKS` = Plant, `BUDAT` = Posting Date, `MATNR` = Material, `MENGE` = Qty, `MEINS` = Unit, `DMBTR` = Local currency cost).
  * Date formats in German notation (`DD.MM.YYYY`).
  * Inconsistent units (normalizing `L`, `Ltr`, `Liter`, `KG`, `Kilo` dynamically).
* **Subset Ignored**: Multi-currency conversions (assumed local/functional currency is matching), complex tax components, and custom material codes (if material is not in lookup, we flag as error and assign confidence score `0` rather than attempting guessing).

### B. Utility Data Ingestion
* **Ambiguity**: Utility providers rarely offer standard APIs. Facilities teams typically scrape PDF bills (highly prone to OCR errors) or pull CSV exports from their commercial billing portals.
* **Resolution**: We chose **Billing Portal CSV exports** containing `Meter_ID`, `Start_Date`, `End_Date`, and usage values.
* **Subset Handled**: 
  * Meter to Facility mapping using `FacilityLookup`.
  * **Fencepost date alignment**: Utility billing periods rarely match calendar months (e.g. Apr 15 to May 14). Carbon accounting requires monthly matching. We divide total usage by billing days, allocate the usage daily, and generate independent normalized records for each calendar month representing the exact allocated consumption.
  * Unit discrepancies (`kWh` vs `MWh`).
* **Subset Ignored**: Complex tariff components (active vs reactive power, peak-demand surcharge fees, solar grid feeding-in credits). We focused strictly on active power consumption.

### C. Corporate Travel (Concur/Navan JSON)
* **Ambiguity**: Flights, hotels, and ground transport involve drastically different calculations. Flights are often logged without miles (only origin/destination airport codes like `JFK` or `LHR`). Cabin class (economy vs business) drastically affects footprint.
* **Resolution**: We designed a mock **Navan/Concur travel booking JSON payload**.
* **Subset Handled**:
  * **Airport distance calculation**: If `distance_miles` is omitted, the parser uses a **Haversine formula** (Great Circle Distance) mapping coordinates of major international airport hubs.
  * Flight distance-bracket adjustments: short-haul (<300 miles) vs long-haul (>=300 miles) have different DEFRA radiative forcing factors.
  * Cabin class multipliers (Business class gets a `1.5x` multiplier, First class gets `2.0x` to account for larger physical space allocation on flights).
  * Hotel stays normalized using room-nights.
* **Subset Ignored**: Indirect radiative forcing multipliers from cruise ships, flight layover details, and vehicle make/model for ground transit (we apply a general vehicle class multiplier instead).

---

## 2. Rationale behind Product UX Choices

* **The Ledger Audit View**: Instead of displaying just a table of numbers, the detail modal in our React UI exposes the **Exact Raw JSON Payload** from the client's uploaded file. Auditors are deeply suspicious of "black-box" normalization. Exposing the original row allows manual side-by-side reconciliation.
* **Proactive Flagging over Ingestion Crashing**: If a row has an unmapped plant code or a bad date format, we **do not crash the file upload**. Rejecting a 10,000-row file because row 9,842 has an error is a horrible client experience. Instead, we ingest the row, set its status to `review` or `error`, and surface it in the analyst’s review panel with a quality flag. The analyst can correct or resolve it in-app.

---

## 3. Top Questions for the Product Manager (PM)

If we were to expand this prototype into a full enterprise feature, we would align on the following:
1. **Target Emissions Engine**: Do we need to integrate with a certified emissions factor database (e.g. Climatiq, DEFRA, EPA, or GHG Protocol) via API, or will client sustainability analysts provide their own custom override factors per facility?
2. **ERP Connectivity**: Should we develop an active SAP OData Connector for direct automated sync, or is the CSV batch export model the preferred onboarding friction-reducer?
3. **Audit Ledger Sign-off Hierarchy**: Once a record is locked, who is authorized to unlock it? Do we need a multi-tiered approval hierarchy (e.g., Analyst drafts, Manager approves, Auditor locks)?
