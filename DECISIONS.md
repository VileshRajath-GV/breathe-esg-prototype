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
  * Inconsistent units (normalising `L`, `Ltr`, `Liter`, `KG`, `Kilo` dynamically).
* **Subset Ignored**: Multi-currency conversions (assumed local/functional currency is matching), complex tax components, and custom material codes (if material is not in lookup, flagged as error and assigned `confidence_score = 0`).

**Model impact**: Plant codes (`WERKS`) are resolved against `FacilityProfile` (code + name). Unresolved codes set `facility=None` and store the raw code in `facility_label`.

### B. Utility Data Ingestion
* **Ambiguity**: Utility providers rarely offer standard APIs. Facilities teams typically scrape PDF bills (highly prone to OCR errors) or pull CSV exports from their commercial billing portals.
* **Resolution**: We chose **Billing Portal CSV exports** containing `Meter_ID`, `Start_Date`, `End_Date`, and usage values.
* **Subset Handled**: 
  * Meter to Facility mapping using `FacilityProfile` (`code` field stores meter serial numbers).
  * **Fencepost date alignment**: Utility billing periods rarely match calendar months (e.g. Apr 15 to May 14). Carbon accounting requires monthly matching. We divide total usage by billing days, allocate daily, and generate independent `NormalisedEmissionRecord` rows for each calendar month — one per `(raw_row, scope, period_start)` combination.
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

* **The Ledger Audit View**: Instead of displaying just a table of numbers, the detail modal exposes the **exact raw JSON payload** from the client's uploaded file (stored in `RawIngestedRow.raw_payload`). Auditors can perform manual side-by-side reconciliation against the source.
* **Proactive Flagging over Ingestion Crashing**: If a row has an unmapped plant code or a bad date format, we **do not crash the file upload**. We ingest the row, set `review_status = NEEDS_REVIEW` and `confidence_score` accordingly, and surface it in the analyst's review panel. The analyst resolves it in-app.
* **`co2e_kg` Always in Kilograms**: All emission records store GHG impact in **kg CO₂e** regardless of scope or source. This allows safe cross-scope aggregation (`SUM(co2e_kg)`) without any unit conversion at query time. Parser-level factors (stored in tCO₂e) are multiplied by 1000 before writing to the DB.

---

## 3. Top Questions for the Product Manager (PM)

If we were to expand this prototype into a full enterprise feature, we would align on the following:
1. **Certified Emissions Factor Database**: Integrate with Climatiq, DEFRA, EPA, or GHG Protocol via API, or allow client sustainability analysts to supply custom override factors per facility via the `EmissionFactor` table?
2. **ERP Connectivity**: Build an active SAP OData Connector for direct automated sync, or keep the CSV batch export model as the preferred low-friction onboarding path?
3. **Audit Sign-off Hierarchy**: Who can transition a record from `APPROVED` to `LOCKED`? Do we need a multi-tiered approval hierarchy using the `ESGUser.role` field (Analyst drafts → Manager approves → Auditor locks)?
4. **`EmissionFactor` Governance**: When EPA/DEFRA publishes annual updates, how do we re-derive historical `co2e_kg` values for already-approved records without violating their `LOCKED` state?
