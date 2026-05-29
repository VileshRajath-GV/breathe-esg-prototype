"""
tenants/models.py
-----------------
Multi-tenant root models for the Breathe ESG platform.

Design decisions
~~~~~~~~~~~~~~~~
* Tenant  — top-level boundary; every row in the system is scoped to one.
  ``slug`` is a URL-safe identifier so PKs are never exposed in routes.
  ``active_reporting_year`` lets the UI default to the year being worked on.

* ESGUser — org-scoped custom user extending Django's auth machinery.
  A user belongs to exactly one tenant. Cross-tenant access (e.g. auditors
  spanning multiple clients) is intentionally out of scope for this version.
  ``on_delete=PROTECT`` on the tenant FK prevents accidental cascade deletes
  of compliance data.
"""

import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from .choices import UserRole, Industry


# ─────────────────────────────────────────────
# 1. Tenant  (multi-tenant root / organisation)
# ─────────────────────────────────────────────

class Tenant(models.Model):
    """
    Top-level tenant boundary — the organisation reporting ESG data.

    ``slug`` is derived from the name and used in API routes instead of
    the UUID PK, preventing enumeration of tenant IDs.
    ``industry`` enables sector-specific emission factor defaults in future.
    """
    id                    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name                  = models.CharField(max_length=255, unique=True)
    slug                  = models.SlugField(max_length=100, unique=True,
                                             help_text="URL-safe identifier, e.g. 'acme-corp'")
    country               = models.CharField(max_length=100, blank=True)
    industry              = models.CharField(
        max_length=50, choices=Industry.choices,
        default=Industry.OTHER, blank=True
    )
    # Which reporting year the tenant is currently working on
    active_reporting_year = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="e.g. 2024 — used as the default year in UI filters"
    )
    created_at            = models.DateTimeField(auto_now_add=True)
    is_active             = models.BooleanField(default=True)

    class Meta:
        db_table = "org_tenant"

    def __str__(self) -> str:
        return self.name


# ─────────────────────────────────────────────
# 2. ESGUser  (role-based, tenant-scoped)
# ─────────────────────────────────────────────

class ESGUserManager(BaseUserManager):
    """Custom manager so ``create_user`` / ``create_superuser`` work with email auth."""

    def create_user(self, email: str, password: str = None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class ESGUser(AbstractBaseUser, PermissionsMixin):
    """
    Platform user. Email is the login identifier.

    ``role`` controls what actions are permitted in the review workflow:
      ANALYST — can submit data, flag records, approve their own submissions
      ADMIN   — can lock records for audit, manage users within their tenant
      AUDITOR — read-only access; can add comments but not change status
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant     = models.ForeignKey(
        Tenant, on_delete=models.PROTECT, related_name="users",
        null=True, blank=True,
        help_text="Null only for Django superusers not tied to a tenant"
    )
    email      = models.EmailField(unique=True)
    full_name  = models.CharField(max_length=255, blank=True)
    role       = models.CharField(
        max_length=20, choices=UserRole.choices, default=UserRole.ANALYST
    )
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False,
                                     help_text="Grants Django admin site access")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ESGUserManager()

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "org_esg_user"
        indexes  = [
            models.Index(fields=["tenant", "role"], name="idx_user_tenant_role"),
        ]

    def __str__(self) -> str:
        return f"{self.email} [{self.role}]"
