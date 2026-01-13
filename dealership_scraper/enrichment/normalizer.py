"""
Data Normalization Module
Normalizes vehicle data to match enum values from models.py
"""
from typing import Dict, Optional


class DataNormalizer:
    """Normalize vehicle fields to match enum values"""

    @staticmethod
    def normalize_fuel_type(value: str) -> Optional[str]:
        """Normalize fuel type to FuelType enum values"""
        if not value:
            return None

        val = str(value).upper()

        # Map to exact enum values from models.py
        # Order matters: check most specific first
        if ('PLUG' in val and 'HYBRID' in val) or 'PHEV' in val:
            return 'Plug-in Hybrid'
        elif 'HYBRID' in val or 'HEV' in val:
            return 'Hybrid'
        elif 'ELECTRIC' in val or 'BATTERY' in val or 'BEV' in val:
            return 'Electric'
        elif 'DIESEL' in val:
            return 'Diesel'
        elif 'GASOLINE' in val or 'GAS' in val or 'REGULAR' in val or 'UNLEADED' in val:
            return 'Gasoline'
        elif 'FLEX' in val or 'E85' in val:
            return 'Flex Fuel'
        elif 'CNG' in val or 'COMPRESSED NATURAL GAS' in val:
            return 'CNG'
        elif 'HYDROGEN' in val or 'FUEL CELL' in val:
            return 'Hydrogen'

        # If no match, return original
        return value

    @staticmethod
    def normalize_transmission(value: str) -> Optional[str]:
        """Normalize transmission to TransmissionType enum values"""
        if not value:
            return None

        val = str(value).upper()

        # Map to exact enum values from models.py
        if 'CVT' in val or 'CONTINUOUSLY VARIABLE' in val:
            return 'CVT'
        elif 'MANUAL' in val and 'SEMI' not in val:
            return 'Manual'
        elif 'DUAL' in val and 'CLUTCH' in val:
            return 'Dual-Clutch'
        elif 'SEMI' in val or 'SEMI-AUTO' in val:
            return 'Semi-Automatic'
        elif 'AUTOMATIC' in val or 'AUTO' in val or 'A/T' in val:
            return 'Automatic'

        # If no match, return original
        return value

    @staticmethod
    def normalize_drivetrain(value: str) -> Optional[str]:
        """Normalize drivetrain to DrivetrainType enum values"""
        if not value:
            return None

        val = str(value).upper()

        # Map to exact enum values from models.py
        if 'FWD' in val or 'FRONT' in val or '4X2' in val or 'F/W' in val:
            return 'FWD'
        elif 'RWD' in val or 'REAR' in val or 'R/W' in val:
            return 'RWD'
        elif 'AWD' in val or 'ALL' in val or 'A/W' in val:
            return 'AWD'
        elif '4WD' in val or 'FOUR' in val or '4X4' in val or '4-WHEEL' in val:
            return '4WD'
        elif '2WD' in val or 'TWO' in val or '2-WHEEL' in val:
            return '2WD'

        # If no match, return original
        return value

    @staticmethod
    def normalize_vehicle_type(value: str) -> Optional[str]:
        """Normalize vehicle type to VehicleType enum values"""
        if not value:
            return None

        val = str(value).upper()

        # Map to exact enum values from models.py
        if 'SUV' in val or 'SPORT UTILITY' in val:
            return 'SUV'
        elif 'SEDAN' in val:
            return 'Sedan'
        elif 'PICKUP' in val:
            return 'Pickup'
        elif 'TRUCK' in val and 'PICKUP' not in val:
            return 'Truck'
        elif 'COUPE' in val:
            return 'Coupe'
        elif 'CONVERTIBLE' in val or 'CABRIO' in val:
            return 'Convertible'
        elif 'HATCHBACK' in val or 'HATCH' in val:
            return 'Hatchback'
        elif 'WAGON' in val or 'ESTATE' in val:
            return 'Wagon'
        elif 'MINIVAN' in val or 'MINI VAN' in val:
            return 'Minivan'
        elif 'VAN' in val and 'MINI' not in val:
            return 'Van'
        elif 'CROSSOVER' in val or 'CUV' in val:
            return 'Crossover'
        elif 'SPORTS CAR' in val or 'SPORT CAR' in val:
            return 'Sports Car'
        elif 'LUXURY' in val:
            return 'Luxury'
        elif 'COMPACT' in val:
            return 'Compact'

        # If no match, return original
        return value

    @staticmethod
    def normalize_condition(value: str) -> Optional[str]:
        """Normalize condition to VehicleCondition enum values"""
        if not value:
            return None

        val = str(value).upper()

        # Map to exact enum values from models.py
        if 'NEW' in val and 'PRE' not in val and 'USED' not in val:
            return 'New'
        elif 'CERTIFIED' in val or 'CPO' in val:
            return 'Certified Pre-Owned'
        elif 'USED' in val or 'PRE-OWNED' in val or 'PREOWNED' in val:
            return 'Used'

        # If no match, return original
        return value

    @classmethod
    def normalize_vehicle(cls, vehicle: Dict) -> Dict:
        """
        Normalize all enum fields in a vehicle dict

        Args:
            vehicle: Vehicle dictionary

        Returns:
            Normalized vehicle dictionary
        """
        if not isinstance(vehicle, dict):
            return vehicle

        # Normalize each enum field
        if vehicle.get('fuel_type'):
            normalized = cls.normalize_fuel_type(vehicle['fuel_type'])
            if normalized:
                vehicle['fuel_type'] = normalized

        if vehicle.get('transmission'):
            normalized = cls.normalize_transmission(vehicle['transmission'])
            if normalized:
                vehicle['transmission'] = normalized

        if vehicle.get('drivetrain'):
            normalized = cls.normalize_drivetrain(vehicle['drivetrain'])
            if normalized:
                vehicle['drivetrain'] = normalized

        if vehicle.get('vehicle_type'):
            normalized = cls.normalize_vehicle_type(vehicle['vehicle_type'])
            if normalized:
                vehicle['vehicle_type'] = normalized

        if vehicle.get('condition'):
            normalized = cls.normalize_condition(vehicle['condition'])
            if normalized:
                vehicle['condition'] = normalized

        return vehicle
