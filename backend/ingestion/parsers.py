import csv
import json
import math
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd

from tenants.models import Tenant
from ingestion.models import UploadBatch, RawIngestedRow
from emissions.models import FacilityProfile, NormalisedEmissionRecord
from emissions.choices import EmissionScope, ReviewStatus, NormalisedUnit
from ingestion.choices import SourceType

# ── Major airports for Great Circle Distance (Haversine) ─────────────────────
AIRPORT_COORDINATES = {
    'JFK': (40.6398, -73.7789), 'LHR': (51.4700, -0.4543),
    'CDG': (49.0097,  2.5479),  'SFO': (37.6190, -122.3748),
    'LAX': (33.9416, -118.4085),'FRA': (50.0379,  8.5622),
    'SIN': ( 1.3502, 103.9944), 'HND': (35.5494, 139.7798),
    'DXB': (25.2532,  55.3657), 'AMS': (52.3081,   4.7642),
}


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 3958.8
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _old_status_to_review(old: str) -> str:
    """Map old status strings to ReviewStatus choices."""
    return {
        'validated': ReviewStatus.AUTO_APPROVED,
        'review':    ReviewStatus.NEEDS_REVIEW,
        'error':     ReviewStatus.NEEDS_REVIEW,
    }.get(old, ReviewStatus.NEEDS_REVIEW)


def _scope(old: str) -> str:
    """Map old scope strings to EmissionScope choices."""
    return {
        'Scope 1': EmissionScope.SCOPE_1,
        'Scope 2': EmissionScope.SCOPE_2,
        'Scope 3': EmissionScope.SCOPE_3,
    }.get(old, EmissionScope.SCOPE_3)


def _checksum(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


# ── Base class ────────────────────────────────────────────────────────────────

class BaseParser:
    def __init__(self, batch: UploadBatch):
        self.batch  = batch
        self.tenant = batch.tenant

    def resolve_facility(self, code: str):
        """Returns (FacilityProfile | None, label_string)."""
        try:
            profile = FacilityProfile.objects.get(tenant=self.tenant, code=str(code))
            return profile, profile.name
        except FacilityProfile.DoesNotExist:
            return None, f"Unmapped Facility (Code: {code})"

    def _save_raw(self, idx: int, payload: dict) -> RawIngestedRow:
        """Create or fetch RawIngestedRow (deduplication by checksum)."""
        cs = _checksum(payload)
        row, _ = RawIngestedRow.objects.get_or_create(
            batch=self.batch,
            checksum=cs,
            defaults={
                'tenant':           self.tenant,
                'raw_payload':      payload,
                'source_row_index': idx,
            }
        )
        return row

    def _create_emission(self, raw_row, *, period_start, period_end,
                         source_type, scope_str, category, activity_type,
                         qty_raw, unit_raw, qty_norm, unit_norm,
                         factor_value, co2e_kg,
                         confidence, old_status, notes,
                         facility_profile=None, facility_label=''):
        """Single entry-point for creating NormalisedEmissionRecord."""
        anomaly = old_status in ('review', 'error')
        NormalisedEmissionRecord.objects.create(
            tenant               = self.tenant,
            batch                = self.batch,
            raw_row              = raw_row,
            reporting_year       = period_start.year,
            facility             = facility_profile,
            facility_label       = facility_label,
            period_start         = period_start,
            period_end           = period_end,
            source_type          = source_type,
            scope                = _scope(scope_str),
            category             = category,
            activity_type        = activity_type,
            quantity_raw         = qty_raw,
            unit_raw             = unit_raw,
            quantity_normalised  = qty_norm,
            unit_normalised      = unit_norm,
            emission_factor      = factor_value,
            co2e_kg              = co2e_kg,
            confidence_score     = max(0, confidence),
            review_status        = _old_status_to_review(old_status),
            review_notes         = notes,
            anomaly_flag         = anomaly,
            anomaly_reason       = notes if anomaly else '',
        )


# ── SAP Parser ────────────────────────────────────────────────────────────────

class SAPParser(BaseParser):
    """
    Parses German/ECC SAP Flat CSV exports.
    Columns: WERKS, BUDAT, MATNR, MENGE, MEINS, DMBTR
    """
    GERMAN_HEADERS = {
        'WERKS': 'plant_code', 'BUDAT': 'date',
        'MATNR': 'material',   'MENGE': 'quantity',
        'MEINS': 'unit',       'DMBTR': 'cost',
    }

    # Emission factors in tCO2e per raw unit
    EMISSION_FACTORS = {
        'DIESEL':   {'unit': 'Liters',     'factor': 0.00268, 'scope': 'Scope 1', 'category': 'Stationary Combustion'},
        'PETROL':   {'unit': 'Liters',     'factor': 0.00231, 'scope': 'Scope 1', 'category': 'Stationary Combustion'},
        'STEEL':    {'unit': 'Kilograms',  'factor': 0.00185, 'scope': 'Scope 3', 'category': 'Purchased Goods and Services'},
        'PLASTIC':  {'unit': 'Kilograms',  'factor': 0.00192, 'scope': 'Scope 3', 'category': 'Purchased Goods and Services'},
        'PAPER':    {'unit': 'Kilograms',  'factor': 0.00095, 'scope': 'Scope 3', 'category': 'Purchased Goods and Services'},
    }

    UNIT_NORM_MAP = {
        'Liters':    NormalisedUnit.LITRE,
        'Kilograms': NormalisedUnit.KG,
    }

    def parse(self, file_path: str) -> int:
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            raise ValueError(f"Failed to read CSV file: {e}")

        df.columns = [c.strip().upper() for c in df.columns]

        required = set(self.GERMAN_HEADERS.keys())
        missing = required - set(df.columns)
        if missing:
            eng_map = {v.upper(): k for k, v in self.GERMAN_HEADERS.items()}
            if set(eng_map.keys()).issubset(set(df.columns)):
                df = df.rename(columns=eng_map)
            else:
                raise ValueError(f"Missing required SAP columns: {', '.join(missing)}")

        records_created = 0
        for idx, row in df.iterrows():
            payload = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
            raw_row = self._save_raw(idx + 1, payload)

            try:
                raw_werks = str(payload.get('WERKS', '')).strip()
                raw_budat = str(payload.get('BUDAT', '')).strip()
                raw_matnr = str(payload.get('MATNR', '')).strip().upper()
                raw_menge = Decimal(str(payload.get('MENGE', '0')).replace(',', '').strip() or '0')
                raw_meins = str(payload.get('MEINS', '')).strip().upper()

                # Parse date
                date_valid = True
                try:
                    tx_date = datetime.strptime(raw_budat, '%d.%m.%Y').date()
                except ValueError:
                    try:
                        tx_date = datetime.strptime(raw_budat, '%Y-%m-%d').date()
                    except ValueError:
                        tx_date = datetime.today().date()
                        date_valid = False

                # Normalise unit label
                norm_unit_label = raw_meins
                if raw_meins in ('L', 'LTR', 'LITER', 'LITERS'):
                    norm_unit_label = 'Liters'
                elif raw_meins in ('KG', 'KILO', 'KILOGRAM', 'KILOGRAMS'):
                    norm_unit_label = 'Kilograms'

                facility_profile, facility_label = self.resolve_facility(raw_werks)
                factor_info = self.EMISSION_FACTORS.get(raw_matnr)

                notes_list, confidence, old_status = [], 100, 'validated'

                if facility_profile is None:
                    notes_list.append(f"WERKS '{raw_werks}' not in facility lookup.")
                    confidence -= 20; old_status = 'review'

                if not date_valid:
                    notes_list.append(f"Invalid date '{raw_budat}'. Defaulted to today.")
                    confidence -= 30; old_status = 'error'

                if not factor_info:
                    notes_list.append(f"Unknown material '{raw_matnr}'. Cannot calculate.")
                    confidence -= 50; old_status = 'error'
                    tco2e = Decimal('0')
                    scope_str, category = 'Scope 3', 'Purchased Goods and Services'
                    norm_unit_choice = NormalisedUnit.KG
                    factor_val = Decimal('0')
                else:
                    scope_str = factor_info['scope']
                    category  = factor_info['category']
                    factor_val = Decimal(str(factor_info['factor']))
                    norm_unit_choice = self.UNIT_NORM_MAP.get(factor_info['unit'], NormalisedUnit.KG)

                    if factor_info['unit'] != norm_unit_label:
                        notes_list.append(f"Unit mismatch: expected {factor_info['unit']}, got {norm_unit_label}.")
                        confidence -= 15; old_status = 'review'

                    tco2e = factor_val * raw_menge

                if raw_menge > 100000:
                    notes_list.append("Anomaly: unusually large quantity (>100k).")
                    confidence -= 10; old_status = 'review'

                self._create_emission(
                    raw_row,
                    period_start     = tx_date,
                    period_end       = tx_date,
                    source_type      = SourceType.SAP,
                    scope_str        = scope_str,
                    category         = category,
                    activity_type    = raw_matnr,
                    qty_raw          = raw_menge,
                    unit_raw         = norm_unit_label,
                    qty_norm         = raw_menge,
                    unit_norm        = norm_unit_choice,
                    factor_value     = factor_val,
                    co2e_kg          = tco2e * 1000,   # tCO2e → kg
                    confidence       = confidence,
                    old_status       = old_status,
                    notes            = '; '.join(notes_list) or 'Ingestion successful',
                    facility_profile = facility_profile,
                    facility_label   = facility_label,
                )
                records_created += 1

            except Exception as e:
                self._create_emission(
                    raw_row,
                    period_start=datetime.today().date(), period_end=datetime.today().date(),
                    source_type=SourceType.SAP, scope_str='Scope 3',
                    category='Ingestion Error', activity_type='Unknown',
                    qty_raw=Decimal('0'), unit_raw='Unknown',
                    qty_norm=Decimal('0'), unit_norm=NormalisedUnit.KG_CO2E,
                    factor_value=Decimal('0'), co2e_kg=Decimal('0'),
                    confidence=0, old_status='error',
                    notes=f'Parsing crash: {e}',
                )
                records_created += 1

        return records_created


# ── Utility Parser ────────────────────────────────────────────────────────────

class UtilityParser(BaseParser):
    """
    Parses Utility portal billing cycle CSV exports.
    Columns: Meter_ID, Start_Date, End_Date, Usage_Value, Usage_Unit, Amount_USD
    """
    GRID_EMISSION_FACTOR = Decimal('0.00042')   # tCO2e per kWh

    def parse(self, file_path: str) -> int:
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            raise ValueError(f"Failed to read CSV: {e}")

        df.columns = [c.strip() for c in df.columns]
        required = {'Meter_ID', 'Start_Date', 'End_Date', 'Usage_Value', 'Usage_Unit'}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing Utility columns: {', '.join(missing)}")

        records_created = 0
        for idx, row in df.iterrows():
            payload = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
            raw_row = self._save_raw(idx + 1, payload)

            try:
                raw_meter = str(payload.get('Meter_ID', '')).strip()
                raw_start = str(payload.get('Start_Date', '')).strip()
                raw_end   = str(payload.get('End_Date', '')).strip()
                raw_value = Decimal(str(payload.get('Usage_Value', '0')).replace(',', '').strip() or '0')
                raw_unit  = str(payload.get('Usage_Unit', '')).strip().upper()

                try:
                    start_date = pd.to_datetime(raw_start).date()
                    end_date   = pd.to_datetime(raw_end).date()
                    dates_valid = True
                except Exception:
                    start_date  = datetime.today().date() - timedelta(days=30)
                    end_date    = datetime.today().date()
                    dates_valid = False

                facility_profile, facility_label = self.resolve_facility(raw_meter)

                usage_kwh = raw_value
                if raw_unit == 'MWH':
                    usage_kwh = raw_value * 1000

                notes_list, confidence, old_status = [], 100, 'validated'
                if facility_profile is None:
                    notes_list.append(f"Meter '{raw_meter}' not in lookup.")
                    confidence -= 20; old_status = 'review'
                if not dates_valid:
                    notes_list.append(f"Failed to parse dates ({raw_start} – {raw_end}).")
                    confidence -= 40; old_status = 'error'
                if dates_valid and start_date >= end_date:
                    notes_list.append(f"Start {start_date} ≥ End {end_date}.")
                    confidence -= 50; old_status = 'error'

                if dates_valid and start_date < end_date:
                    total_days = (end_date - start_date).days + 1
                    daily_avg  = usage_kwh / Decimal(str(total_days))

                    current = start_date
                    monthly: dict = {}
                    while current <= end_date:
                        key = (current.year, current.month)
                        monthly[key] = monthly.get(key, 0) + 1
                        current += timedelta(days=1)

                    for (yr, mo), days in monthly.items():
                        alloc_kwh = daily_avg * Decimal(str(days))
                        tco2e     = alloc_kwh * self.GRID_EMISSION_FACTOR
                        m_start   = datetime(yr, mo, 1).date()
                        sub_notes = list(notes_list)
                        sub_notes.append(f"Distributed {days}/{total_days} days to {mo}/{yr}.")

                        self._create_emission(
                            raw_row,
                            period_start     = m_start,
                            period_end       = m_start,
                            source_type      = SourceType.UTILITY,
                            scope_str        = 'Scope 2',
                            category         = 'Purchased Electricity',
                            activity_type    = 'Grid Electricity',
                            qty_raw          = alloc_kwh,
                            unit_raw         = 'kWh',
                            qty_norm         = alloc_kwh,
                            unit_norm        = NormalisedUnit.KWH,
                            factor_value     = self.GRID_EMISSION_FACTOR,
                            co2e_kg          = tco2e * 1000,
                            confidence       = confidence,
                            old_status       = old_status,
                            notes            = '; '.join(sub_notes),
                            facility_profile = facility_profile,
                            facility_label   = facility_label,
                        )
                        records_created += 1
                else:
                    tco2e = usage_kwh * self.GRID_EMISSION_FACTOR
                    self._create_emission(
                        raw_row,
                        period_start     = start_date,
                        period_end       = end_date,
                        source_type      = SourceType.UTILITY,
                        scope_str        = 'Scope 2',
                        category         = 'Purchased Electricity',
                        activity_type    = 'Grid Electricity',
                        qty_raw          = usage_kwh,
                        unit_raw         = 'kWh',
                        qty_norm         = usage_kwh,
                        unit_norm        = NormalisedUnit.KWH,
                        factor_value     = self.GRID_EMISSION_FACTOR,
                        co2e_kg          = tco2e * 1000,
                        confidence       = confidence,
                        old_status       = old_status,
                        notes            = '; '.join(notes_list) or 'Ingestion successful',
                        facility_profile = facility_profile,
                        facility_label   = facility_label,
                    )
                    records_created += 1

            except Exception as e:
                self._create_emission(
                    raw_row,
                    period_start=datetime.today().date(), period_end=datetime.today().date(),
                    source_type=SourceType.UTILITY, scope_str='Scope 2',
                    category='Ingestion Error', activity_type='Unknown',
                    qty_raw=Decimal('0'), unit_raw='Unknown',
                    qty_norm=Decimal('0'), unit_norm=NormalisedUnit.KWH,
                    factor_value=Decimal('0'), co2e_kg=Decimal('0'),
                    confidence=0, old_status='error',
                    notes=f'Parsing crash: {e}',
                )
                records_created += 1

        return records_created


# ── Travel Parser ─────────────────────────────────────────────────────────────

class TravelParser(BaseParser):
    """
    Parses Concur / Navan corporate travel JSON payloads.
    Expected: JSON array of bookings.
    """
    FACTORS = {
        'flight_short': Decimal('0.00028'),
        'flight_long':  Decimal('0.00018'),
        'hotel_night':  Decimal('0.02030'),
        'train_mile':   Decimal('0.00011'),
        'car_mile':     Decimal('0.00035'),
    }

    CABIN_MULTIPLIERS = {
        'business': Decimal('1.5'),
        'first':    Decimal('2.0'),
    }

    def parse_file(self, file_path: str) -> int:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                bookings = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON: {e}")

        if isinstance(bookings, dict) and 'bookings' in bookings:
            bookings = bookings['bookings']
        if not isinstance(bookings, list):
            raise ValueError("JSON must be a list of bookings.")

        records_created = 0
        for idx, booking in enumerate(bookings):
            raw_row = self._save_raw(idx + 1, booking)
            try:
                trip_type    = str(booking.get('type', '')).strip().lower()
                date_str     = booking.get('booking_date', '')
                origin       = str(booking.get('origin_airport', '')).strip().upper()
                destination  = str(booking.get('destination_airport', '')).strip().upper()
                raw_dist     = booking.get('distance_miles')
                cabin_class  = str(booking.get('class', 'economy')).strip().lower()
                room_nights  = booking.get('room_nights')

                try:
                    bk_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except Exception:
                    bk_date = datetime.today().date()

                notes_list, confidence, old_status = [], 100, 'validated'
                tco2e = Decimal('0')
                qty   = Decimal('0')
                unit_norm     = NormalisedUnit.MILE
                activity_type = trip_type.capitalize()

                if trip_type == 'flight':
                    distance = Decimal('0')
                    if raw_dist is not None:
                        distance = Decimal(str(raw_dist))
                    elif origin and destination:
                        c1 = AIRPORT_COORDINATES.get(origin)
                        c2 = AIRPORT_COORDINATES.get(destination)
                        if c1 and c2:
                            distance = Decimal(str(round(haversine_distance(c1[0], c1[1], c2[0], c2[1]), 1)))
                            notes_list.append(f"Distance {origin}→{destination} via Haversine.")
                        else:
                            distance = Decimal('500')
                            confidence -= 40; old_status = 'review'
                            notes_list.append(f"Unknown airports ({origin}→{destination}). Used 500-mile fallback.")
                    else:
                        confidence -= 50; old_status = 'error'
                        notes_list.append("Missing airport codes and distance.")

                    qty       = distance
                    multiplier = self.CABIN_MULTIPLIERS.get(cabin_class, Decimal('1.0'))
                    if multiplier > 1:
                        notes_list.append(f"{multiplier}x multiplier for {cabin_class} cabin.")
                    factor_key = 'flight_short' if distance < 300 else 'flight_long'
                    tco2e      = distance * self.FACTORS[factor_key] * multiplier

                elif trip_type == 'hotel':
                    nights = Decimal(str(room_nights)) if room_nights else Decimal('0')
                    qty    = nights; unit_norm = NormalisedUnit.NIGHT
                    tco2e  = nights * self.FACTORS['hotel_night']
                    if nights <= 0:
                        notes_list.append("Hotel booking has 0 room nights.")
                        confidence -= 10; old_status = 'review'

                elif trip_type in ('train', 'rail'):
                    distance = Decimal(str(raw_dist)) if raw_dist else Decimal('0')
                    qty = distance; tco2e = distance * self.FACTORS['train_mile']

                elif trip_type == 'car':
                    distance = Decimal(str(raw_dist)) if raw_dist else Decimal('0')
                    qty = distance; tco2e = distance * self.FACTORS['car_mile']

                else:
                    confidence -= 50; old_status = 'error'
                    notes_list.append(f"Unknown travel type '{trip_type}'.")

                self._create_emission(
                    raw_row,
                    period_start     = bk_date,
                    period_end       = bk_date,
                    source_type      = SourceType.TRAVEL,
                    scope_str        = 'Scope 3',
                    category         = 'Business Travel',
                    activity_type    = activity_type,
                    qty_raw          = qty,
                    unit_raw         = 'miles',
                    qty_norm         = qty,
                    unit_norm        = unit_norm,
                    factor_value     = self.FACTORS.get(f'{trip_type}_mile', Decimal('0')),
                    co2e_kg          = tco2e * 1000,
                    confidence       = confidence,
                    old_status       = old_status,
                    notes            = '; '.join(notes_list) or 'Ingestion successful',
                    facility_profile = None,
                    facility_label   = 'Corporate Headquarters',
                )
                records_created += 1

            except Exception as e:
                self._create_emission(
                    raw_row,
                    period_start=datetime.today().date(), period_end=datetime.today().date(),
                    source_type=SourceType.TRAVEL, scope_str='Scope 3',
                    category='Ingestion Error', activity_type='Unknown',
                    qty_raw=Decimal('0'), unit_raw='Unknown',
                    qty_norm=Decimal('0'), unit_norm=NormalisedUnit.MILE,
                    factor_value=Decimal('0'), co2e_kg=Decimal('0'),
                    confidence=0, old_status='error',
                    notes=f'Parsing crash: {e}',
                )
                records_created += 1

        return records_created
