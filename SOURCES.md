# SOURCES.md: Real-World Formats, Learnings & Technical Failure Modes

This document details the real-world data shapes researched for the Breathe ESG prototype, our mock data structure design, and what would fail in a production environment.

---

## 1. SAP Fuel & Procurement Data (Scope 1 & 3)

### A. Real-World Format Researched
In corporate environments, SAP ECC or S/4HANA stores transaction items in table views (like `BSEG` for accounting items or `MSEG` for material documents). Legacy configurations (especially in multinational manufacturing firms founded or headquartered in Europe) frequently retain technical German headers.

* **German Header Column Mapping**:
  * `WERKS`: Plant/Factory Code (e.g. `1000`, `2000`).
  * `BUDAT`: Posting Date (e.g. `29.05.2026`).
  * `MATNR`: Material Number/Description (e.g. `DIESEL`, `STEEL`).
  * `MENGE`: Quantity (e.g. `45000.00`).
  * `MEINS`: Base Unit of Measure (e.g. German `Ltr` or `KG`).
  * `DMBTR`: Amount in Local Currency (e.g. cost).

### B. Our Sample Data Structure
Our parser expects a flat CSV conforming to this structure:
```csv
WERKS,BUDAT,MATNR,MENGE,MEINS,DMBTR
1000,29.05.2026,DIESEL,1500,L,3200
2000,28.05.2026,STEEL,500,KG,4500
3000,27.05.2026,PLASTIC,2000,KILO,8000
4000,29.05.2026,PETROL,800,Ltr,1800
```
* **Why**: It mimics the German standard export format commonly found in SAP financial ledgers, ensuring the parser handles messy unit variations (`L`, `Ltr`, `LITER`, `KG`, `Kilo`) and German date formatting (`DD.MM.YYYY`).

### C. What Breaks in Production
* **Custom SAP Materials**: In a real SAP deployment, material records are integers (e.g., `MATNR` `000000000000109281` representing a specific type of fuel). A mapping lookup sheet must be maintained in Django to translate these integer SKUs into carbon activity categories.
* **Bad Unicode/Delimiters**: SAP exports frequently use semi-colons (`;`) or tab delimiters instead of commas, along with messy European number notations (e.g. using `.` for thousands and `,` for decimals: `1.500,50 L`). A production parser needs highly customizable regex normalization.

---

## 2. Utility Electricity Data (Scope 2)

### A. Real-World Format Researched
Commercial facilities teams download historical energy invoices from online portals (e.g., PG&E, National Grid, or ConEd billing portals) in flat CSVs. These billing cycles are based on physical meter reads and rarely align with calendar months.

* **Key Columns**:
  * `Meter_ID`: Serial number of the physical electric meter.
  * `Start_Date`: Cycle start day.
  * `End_Date`: Cycle billing end day.
  * `Usage_Value`: Active power consumed.
  * `Usage_Unit`: Billing units (typically `kWh` or `MWh`).

### B. Our Sample Data Structure
Our parser expects a flat CSV conforming to this structure:
```csv
Meter_ID,Start_Date,End_Date,Usage_Value,Usage_Unit,Amount_USD
MTR-1000,2026-04-15,2026-05-14,3000,kWh,450
MTR-2000,2026-04-01,2026-04-30,4.5,MWh,675
MTR-9999,2026-05-01,2026-05-31,1200,kWh,180
```
* **Why**: This represents a typical portal download. It tests the engine's ability to map meter numbers (`MTR-1000` -> `Plant A`), handle multiple units (`kWh` vs `MWh`), and run daily-average calendar-month splits.

### C. What Breaks in Production
* **Meter Swaps**: If a facility swaps physical electric meters during a billing cycle, two different `Meter_ID` rows will appear with overlapping periods, causing double-counting if the lookups are not version-controlled.
* **Estimated Bills**: Utilities frequently estimate bills for months where a reader could not access the meter, followed by a correction bill. If an analyst uploads the correction file, past months' databases must be retroactively corrected without violating locked audit states.

---

## 3. Corporate Travel platform (Scope 3, Category 6)

### A. Real-World Format Researched
Platforms like Concur or Navan expose booking details via webhook JSON payloads or scheduled CSV downloads. Flight records contain airport codes but lack distance metrics.

* **Key Keys**:
  * `type`: Flight, Hotel, Train, or Car.
  * `origin_airport` / `destination_airport`: 3-character IATA codes (e.g. `JFK`, `LHR`).
  * `class`: Economy, Business, or First.
  * `room_nights`: Duration of hotel booking.

### B. Our Sample Data Structure
Our parser expects a JSON array representing booking objects:
```json
[
  {
    "booking_id": "T-88219",
    "employee_email": "johndoe@breatheesg.com",
    "type": "flight",
    "origin_airport": "JFK",
    "destination_airport": "LHR",
    "distance_miles": null,
    "class": "business",
    "booking_date": "2026-05-28"
  },
  {
    "booking_id": "T-99821",
    "employee_email": "janesmith@breatheesg.com",
    "type": "hotel",
    "room_nights": 4,
    "booking_date": "2026-05-25"
  }
]
```
* **Why**: This mimics a direct booking platform API payload. It tests the engine's Haversine formula calculation for flights, IATA code coordinate mappings, business-class weight multipliers, and hotel night calculations.

### C. What Breaks in Production
* **Layover Flights**: If a flight booking has multiple legs (e.g. `JFK -> LHR -> SIN`), treating it as a simple great-circle distance `JFK -> SIN` will significantly underestimate the actual flight mileage and emissions.
* **Unmapped Airport Codes**: Regional airports frequently change IATA codes or introduce new ones. A production engine needs a fallback connection to an active IATA directory database.
