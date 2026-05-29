"""
ingestion/choices.py
--------------------
Enum definitions for data ingestion pipeline statuses and source types.
"""

from django.db import models


class SourceType(models.TextChoices):
    SAP     = "SAP",     "SAP (Fuel & Procurement)"
    UTILITY = "UTILITY", "Utility (Electricity Bills)"
    TRAVEL  = "TRAVEL",  "Corporate Travel"


class BatchStatus(models.TextChoices):
    PENDING    = "PENDING",    "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED  = "COMPLETED",  "Completed"
    FAILED     = "FAILED",     "Failed"
