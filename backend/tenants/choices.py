"""
tenants/choices.py
------------------
Centralised enum definitions for the Breathe ESG platform.

Using models.TextChoices keeps values human-readable in the DB and
avoids integer drift bugs when the ordering of choices changes.
"""

from django.db import models


class UserRole(models.TextChoices):
    ADMIN   = "ADMIN",   "Admin"
    ANALYST = "ANALYST", "Analyst"
    AUDITOR = "AUDITOR", "Auditor (read-only)"


class Industry(models.TextChoices):
    MANUFACTURING   = "MANUFACTURING",   "Manufacturing"
    ENERGY          = "ENERGY",          "Energy & Utilities"
    FINANCIAL       = "FINANCIAL",       "Financial Services"
    TECHNOLOGY      = "TECHNOLOGY",      "Technology"
    RETAIL          = "RETAIL",          "Retail & Consumer"
    TRANSPORT       = "TRANSPORT",       "Transport & Logistics"
    HEALTHCARE      = "HEALTHCARE",      "Healthcare"
    OTHER           = "OTHER",           "Other"
