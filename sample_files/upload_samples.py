import os
import sys
import django

# Add backend directory to sys.path so django settings can be loaded
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.append(backend_dir)

# Setup Django Environment
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
        ('SAP', 'backend_sap_export.csv'),
        ('Utility', 'portal_utility_export.csv'),
        ('Travel', 'concur_travel_export.json')
    ]
    
    for source_type, filename in samples:
        # Since this script is now in the sample_files folder, files are in the same folder!
        filepath = os.path.join(os.path.dirname(__file__), filename)
        filepath = os.path.abspath(filepath)
        
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue
            
        print(f"Processing {source_type} from {filename}...")
        
        # Clean up any existing batches for this file to ensure clean seeding
        UploadBatch.objects.filter(tenant=tenant, filename=filename).delete()
        
        # Create UploadBatch
        batch = UploadBatch.objects.create(
            tenant=tenant,
            filename=filename,
            source_type=source_type,
            status='processing'
        )
        
        try:
            if source_type == 'SAP':
                parser = SAPParser(batch)
                rows = parser.parse(filepath)
            elif source_type == 'Utility':
                parser = UtilityParser(batch)
                rows = parser.parse(filepath)
            elif source_type == 'Travel':
                parser = TravelParser(batch)
                rows = parser.parse_file(filepath)
                
            batch.status = 'completed'
            batch.row_count = rows
            batch.save()
            print(f"  Successfully processed {rows} rows!")
        except Exception as e:
            batch.status = 'failed'
            batch.error_summary = str(e)
            batch.save()
            print(f"  Failed: {e}")

if __name__ == '__main__':
    main()
