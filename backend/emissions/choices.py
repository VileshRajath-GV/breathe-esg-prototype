"""
emissions/choices.py
---------------------
Enum definitions for GHG scopes, review workflow statuses, and
normalised measurement units used across the Breathe ESG platform.
"""

from django.db import models


class EmissionScope(models.TextChoices):
    SCOPE_1 = "SCOPE_1", "Scope 1 — Direct"
    SCOPE_2 = "SCOPE_2", "Scope 2 — Indirect (Energy)"
    SCOPE_3 = "SCOPE_3", "Scope 3 — Value Chain"


class ReviewStatus(models.TextChoices):
    """
    State machine for the analyst review workflow.

    Transitions:
        NEEDS_REVIEW → AUTO_APPROVED  (pipeline confidence ≥ 80)
        NEEDS_REVIEW → APPROVED       (analyst manual approval)
        AUTO_APPROVED → APPROVED      (analyst override)
        APPROVED / AUTO_APPROVED → REJECTED → NEEDS_REVIEW (analyst reset)
        APPROVED → LOCKED             (admin audit lock — terminal state)
    """
    NEEDS_REVIEW   = "NEEDS_REVIEW",   "Needs Review"
    AUTO_APPROVED  = "AUTO_APPROVED",  "Auto-Approved"
    APPROVED       = "APPROVED",       "Approved"
    REJECTED       = "REJECTED",       "Rejected"
    LOCKED         = "LOCKED",         "Locked (Audited)"


class NormalisedUnit(models.TextChoices):
    KG_CO2E    = "kg_CO2e", "Kilograms CO₂-equivalent"
    TONNE_CO2E = "tCO2e",   "Metric Tonnes CO₂-equivalent"
    KWH        = "kWh",     "Kilowatt-hours"
    MJ         = "MJ",      "Megajoules"
    LITRE      = "L",       "Litres"
    KM         = "km",      "Kilometres"
