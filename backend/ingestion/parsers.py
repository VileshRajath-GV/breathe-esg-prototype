import csv
import json
import math
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd

from tenants.models import Tenant
from ingestion.models import UploadBatch, RawIngestedData
from emissions.models import FacilityLookup, NormalizedRecord

# Major airports and their lat/lon for Great Circle Distance (Haversine)
AIRPORT_COORDINATES = {
    'JFK': (40.6398, -73.7789),
    'LHR': (51.4700, -0.4543),
    'CDG': (49.0097, 2.5479),
    'SFO': (37.6190, -122.3748),
    'LAX': (33.9416, -118.4085),
    'FRA': (50.0379, 8.5622),
    'SIN': (1.3502, 103.9944),
    'HND': (35.5494, 139.7798),
    'DXB': (25.2532, 55.3657),
    'AMS': (52.3081, 4.7642),
}

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the great-circle distance between two points on the Earth in miles.
    """
    R = 3958.8  # Earth radius in miles
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class BaseParser:
    def __init__(self, batch: UploadBatch):
        self.batch = batch
        self.tenant = batch.tenant

    def resolve_facility(self, code):
        """
        Attempts to resolve code (like plant code or meter number) to a facility name.
        Returns a tuple: (resolved_facility_name, exists_in_lookup)
        """
        try:
            lookup = FacilityLookup.objects.get(tenant=self.tenant, code=code)
            return lookup.facility_name, True
        except FacilityLookup.DoesNotExist:
            return f"Unmapped Facility (Code: {code})", False

class SAPParser(BaseParser):
    """
    Parses German/ECC SAP Flat CSV exports.
    Expected Columns:
    - WERKS: Plant Code
    - BUDAT: Posting Date (Format: DD.MM.YYYY)
    - MATNR: Material/Fuel Identifier (e.g., 'DIESEL', 'STEEL')
    - MENGE: Quantity
    - MEINS: Unit of Measure (e.g. L, Ltr, Liter, KG, Kilo)
    - DMBTR: Cost in local currency (USD/EUR)
    """
    
    GERMAN_HEADERS = {
        'WERKS': 'plant_code',
        'BUDAT': 'date',
        'MATNR': 'material',
        'MENGE': 'quantity',
        'MEINS': 'unit',
        'DMBTR': 'cost'
    }

    # Emission Factors (tCO2e per raw unit)
    EMISSION_FACTORS = {
        'DIESEL': {'unit': 'Liters', 'factor': 0.00268, 'scope': 'Scope 1', 'category': 'Stationary Combustion'},
        'PETROL': {'unit': 'Liters', 'factor': 0.00231, 'scope': 'Scope 1', 'category': 'Stationary Combustion'},
        'STEEL': {'unit': 'Kilograms', 'factor': 0.00185, 'scope': 'Scope 3', 'category': 'Purchased Goods and Services'},
        'PLASTIC': {'unit': 'Kilograms', 'factor': 0.00192, 'scope': 'Scope 3', 'category': 'Purchased Goods and Services'},
        'PAPER': {'unit': 'Kilograms', 'factor': 0.00095, 'scope': 'Scope 3', 'category': 'Purchased Goods and Services'},
    }

    def parse(self, file_path):
        # Read with pandas to handle headers easily
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            raise ValueError(f"Failed to read CSV file: {str(e)}")

        # Clean column names (strip spaces, uppercase)
        df.columns = [c.strip().upper() for c in df.columns]

        # Verify minimum required columns (can be in German or standard English)
        required = set(self.GERMAN_HEADERS.keys())
        missing = required - set(df.columns)
        if missing:
            # Let's support English headers too in case they converted them
            english_mapping = {v.upper(): k for k, v in self.GERMAN_HEADERS.items()}
            # If all English equivalents are present, rename them back to German
            if set(english_mapping.keys()).issubset(set(df.columns)):
                df = df.rename(columns=english_mapping)
            else:
                raise ValueError(f"Missing required columns in SAP file: {', '.join(missing)}")

        records_created = 0
        
        for idx, row in df.iterrows():
            raw_row = row.to_dict()
            # Convert NaN to None for clean JSON serialization
            raw_row_cleaned = {k: (None if pd.isna(v) else v) for k, v in raw_row.items()}

            # 1. Save Raw Ingested Data for Audit
            raw_data = RawIngestedData.objects.create(
                batch=self.batch,
                row_index=idx + 1,
                raw_payload=raw_row_cleaned
            )

            try:
                # Extract values
                raw_werks = str(raw_row_cleaned.get('WERKS', '')).strip()
                raw_budat = str(raw_row_cleaned.get('BUDAT', '')).strip()
                raw_matnr = str(raw_row_cleaned.get('MATNR', '')).strip().upper()
                raw_menge_str = str(raw_row_cleaned.get('MENGE', '0')).replace(',', '').strip()
                raw_meins = str(raw_row_cleaned.get('MEINS', '')).strip().upper()

                # Parse quantities
                raw_menge = Decimal(raw_menge_str) if raw_menge_str else Decimal('0')

                # Parse Date (Handle DD.MM.YYYY format)
                try:
                    transaction_date = datetime.strptime(raw_budat, '%d.%m.%Y').date()
                    date_valid = True
                except ValueError:
                    # Fallback to standard YYYY-MM-DD
                    try:
                        transaction_date = datetime.strptime(raw_budat, '%Y-%m-%d').date()
                        date_valid = True
                    except ValueError:
                        transaction_date = datetime.today().date()
                        date_valid = False

                # Map units
                normalized_unit = raw_meins
                if raw_meins in ['L', 'LTR', 'LITER', 'LITERS']:
                    normalized_unit = 'Liters'
                elif raw_meins in ['KG', 'KILO', 'KILOGRAM', 'KILOGRAMS']:
                    normalized_unit = 'Kilograms'

                # Resolve Facility
                facility_name, resolved = self.resolve_facility(raw_werks)

                # Emissions factors lookup
                factor_info = self.EMISSION_FACTORS.get(raw_matnr)
                
                validation_notes = []
                confidence_score = 100
                status = 'validated'

                if not resolved:
                    validation_notes.append(f"WERKS Code '{raw_werks}' not found in lookup table.")
                    confidence_score -= 20
                    status = 'review'

                if not date_valid:
                    validation_notes.append(f"Invalid date format '{raw_budat}'. Defaulted to today.")
                    confidence_score -= 30
                    status = 'error'

                if not factor_info:
                    validation_notes.append(f"Unknown material/fuel category '{raw_matnr}'. Cannot calculate emissions.")
                    confidence_score -= 50
                    status = 'error'
                    tco2e = Decimal('0')
                    scope = 'Scope 3'
                    category = 'Purchased Goods and Services'
                else:
                    scope = factor_info['scope']
                    category = factor_info['category']
                    # Calculate emissions
                    # Apply unit compatibility checks
                    if factor_info['unit'] != normalized_unit:
                        validation_notes.append(f"Unit mismatch: Expected {factor_info['unit']}, got {normalized_unit}. Applying raw multiplication.")
                        confidence_score -= 15
                        status = 'review'
                    
                    tco2e = Decimal(str(factor_info['factor'])) * raw_menge

                # Anomaly detection: extremely high cost or quantity
                if raw_menge > 100000:
                    validation_notes.append("Anomaly detected: Unusually large fuel/procurement quantity (>100k).")
                    confidence_score -= 10
                    status = 'review'

                NormalizedRecord.objects.create(
                    tenant=self.tenant,
                    batch=self.batch,
                    raw_data=raw_data,
                    facility=facility_name,
                    scope=scope,
                    category=category,
                    activity_type=raw_matnr,
                    raw_value=raw_menge,
                    raw_unit=normalized_unit,
                    normalized_value_tco2e=tco2e,
                    confidence_score=max(0, confidence_score),
                    status=status,
                    validation_notes="; ".join(validation_notes) if validation_notes else "Ingestion successful",
                    transaction_date=transaction_date,
                    is_locked=False
                )
                records_created += 1

            except Exception as e:
                # Log critical parsing failures
                NormalizedRecord.objects.create(
                    tenant=self.tenant,
                    batch=self.batch,
                    raw_data=raw_data,
                    facility="Parsing Failure",
                    scope="Scope 1",
                    category="Ingestion Error",
                    activity_type="Unknown",
                    raw_value=Decimal('0'),
                    raw_unit="Unknown",
                    normalized_value_tco2e=Decimal('0'),
                    confidence_score=0,
                    status='error',
                    validation_notes=f"Parsing crash: {str(e)}",
                    transaction_date=datetime.today().date(),
                    is_locked=False
                )
                records_created += 1

        return records_created


class UtilityParser(BaseParser):
    """
    Parses Utility portal billing cycle CSV exports.
    Expected Columns:
    - Meter_ID: Meter identifier code
    - Start_Date: Start of billing cycle (Format: YYYY-MM-DD or D-M-Y)
    - End_Date: End of billing cycle (Format: YYYY-MM-DD or D-M-Y)
    - Usage_Value: Electricity quantity used
    - Usage_Unit: Unit (kWh or MWh)
    - Amount_USD: Cost of bill (optional)
    """

    # Grid Emissions Factor: 0.00042 tCO2e per kWh (typical mixed-generation grid)
    GRID_EMISSION_FACTOR = 0.00042

    def parse(self, file_path):
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            raise ValueError(f"Failed to read CSV file: {str(e)}")

        df.columns = [c.strip() for c in df.columns]

        # Verify minimal columns
        required = {'Meter_ID', 'Start_Date', 'End_Date', 'Usage_Value', 'Usage_Unit'}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns in Utility file: {', '.join(missing)}")

        records_created = 0

        for idx, row in df.iterrows():
            raw_row = row.to_dict()
            raw_row_cleaned = {k: (None if pd.isna(v) else v) for k, v in raw_row.items()}

            raw_data = RawIngestedData.objects.create(
                batch=self.batch,
                row_index=idx + 1,
                raw_payload=raw_row_cleaned
            )

            try:
                raw_meter = str(raw_row_cleaned.get('Meter_ID', '')).strip()
                raw_start = str(raw_row_cleaned.get('Start_Date', '')).strip()
                raw_end = str(raw_row_cleaned.get('End_Date', '')).strip()
                raw_value = Decimal(str(raw_row_cleaned.get('Usage_Value', '0')).replace(',', '').strip())
                raw_unit = str(raw_row_cleaned.get('Usage_Unit', '')).strip().upper()

                # Parse dates
                try:
                    start_date = pd.to_datetime(raw_start).date()
                    end_date = pd.to_datetime(raw_end).date()
                    dates_valid = True
                except Exception:
                    start_date = datetime.today().date() - timedelta(days=30)
                    end_date = datetime.today().date()
                    dates_valid = False

                # Facility lookup mapping
                facility_name, resolved = self.resolve_facility(raw_meter)

                # Normalize raw value to kWh
                usage_kwh = raw_value
                normalized_unit = 'kWh'
                if raw_unit == 'MWH':
                    usage_kwh = raw_value * Decimal('1000')
                    normalized_unit = 'kWh'
                elif raw_unit != 'KWH':
                    normalized_unit = raw_unit

                validation_notes = []
                confidence_score = 100
                status = 'validated'

                if not resolved:
                    validation_notes.append(f"Meter ID '{raw_meter}' not found in lookup mapping.")
                    confidence_score -= 20
                    status = 'review'

                if not dates_valid:
                    validation_notes.append(f"Failed to parse dates ({raw_start} to {raw_end}).")
                    confidence_score -= 40
                    status = 'error'

                # Verify start < end
                if dates_valid and start_date >= end_date:
                    validation_notes.append(f"Start date {start_date} is after or equal to End date {end_date}.")
                    confidence_score -= 50
                    status = 'error'

                # Realistic billing period distribution across calendar months!
                # If start_date and end_date are in different calendar months, we split daily average
                if dates_valid and start_date < end_date:
                    total_days = (end_date - start_date).days + 1
                    if total_days <= 0:
                        total_days = 1
                    
                    daily_average = usage_kwh / Decimal(str(total_days))

                    # Distribute daily average across months
                    current_day = start_date
                    monthly_distribution = {}  # (year, month) -> count of days
                    
                    while current_day <= end_date:
                        key = (current_day.year, current_day.month)
                        monthly_distribution[key] = monthly_distribution.get(key, 0) + 1
                        current_day += timedelta(days=1)

                    # Create a record for each month
                    for (year, month), days in monthly_distribution.items():
                        allocated_kwh = daily_average * Decimal(str(days))
                        tco2e = allocated_kwh * Decimal(str(self.GRID_EMISSION_FACTOR))
                        
                        month_start = datetime(year, month, 1).date()
                        
                        notes = list(validation_notes)
                        notes.append(f"Distributed billing cycle: allocated {days}/{total_days} days to {month}/{year}.")

                        NormalizedRecord.objects.create(
                            tenant=self.tenant,
                            batch=self.batch,
                            raw_data=raw_data,
                            facility=facility_name,
                            scope='Scope 2',
                            category='Purchased Electricity',
                            activity_type='Grid Electricity',
                            raw_value=allocated_kwh,
                            raw_unit='kWh',
                            normalized_value_tco2e=tco2e,
                            confidence_score=max(0, confidence_score),
                            status=status,
                            validation_notes="; ".join(notes),
                            transaction_date=month_start,
                            billing_start_date=start_date,
                            billing_end_date=end_date,
                            is_locked=False
                        )
                        records_created += 1

                else:
                    # Fallback if dates are invalid - create single static row
                    tco2e = usage_kwh * Decimal(str(self.GRID_EMISSION_FACTOR))
                    NormalizedRecord.objects.create(
                        tenant=self.tenant,
                        batch=self.batch,
                        raw_data=raw_data,
                        facility=facility_name,
                        scope='Scope 2',
                        category='Purchased Electricity',
                        activity_type='Grid Electricity',
                        raw_value=usage_kwh,
                        raw_unit=normalized_unit,
                        normalized_value_tco2e=tco2e,
                        confidence_score=max(0, confidence_score),
                        status=status,
                        validation_notes="; ".join(validation_notes) if validation_notes else "Ingestion successful",
                        transaction_date=start_date,
                        billing_start_date=start_date,
                        billing_end_date=end_date,
                        is_locked=False
                    )
                    records_created += 1

            except Exception as e:
                # Log critical parsing failures
                NormalizedRecord.objects.create(
                    tenant=self.tenant,
                    batch=self.batch,
                    raw_data=raw_data,
                    facility="Parsing Failure",
                    scope="Scope 2",
                    category="Ingestion Error",
                    activity_type="Unknown",
                    raw_value=Decimal('0'),
                    raw_unit="Unknown",
                    normalized_value_tco2e=Decimal('0'),
                    confidence_score=0,
                    status='error',
                    validation_notes=f"Parsing crash: {str(e)}",
                    transaction_date=datetime.today().date(),
                    is_locked=False
                )
                records_created += 1

        return records_created


class TravelParser(BaseParser):
    """
    Parses Concur or Navan corporate travel API JSON payloads.
    Structure: JSON array of bookings
    Format:
    [
      {
        "booking_id": "T-0912",
        "employee_email": "jane@client.com",
        "type": "flight",
        "origin_airport": "JFK",
        "destination_airport": "LHR",
        "distance_miles": null,
        "class": "business",
        "room_nights": null,
        "booking_date": "2026-05-28"
      }
    ]
    """

    # Travel Emission Factors (tCO2e per passenger-mile or per room-night)
    FACTORS = {
        'flight_short': 0.00028,  # < 300 miles
        'flight_long': 0.00018,   # >= 300 miles
        'hotel_night': 0.02030,   # per night
        'train_mile': 0.00011,    # per mile
        'car_mile': 0.00035,      # rental per mile
    }

    def parse_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                bookings = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON file: {str(e)}")

        if not isinstance(bookings, list):
            # Try to handle wrapper dict
            if isinstance(bookings, dict) and 'bookings' in bookings:
                bookings = bookings['bookings']
            else:
                raise ValueError("JSON payload must be a list of bookings or contain a 'bookings' list.")

        records_created = 0

        for idx, booking in enumerate(bookings):
            # Save Raw for Audit
            raw_data = RawIngestedData.objects.create(
                batch=self.batch,
                row_index=idx + 1,
                raw_payload=booking
            )

            try:
                booking_id = booking.get('booking_id', f"MOCK-{idx}")
                employee_email = booking.get('employee_email', 'unknown@client.com')
                trip_type = str(booking.get('type', '')).strip().lower()
                booking_date_str = booking.get('booking_date', '')
                origin = str(booking.get('origin_airport', '')).strip().upper()
                destination = str(booking.get('destination_airport', '')).strip().upper()
                raw_dist = booking.get('distance_miles')
                cabin_class = str(booking.get('class', 'economy')).strip().lower()
                room_nights = booking.get('room_nights')

                # Parse date
                try:
                    booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
                except Exception:
                    booking_date = datetime.today().date()

                # Determine facility from email domain or fallback
                # For realistic travel, we map all business travel to 'Corporate Headquarters' or a default
                facility_name = "Corporate Headquarters"

                validation_notes = []
                confidence_score = 100
                status = 'validated'
                tco2e = Decimal('0')
                raw_val = Decimal('0')
                raw_unit = 'N/A'
                activity_type = trip_type.capitalize()

                if trip_type == 'flight':
                    # Calculate or lookup distance
                    distance = Decimal('0')
                    if raw_dist is not None:
                        distance = Decimal(str(raw_dist))
                        raw_unit = 'miles'
                    elif origin and destination:
                        # Omitted distance - run Great Circle Distance Lookup
                        coord1 = AIRPORT_COORDINATES.get(origin)
                        coord2 = AIRPORT_COORDINATES.get(destination)

                        if coord1 and coord2:
                            distance = Decimal(str(round(haversine_distance(coord1[0], coord1[1], coord2[0], coord2[1]), 1)))
                            raw_unit = 'miles'
                            validation_notes.append(f"Distance calculated between {origin} and {destination} using Great Circle formula.")
                        else:
                            # Airport not in coordinates lookup
                            distance = Decimal('500')  # Default fallback
                            raw_unit = 'miles'
                            confidence_score -= 40
                            status = 'review'
                            validation_notes.append(f"Unmapped airport code pair ({origin}->{destination}). Applied default 500-mile fallback.")
                    else:
                        confidence_score -= 50
                        status = 'error'
                        validation_notes.append("Flight trip is missing airport codes and explicit distance.")

                    raw_val = distance
                    
                    # Apply flight length factor
                    factor_key = 'flight_short' if distance < 300 else 'flight_long'
                    factor = Decimal(str(self.FACTORS[factor_key]))

                    # Apply business class premium multiplier (business flights emit more per seat allocation)
                    multiplier = Decimal('1.0')
                    if cabin_class == 'business':
                        multiplier = Decimal('1.5')
                        validation_notes.append("1.5x Multiplier applied for Business Cabin class.")
                    elif cabin_class == 'first':
                        multiplier = Decimal('2.0')
                        validation_notes.append("2.0x Multiplier applied for First Cabin class.")

                    tco2e = distance * factor * multiplier

                elif trip_type == 'hotel':
                    nights = Decimal(str(room_nights)) if room_nights else Decimal('0')
                    raw_val = nights
                    raw_unit = 'room-nights'
                    tco2e = nights * Decimal(str(self.FACTORS['hotel_night']))
                    if nights <= 0:
                        status = 'review'
                        validation_notes.append("Hotel booking has 0 room nights.")
                        confidence_score -= 10

                elif trip_type in ['train', 'rail']:
                    distance = Decimal(str(raw_dist)) if raw_dist else Decimal('0')
                    raw_val = distance
                    raw_unit = 'miles'
                    tco2e = distance * Decimal(str(self.FACTORS['train_mile']))

                elif trip_type == 'car':
                    distance = Decimal(str(raw_dist)) if raw_dist else Decimal('0')
                    raw_val = distance
                    raw_unit = 'miles'
                    tco2e = distance * Decimal(str(self.FACTORS['car_mile']))
                
                else:
                    status = 'error'
                    confidence_score -= 50
                    validation_notes.append(f"Unknown corporate travel activity type '{trip_type}'.")

                NormalizedRecord.objects.create(
                    tenant=self.tenant,
                    batch=self.batch,
                    raw_data=raw_data,
                    facility=facility_name,
                    scope='Scope 3',
                    category='Business Travel',
                    activity_type=activity_type,
                    raw_value=raw_val,
                    raw_unit=raw_unit,
                    normalized_value_tco2e=tco2e,
                    confidence_score=max(0, confidence_score),
                    status=status,
                    validation_notes="; ".join(validation_notes) if validation_notes else "Ingestion successful",
                    transaction_date=booking_date,
                    is_locked=False
                )
                records_created += 1

            except Exception as e:
                NormalizedRecord.objects.create(
                    tenant=self.tenant,
                    batch=self.batch,
                    raw_data=raw_data,
                    facility="Parsing Failure",
                    scope="Scope 3",
                    category="Ingestion Error",
                    activity_type="Unknown",
                    raw_value=Decimal('0'),
                    raw_unit="Unknown",
                    normalized_value_tco2e=Decimal('0'),
                    confidence_score=0,
                    status='error',
                    validation_notes=f"Parsing crash: {str(e)}",
                    transaction_date=datetime.today().date(),
                    is_locked=False
                )
                records_created += 1

        return records_created
