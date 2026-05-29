import os
import django

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tenants.models import Tenant
from emissions.models import FacilityLookup

def seed():
    print("Seeding database...")
    
    # 1. Create a Default Tenant
    tenant, created = Tenant.objects.get_or_create(
        name="Breathe ESG Enterprise"
    )
    if created:
        print(f"Created default tenant: {tenant.name} (ID: {tenant.id})")
    else:
        print(f"Found existing tenant: {tenant.name} (ID: {tenant.id})")

    # 2. Seed Facility Lookups
    lookups = [
        # SAP Plant codes
        ('1000', 'Plant A'),
        ('2000', 'Plant B'),
        ('3000', 'Office C'),
        ('4000', 'Plant D'),
        ('5000', 'Plant E'),
        # Utility Meter IDs
        ('MTR-1000', 'Plant A'),
        ('MTR-2000', 'Plant B'),
        ('MTR-3000', 'Office C'),
        ('MTR-4000', 'Plant D'),
        ('MTR-5000', 'Plant E'),
    ]

    for code, name in lookups:
        lookup, created = FacilityLookup.objects.get_or_create(
            tenant=tenant,
            code=code,
            defaults={'facility_name': name}
        )
        if created:
            print(f"  Seeded lookup: {code} -> {name}")
        else:
            print(f"  Existing lookup: {code} -> {name}")

    print("Seeding completed successfully!")
    print(f"\nIMPORTANT: Your default Tenant ID is: {tenant.id}")

if __name__ == '__main__':
    seed()
