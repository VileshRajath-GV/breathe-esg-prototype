import os
import sys
import django

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.append(backend_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tenants.models import Tenant
from ingestion.models import UploadBatch
from ingestion.parsers import SAPParser, UtilityParser, TravelParser


def main():
    tenant = Tenant.objects.first()
    if not tenant:
        print("Error: No tenant found. Run seed.py first.")
        return

    print(f"Uploading samples for Tenant: {tenant.name} ({tenant.id})")

    samples = [
        ('SAP',     'backend_sap_export.csv'),
        ('UTILITY', 'portal_utility_export.csv'),
        ('TRAVEL',  'concur_travel_export.json'),
    ]

    for source_type, filename in samples:
        filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), filename))
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue

        print(f"Processing {source_type} from {filename}...")

        # Clean up previous test batches for idempotent re-runs
        old_batches = UploadBatch.objects.filter(tenant=tenant, external_ref=filename)
        for ob in old_batches:
            from emissions.models import NormalisedEmissionRecord
            from ingestion.models import RawIngestedRow
            NormalisedEmissionRecord.objects.filter(batch=ob).delete()
            RawIngestedRow.objects.filter(batch=ob).delete()
        old_batches.delete()

        batch = UploadBatch.objects.create(
            tenant         = tenant,
            name           = filename,
            external_ref   = filename,
            source_type    = source_type,
            status         = 'PROCESSING',
            reporting_year = 2024,
        )

        try:
            if source_type == 'SAP':
                rows = SAPParser(batch).parse(filepath)
            elif source_type == 'UTILITY':
                rows = UtilityParser(batch).parse(filepath)
            elif source_type == 'TRAVEL':
                rows = TravelParser(batch).parse_file(filepath)

            batch.status    = 'COMPLETED'
            batch.row_count = rows
            batch.save()
            print(f"  OK: {rows} rows processed successfully")
        except Exception as e:
            batch.status        = 'FAILED'
            batch.error_summary = {'error': str(e)}
            batch.save()
            print(f"  FAILED: {e}")


if __name__ == '__main__':
    main()
