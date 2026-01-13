"""
VIN Decoder Enrichment Module
Uses NHTSA VIN decoder API to fill missing vehicle data
"""
import requests
from typing import Dict, List, Optional
import time


class VINEnricher:
    """Enrich vehicle data using NHTSA VIN decoder API"""

    NHTSA_API = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"

    def __init__(self, cache_ttl: int = 3600):
        """
        Args:
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        """
        self._cache = {}
        self.cache_ttl = cache_ttl
        self.stats = {
            'total_calls': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'errors': 0,
            'enriched_vehicles': 0,
            'fields_filled': 0
        }

    def decode_vin(self, vin: str) -> Optional[Dict]:
        """
        Get NHTSA data for VIN with caching

        Args:
            vin: 17-character VIN

        Returns:
            Dict of NHTSA data or None if error
        """
        if not vin or len(vin) != 17:
            return None

        self.stats['total_calls'] += 1

        # Check cache
        if vin in self._cache:
            cache_entry = self._cache[vin]
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                self.stats['cache_hits'] += 1
                return cache_entry['data']

        # API call with retry
        max_retries = 2
        for attempt in range(max_retries):
            try:
                self.stats['api_calls'] += 1
                response = requests.get(
                    self.NHTSA_API.format(vin=vin),
                    timeout=5  # Shorter timeout, will retry if fails
                )
                response.raise_for_status()
                data = response.json()

                # Convert to dict
                result = {
                    item['Variable']: item['Value']
                    for item in data.get('Results', [])
                }

                # Cache result
                self._cache[vin] = {
                    'data': result,
                    'timestamp': time.time()
                }

                return result

            except Exception as e:
                if attempt < max_retries - 1:
                    # Retry on failure
                    continue
                else:
                    # Final attempt failed
                    self.stats['errors'] += 1
                    print(f"  ! VIN decode error for {vin}: {str(e)[:50]}")
            return None

    def _map_fuel_type(self, nhtsa_fuel: str) -> Optional[str]:
        """Map NHTSA FuelTypePrimary to our FuelType enum values"""
        if not nhtsa_fuel:
            return None

        fuel = nhtsa_fuel.upper()

        # Map to exact enum values from models.py
        if 'GASOLINE' in fuel or 'GAS' in fuel:
            return 'Gasoline'
        elif 'DIESEL' in fuel:
            return 'Diesel'
        elif 'ELECTRIC' in fuel or 'BATTERY' in fuel:
            return 'Electric'
        elif 'PLUG' in fuel and 'HYBRID' in fuel:
            return 'Plug-in Hybrid'
        elif 'HYBRID' in fuel:
            return 'Hybrid'
        elif 'FLEX' in fuel:
            return 'Flex Fuel'
        elif 'CNG' in fuel or 'COMPRESSED NATURAL GAS' in fuel:
            return 'CNG'
        elif 'HYDROGEN' in fuel:
            return 'Hydrogen'

        return None

    def _map_transmission(self, nhtsa_trans: str) -> Optional[str]:
        """Map NHTSA TransmissionStyle to our TransmissionType enum values"""
        if not nhtsa_trans:
            return None

        trans = nhtsa_trans.upper()

        # Map to exact enum values from models.py
        if 'CVT' in trans or 'CONTINUOUSLY VARIABLE' in trans:
            return 'CVT'
        elif 'MANUAL' in trans:
            return 'Manual'
        elif 'DUAL' in trans and 'CLUTCH' in trans:
            return 'Dual-Clutch'
        elif 'SEMI' in trans:
            return 'Semi-Automatic'
        elif 'AUTOMATIC' in trans or 'AUTO' in trans:
            return 'Automatic'

        return None

    def _map_drivetrain(self, drive_type: str) -> Optional[str]:
        """Map NHTSA DriveType to our DrivetrainType enum values"""
        if not drive_type:
            return None

        drive_type = drive_type.upper()

        # Map to exact enum values from models.py
        if 'FWD' in drive_type or drive_type == '4X2':
            return 'FWD'
        elif 'RWD' in drive_type:
            return 'RWD'
        elif 'AWD' in drive_type or 'ALL' in drive_type:
            return 'AWD'
        elif '4WD' in drive_type or '4X4' in drive_type:
            return '4WD'
        elif '2WD' in drive_type:
            return '2WD'

        return None

    def _map_vehicle_type(self, body_class: str) -> Optional[str]:
        """Map NHTSA BodyClass to our VehicleType enum values"""
        if not body_class:
            return None

        body_class = body_class.upper()

        # Map to exact enum values from models.py
        if 'SUV' in body_class or 'SPORT UTILITY' in body_class:
            return 'SUV'
        elif 'SEDAN' in body_class:
            return 'Sedan'
        elif 'PICKUP' in body_class:
            return 'Pickup'
        elif 'TRUCK' in body_class:
            return 'Truck'
        elif 'COUPE' in body_class:
            return 'Coupe'
        elif 'CONVERTIBLE' in body_class:
            return 'Convertible'
        elif 'HATCHBACK' in body_class:
            return 'Hatchback'
        elif 'WAGON' in body_class:
            return 'Wagon'
        elif 'MINIVAN' in body_class:
            return 'Minivan'
        elif 'VAN' in body_class:
            return 'Van'
        elif 'CROSSOVER' in body_class:
            return 'Crossover'

        return None

    def _map_condition(self, nhtsa_data: Dict) -> Optional[str]:
        """Determine vehicle condition from NHTSA data"""
        # NHTSA doesn't provide condition, but we can infer from model year
        # This is a placeholder - condition should come from scraper
        return None

    def extract_safety_features(self, nhtsa_data: Dict) -> List[str]:
        """
        Extract safety features from NHTSA data

        Args:
            nhtsa_data: NHTSA decoded data

        Returns:
            List of safety feature names
        """
        features = []

        # Expanded mapping of NHTSA fields to feature names
        safety_mapping = {
            'ABS': 'ABS',
            'BlindSpotMon': 'Blind Spot Monitor',
            'BlindSpotIntervention': 'Blind Spot Intervention',
            'ForwardCollisionWarning': 'Forward Collision Warning',
            'LaneDepartureWarning': 'Lane Departure Warning',
            'LaneKeepSystem': 'Lane Keep Assist',
            'LaneCenteringAssistance': 'Lane Centering Assist',
            'RearVisibilitySystem': 'Backup Camera',
            'AdaptiveCruiseControl': 'Adaptive Cruise Control',
            'ParkAssist': 'Park Assist',
            'RearCrossTrafficAlert': 'Rear Cross Traffic Alert',
            'RearAutomaticEmergencyBraking': 'Rear Automatic Emergency Braking',
            'PedestrianAutomaticEmergencyBraking': 'Pedestrian Detection',
            'AutomaticPedestrianAlertingSound': 'Pedestrian Alert Sound',
            'DynamicBrakeSupport': 'Dynamic Brake Support',
            'CrashImminentBraking': 'Crash Imminent Braking',
            'ESC': 'Electronic Stability Control',
            'TractionControl': 'Traction Control',
            'AutoReverseSystem': 'Auto Reverse System',
            'ActiveSafetySysNote': 'Active Safety Systems',
            'TPMS': 'Tire Pressure Monitoring',
            'SeatBeltsAll': 'Seat Belts',
            'PretensionerorLoadLimiter': 'Seat Belt Pretensioners',
            'SeatCushionAirbag': 'Seat Cushion Airbag',
            'FrontAirBagLocCurtain': 'Front Curtain Airbags',
            'SideAirBagLocCurtain': 'Side Curtain Airbags',
        }

        for field, feature_name in safety_mapping.items():
            value = nhtsa_data.get(field, '')
            # Accept both 'standard' and other positive indicators
            if value and (value.lower() in ['standard', 'yes', 'all seating positions', '1st row', 'all rows']):
                features.append(feature_name)

        return features

    def extract_features(self, nhtsa_data: Dict) -> List[str]:
        """
        Extract standard features from NHTSA data

        Args:
            nhtsa_data: NHTSA decoded data

        Returns:
            List of feature names
        """
        features = []

        # Expanded feature mapping
        feature_mapping = {
            'KeylessIgnition': 'Keyless Ignition',
            'DaytimeRunningLight': 'Daytime Running Lights',
            'AdaptiveHeadlights': 'Adaptive Headlights',
            'AdaptiveDrivingBeam': 'Adaptive High Beams',
            'SemiautomaticHeadlampBeamSwitching': 'Automatic High Beams',
            'SAEAutomationLevel': 'Driver Assistance',
            'EntertainmentSystem': 'Entertainment System',
        }

        for field, feature_name in feature_mapping.items():
            value = nhtsa_data.get(field, '')
            if value and value.lower() in ['standard', 'yes']:
                features.append(feature_name)

        return features

    def enrich_vehicle(self, vehicle: Dict, verbose: bool = False) -> Dict:
        """
        Enrich vehicle dict with NHTSA data (OVERRIDES scraper data for accuracy)

        NHTSA data is preferred over scraper data because it's authoritative government data.
        Exception: VIN and price always come from scraper (never overwritten).

        Args:
            vehicle: Vehicle dictionary to enrich
            verbose: Print enrichment details

        Returns:
            Enriched vehicle dictionary with NHTSA data prioritized
        """
        vin = vehicle.get('vin')
        if not vin or len(vin) != 17:
            return vehicle

        # Decode VIN
        nhtsa = self.decode_vin(vin)
        if not nhtsa:
            return vehicle

        fields_updated = 0

        # OVERRIDE core fields with NHTSA data (more accurate than scraper)
        if nhtsa.get('ModelYear'):
            old_year = vehicle.get('year')
            vehicle['year'] = nhtsa['ModelYear']
            if old_year != vehicle['year']:
                fields_updated += 1

        if nhtsa.get('Make'):
            old_make = vehicle.get('make')
            vehicle['make'] = nhtsa['Make']
            if old_make != vehicle['make']:
                fields_updated += 1

        if nhtsa.get('Model'):
            old_model = vehicle.get('model')
            vehicle['model'] = nhtsa['Model']
            if old_model != vehicle['model']:
                fields_updated += 1

        # Trim: Use NHTSA if available, otherwise keep scraper value
        trim = nhtsa.get('Trim') or nhtsa.get('Series')
        if trim:
            old_trim = vehicle.get('trim')
            vehicle['trim'] = trim
            if old_trim != vehicle['trim']:
                fields_updated += 1

        # OVERRIDE technical specs with NHTSA data (standardized enum values)
        fuel_type = self._map_fuel_type(nhtsa.get('FuelTypePrimary', ''))
        if fuel_type:
            old_fuel = vehicle.get('fuel_type')
            vehicle['fuel_type'] = fuel_type
            if old_fuel != vehicle['fuel_type']:
                fields_updated += 1

        transmission = self._map_transmission(nhtsa.get('TransmissionStyle', ''))
        if transmission:
            old_trans = vehicle.get('transmission')
            vehicle['transmission'] = transmission
            if old_trans != vehicle['transmission']:
                fields_updated += 1

        drivetrain = self._map_drivetrain(nhtsa.get('DriveType', ''))
        if drivetrain:
            old_drive = vehicle.get('drivetrain')
            vehicle['drivetrain'] = drivetrain
            if old_drive != vehicle['drivetrain']:
                fields_updated += 1

        # Engine: Build from NHTSA data if available
        displacement = nhtsa.get('DisplacementL')
        cylinders = nhtsa.get('EngineCylinders')
        if displacement:
            engine = f"{displacement}L"
            if cylinders:
                engine += f" {cylinders}-Cylinder"
            old_engine = vehicle.get('engine')
            vehicle['engine'] = engine
            if old_engine != vehicle['engine']:
                fields_updated += 1

        # Doors: NHTSA data preferred
        doors = nhtsa.get('Doors')
        if doors and doors.isdigit():
            old_doors = vehicle.get('doors')
            vehicle['doors'] = int(doors)
            if old_doors != vehicle['doors']:
                fields_updated += 1

        # Seating capacity: NHTSA data preferred
        seats = nhtsa.get('Seats')
        if seats and seats.isdigit():
            old_seats = vehicle.get('seating_capacity')
            vehicle['seating_capacity'] = int(seats)
            if old_seats != vehicle['seating_capacity']:
                fields_updated += 1

        # Vehicle type: NHTSA data preferred (standardized)
        vehicle_type = self._map_vehicle_type(nhtsa.get('BodyClass', ''))
        if vehicle_type:
            old_type = vehicle.get('vehicle_type')
            vehicle['vehicle_type'] = vehicle_type
            if old_type != vehicle['vehicle_type']:
                fields_updated += 1

        # Safety features: ALWAYS use NHTSA data (most comprehensive and accurate)
        safety_features = self.extract_safety_features(nhtsa)
        if safety_features:
            old_safety = vehicle.get('safety_features')
            vehicle['safety_features'] = safety_features
            if old_safety != safety_features:
                fields_updated += len(safety_features)

        # Standard features: Merge NHTSA features with scraper features
        nhtsa_features = self.extract_features(nhtsa)
        if nhtsa_features:
            if not vehicle.get('features'):
                # No scraper features, use NHTSA only
                vehicle['features'] = nhtsa_features
                fields_updated += len(nhtsa_features)
            elif isinstance(vehicle.get('features'), list):
                # Merge: NHTSA features + unique scraper features
                existing = set(vehicle['features'])
                new_features = [f for f in nhtsa_features if f not in existing]
                if new_features:
                    # Prepend NHTSA features (they're more reliable)
                    vehicle['features'] = nhtsa_features + [f for f in vehicle['features'] if f not in nhtsa_features]
                    fields_updated += len(new_features)
                else:
                    # Just reorder to put NHTSA features first
                    vehicle['features'] = nhtsa_features + [f for f in vehicle['features'] if f not in nhtsa_features]

        if fields_updated > 0:
            self.stats['enriched_vehicles'] += 1
            self.stats['fields_filled'] += fields_updated

            if verbose:
                print(f"  ✓ Enriched {vin[:9]}... ({fields_updated} fields updated with NHTSA data)")

        return vehicle

    def print_stats(self):
        """Print enrichment statistics"""
        print("\n" + "="*80)
        print("VIN ENRICHMENT STATISTICS (NHTSA Data Prioritized)")
        print("="*80)
        print(f"Total VIN lookups:      {self.stats['total_calls']}")
        print(f"  Cache hits:           {self.stats['cache_hits']}")
        print(f"  API calls:            {self.stats['api_calls']}")
        print(f"  Errors:               {self.stats['errors']}")
        print(f"\nEnriched vehicles:      {self.stats['enriched_vehicles']}")
        print(f"Total fields updated:   {self.stats['fields_filled']} (NHTSA data overrides scraper)")

        if self.stats['enriched_vehicles'] > 0:
            avg = self.stats['fields_filled'] / self.stats['enriched_vehicles']
            print(f"Avg fields per vehicle: {avg:.1f}")

        if self.stats['total_calls'] > 0:
            hit_rate = (self.stats['cache_hits'] / self.stats['total_calls']) * 100
            print(f"Cache hit rate:         {hit_rate:.1f}%")

        print("="*80)
