# TRADEOFFS.md: Deliberate Scoping & Exclusions

To deliver a high-quality, auditable, and mathematically rigorous prototype, we deliberately chose to exclude three complex features, opting instead for robust, standard-conforming designs.

---

## 1. No PDF OCR Utility Bill Parsing
* **Why it was excluded**: Facilities teams often suggest parsing PDF invoices directly using OCR (Optical Character Recognition) tools like Tesseract or AWS Textract. However, utility layouts are notorious for changing formats without notice. Even a tiny OCR error (e.g., misreading a `1` as a `7` or missing a decimal point) causes massive, silent reporting errors that fail audit standards.
* **Our Alternative Choice**: We chose to ingest **Portal CSV Billing Exports**. Billing portals already provide structured, clean text databases. This is the industry-preferred onboarding mechanism for enterprise clients because it is 100% accurate and mathematically reliable.

---

## 2. No Live Third-Party Emissions Factor API Sync
* **Why it was excluded**: Connecting to external live carbon factor APIs (like Climatiq or UK DEFRA) introduces massive external dependencies. If the external service goes down, ingestion freezes. More importantly, emissions factors change annually; a live, automatic sync can silently change historical emissions calculations, violating audit baseline locking standards.
* **Our Alternative Choice**: We built an **Internal Static Emissions Factor Register** within our ingestion parsers. This ensures consistent, deterministic calculations. Factors are version-controlled and tied to specific ingestion batches, satisfying auditors who require absolute reproducibility.

---

## 3. No Multi-Tiered Role-Based Access Control (RBAC) & Custom Workflows
* **Why it was excluded**: Building complex workflow routing (e.g., "Sustainability Specialist uploads -> Sustainability Manager reviews -> Director signs off -> Auditor locks") involves significant database and state-machine overhead. For a prototype, building a fully generic RBAC engine takes time away from refining the core data models and normalization logic.
* **Our Alternative Choice**: We designed a streamlined **Immutable Audit Lock (`is_locked`)** model accompanied by an automatic `AuditTrail` ledger. Every analyst action (approval, flagging, rejecting) is recorded in a flat history database. This satisfies the core security and compliance requirements without introducing unnecessary workflow complexity.
