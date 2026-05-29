from datetime import datetime, date
from decimal import Decimal
from django.test import TestCase

from tenants.models import Tenant
from ingestion.models import UploadBatch, RawIngestedData
from emissions.models import FacilityLookup, NormalizedRecord
from ingestion.parsers import haversine_distance, SAPParser, UtilityParser, TravelParser

class IngestionParsersTestCase(TestCase):
    def setUp(self):
        # Setup tenants
        self.tenant_a = Tenant.objects.create(name="Tenant A")
        self.tenant_b = Tenant.objects.create(name="Tenant B")

        # Setup lookup codes for Tenant A
        FacilityLookup.objects.create(tenant=self.tenant_a, code="1000", facility_name="Plant A")
        FacilityLookup.objects.create(tenant=self.tenant_a, code="MTR-1000", facility_name="Plant A")

    def test_haversine_distance(self):
        # JFK coordinates: (40.6398, -73.7789)
        # LHR coordinates: (51.4700, -0.4543)
        dist = haversine_distance(40.6398, -73.7789, 51.4700, -0.4543)
        # Distance between JFK and LHR should be around 3440-3460 miles
        self.assertTrue(3430 < dist < 3470)

    def test_sap_diesel_calculation_and_resolution(self):
        # Create a batch
        batch = UploadBatch.objects.create(
            tenant=self.tenant_a,
            filename="sap_test.csv",
            source_type="SAP",
            status="pending"
        )
        
        # We will manually pass a mock CSV-like file path or simulate the parse using custom dataframe
        # Let's test the parser's logic directly or run it with a simple CSV mock
        import tempfile
        import os
        
        csv_content = (
            "WERKS,BUDAT,MATNR,MENGE,MEINS,DMBTR\n"
            "1000,29.05.2026,DIESEL,1000,L,2500\n" # Valid code, valid material
            "9999,29.05.2026,DIESEL,1000,L,2500\n" # Unmapped code -> Should set status='review'
        )
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            parser = SAPParser(batch)
            rows = parser.parse(temp_path)
            
            self.assertEqual(rows, 2)
            
            # Fetch generated records
            record_1 = NormalizedRecord.objects.get(raw_data__row_index=1)
            record_2 = NormalizedRecord.objects.get(raw_data__row_index=2)

            # Record 1 check (WERKS 1000 -> Plant A)
            self.assertEqual(record_1.facility, "Plant A")
            self.assertEqual(record_1.status, "validated")
            self.assertEqual(record_1.scope, "Scope 1")
            self.assertEqual(record_1.activity_type, "DIESEL")
            # 1000 L * 0.00268 factor = 2.68 tCO2e
            self.assertAlmostEqual(float(record_1.normalized_value_tco2e), 2.68)
            self.assertEqual(record_1.transaction_date, date(2026, 5, 29))

            # Record 2 check (WERKS 9999 -> Unmapped)
            self.assertEqual(record_2.facility, "Unmapped Facility (Code: 9999)")
            self.assertEqual(record_2.status, "review")
            self.assertTrue("not found in lookup table" in record_2.validation_notes)
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_utility_days_distribution(self):
        batch = UploadBatch.objects.create(
            tenant=self.tenant_a,
            filename="utility_test.csv",
            source_type="Utility",
            status="pending"
        )

        # Electricity bill crossing months: 2026-04-15 to 2026-05-14 (30 days total)
        # Usage: 3000 kWh
        # Daily average: 100 kWh
        # April has 16 days (April 15 to April 30 inclusive) -> 1600 kWh
        # May has 14 days (May 1 to May 14 inclusive) -> 1400 kWh
        csv_content = (
            "Meter_ID,Start_Date,End_Date,Usage_Value,Usage_Unit,Amount_USD\n"
            "MTR-1000,2026-04-15,2026-05-14,3000,kWh,450\n"
        )

        import tempfile
        import os
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            parser = UtilityParser(batch)
            rows = parser.parse(temp_path)
            
            # Since it crosses two months, it should generate 2 records!
            self.assertEqual(rows, 2)
            
            records = NormalizedRecord.objects.filter(batch=batch).order_by('transaction_date')
            
            # April Record
            rec_april = records[0]
            self.assertEqual(rec_april.transaction_date, date(2026, 4, 1))
            self.assertEqual(rec_april.facility, "Plant A")
            self.assertEqual(rec_april.scope, "Scope 2")
            # 16 days * 100 kWh/day = 1600 kWh
            self.assertAlmostEqual(float(rec_april.raw_value), 1600.0)
            # 1600 * 0.00042 factor = 0.672 tCO2e
            self.assertAlmostEqual(float(rec_april.normalized_value_tco2e), 0.672)

            # May Record
            rec_may = records[1]
            self.assertEqual(rec_may.transaction_date, date(2026, 5, 1))
            # 14 days * 100 kWh/day = 1400 kWh
            self.assertAlmostEqual(float(rec_may.raw_value), 1400.0)
            # 1400 * 0.00042 factor = 0.588 tCO2e
            self.assertAlmostEqual(float(rec_may.normalized_value_tco2e), 0.588)

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_multi_tenant_isolation(self):
        # Verify Facility Lookup is isolated by tenant
        FacilityLookup.objects.create(tenant=self.tenant_b, code="1000", facility_name="Plant B (Tenant B)")

        # Ingesting a record for Tenant A using plant code "1000"
        # Since Tenant A's lookup is "Plant A", it should resolve to "Plant A"
        batch_a = UploadBatch.objects.create(tenant=self.tenant_a, filename="test.csv", source_type="SAP")
        parser_a = SAPParser(batch_a)
        fac_a, resolved_a = parser_a.resolve_facility("1000")
        
        self.assertEqual(fac_a, "Plant A")
        self.assertTrue(resolved_a)

        # Tenant B's lookup for "1000" is "Plant B (Tenant B)"
        batch_b = UploadBatch.objects.create(tenant=self.tenant_b, filename="test.csv", source_type="SAP")
        parser_b = SAPParser(batch_b)
        fac_b, resolved_b = parser_b.resolve_facility("1000")

        self.assertEqual(fac_b, "Plant B (Tenant B)")
        self.assertTrue(resolved_b)
