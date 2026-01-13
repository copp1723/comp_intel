"""
Data models for dealership scraper
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class ToolType(str, Enum):
    """8 dealership tools to detect"""
    PAYMENT_CALCULATOR = "payment_calculator"
    APR_DISCLOSURE = "apr_disclosure"
    LEASE_PAYMENT_OPTIONS = "lease_payment_options"
    PRE_QUALIFICATION_TOOL = "pre_qualification_tool"
    TRADE_IN_TOOL = "trade_in_tool"
    ONLINE_FINANCE_APPLICATION = "online_finance_application"
    SRP_PAYMENTS_SHOWN = "srp_payments_shown"
    VDP_PAYMENTS_SHOWN = "vdp_payments_shown"


class ToolDetection(BaseModel):
    """Tool detection result"""
    tool_name: str
    isPresent: bool
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    location: str
    url: str
    notes: str


# ========== VEHICLE ENUMS ==========
class VehicleCondition(str, Enum):
    NEW = "New"
    USED = "Used"
    CERTIFIED = "Certified Pre-Owned"
    CPO = "CPO"


class DrivetrainType(str, Enum):
    FWD = "FWD"
    RWD = "RWD"
    AWD = "AWD"
    FOUR_WD = "4WD"
    TWO_WD = "2WD"


class TransmissionType(str, Enum):
    AUTOMATIC = "Automatic"
    MANUAL = "Manual"
    CVT = "CVT"
    DUAL_CLUTCH = "Dual-Clutch"
    SEMI_AUTOMATIC = "Semi-Automatic"


class FuelType(str, Enum):
    GASOLINE = "Gasoline"
    DIESEL = "Diesel"
    ELECTRIC = "Electric"
    HYBRID = "Hybrid"
    PLUGIN_HYBRID = "Plug-in Hybrid"
    HEV = "HEV"
    PHEV = "PHEV"
    BEV = "BEV"
    FLEX_FUEL = "Flex Fuel"
    CNG = "CNG"
    HYDROGEN = "Hydrogen"


class VehicleType(str, Enum):
    SEDAN = "Sedan"
    SUV = "SUV"
    TRUCK = "Truck"
    COUPE = "Coupe"
    CONVERTIBLE = "Convertible"
    HATCHBACK = "Hatchback"
    WAGON = "Wagon"
    VAN = "Van"
    MINIVAN = "Minivan"
    CROSSOVER = "Crossover"
    PICKUP = "Pickup"
    SPORTS_CAR = "Sports Car"
    LUXURY = "Luxury"
    COMPACT = "Compact"


# ========== VEHICLE MODEL (CarListing from url_seeding_crawler.py) ==========
class Vehicle(BaseModel):
    """
    Complete vehicle schema from url_seeding_crawler.py
    All fields are optional to allow flexible extraction
    """
    # Core identification
    year: Optional[str] = Field(None, description="Year of the vehicle (e.g., 2024, 2025)")
    make: Optional[str] = Field(None, description="Make/Brand (e.g., Toyota, Honda, Ford)")
    model: Optional[str] = Field(None, description="Model (e.g., Camry, Accord, F-150)")
    trim: Optional[str] = Field(None, description="Trim level (e.g., LE, XLE, Limited)")

    # Pricing
    price: Optional[float] = Field(None, description="Total vehicle price as number ONLY (e.g., 25995.00). Do NOT extract monthly payments. Extract only the full purchase price.")
    currency: Optional[str] = Field(None, description="Currency symbol or code (e.g., 'USD', '$', 'CAD')")
    monthly_payment: Optional[float] = Field(None, description="Monthly payment amount if available (for reference only)")

    # Core Specifications
    condition: Optional[str] = Field(None, description="Condition: New, Used, or Certified Pre-Owned")
    vin: Optional[str] = Field(None, description="17-character Vehicle Identification Number")
    vehicle_type: Optional[str] = Field(None, description="Body type (Sedan, SUV, Truck, etc.)")

    # Basic Info
    title: Optional[str] = Field(None, description="Full title of the listing")

    # Detailed Specifications
    stock_number: Optional[str] = Field(None, description="Dealership stock/inventory number")
    mileage: Optional[str] = Field(None, description="Odometer reading (e.g., '15000', '0')")

    # Technical Specifications
    drivetrain: Optional[str] = Field(None, description="Drivetrain (FWD, RWD, AWD, 4WD)")
    transmission: Optional[str] = Field(None, description="Transmission (Automatic, Manual, CVT)")
    fuel_type: Optional[str] = Field(None, description="Fuel/energy type")
    doors: Optional[int] = Field(None, description="Number of doors (2, 4)")
    engine: Optional[str] = Field(None, description="Engine description (e.g., '2.5L 4-Cylinder')")

    # Exterior/Interior
    exterior_color: Optional[str] = Field(None, description="Exterior paint color")
    interior_color: Optional[str] = Field(None, description="Interior color/material")
    seating_capacity: Optional[int] = Field(None, description="Number of seats (e.g., 5, 7)")

    # Features & Options
    features: Optional[List[str]] = Field(None, description="List of features")
    safety_features: Optional[List[str]] = Field(None, description="Safety features")

    # Additional Details
    warranty: Optional[str] = Field(None, description="Warranty information")
    certified_program: Optional[str] = Field(None, description="Certified pre-owned program name")
    special_offers: Optional[str] = Field(None, description="Special offers or promotions")

    # Metadata
    source_url: Optional[str] = Field(None, description="URL where this vehicle was found")
    page_type: Optional[str] = Field(None, description="Type of page (VDP, SRP, etc.)")


class URLClassification(BaseModel):
    """URL classification result"""
    url: str
    type: str  # inventory, finance, skip
    subcategory: str  # high, medium, low, calculator, prequalify, etc.
    priority: int = 0
