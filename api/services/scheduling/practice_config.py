"""Practice configuration for John Li ENT practice.

This module contains configurable practice values for the John Li ENT practice.
All values should be configurable and not hard-coded in the tool implementations.
"""

from dataclasses import dataclass, field
from datetime import time
from typing import Optional


@dataclass
class PracticeConfiguration:
    """Configuration for the John Li ENT practice.
    
    This class holds all configurable practice values that can be customized
    for different deployments or practice locations.
    """
    
    # Provider information
    provider_name: str = "Dr. John Li, MD"
    provider_id: str = "dr-john-li"
    specialty: str = "ENT / Otolaryngology"
    
    # Practice timezone (IANA timezone name)
    practice_timezone: str = "America/New_York"
    
    # Office information
    office_name: str = "John Li, MD - ENT Specialists"
    office_address: str = "[Address to be provided by Dr. Li]"
    office_phone: str = "[Office phone number to be provided by Dr. Li]"
    
    # Office hours (24-hour format)
    office_hours: dict[str, tuple[time, time]] = field(default_factory=lambda: {
        "monday": (time(8, 0), time(17, 0)),
        "tuesday": (time(8, 0), time(17, 0)),
        "wednesday": (time(8, 0), time(17, 0)),
        "thursday": (time(8, 0), time(17, 0)),
        "friday": (time(8, 0), time(13, 0)),
        "saturday": None,  # Closed
        "sunday": None,  # Closed
    })
    
    # Locations
    locations: dict[str, str] = field(default_factory=lambda: {
        "main-office": "Main Office",
    })
    
    # Appointment types and durations
    appointment_types: dict[str, int] = field(default_factory=lambda: {
        "new_patient_consult": 30,
        "follow_up": 15,
        "procedure_consult": 30,
        "post_op_follow_up": 15,
        "emergency": 30,
        "routine_checkup": 30,
    })
    
    # Default appointment duration (minutes)
    default_appointment_duration: int = 30
    
    # Daily slot start times (24-hour format)
    slot_start_times: list[tuple[int, int]] = field(default_factory=lambda: [
        (9, 0),   # 9:00 AM
        (10, 30), # 10:30 AM
        (14, 0),  # 2:00 PM
        (15, 30), # 3:30 PM
    ])
    
    # Transfer destination for human requests
    transfer_destination: Optional[str] = None
    transfer_phone: Optional[str] = None
    
    # Emergency escalation message
    emergency_message: str = (
        "For medical emergencies, please call 911 or go to the nearest emergency room. "
        "If this is a life-threatening emergency, please hang up and call 911 immediately."
    )
    
    # Greeting message
    greeting: str = (
        "Thank you for calling the office of John Li, MD. I'm the automated scheduling assistant. "
        "How can I help you today?"
    )
    
    # New patient rules
    new_patient_requires_referral: bool = False
    new_patient_deposit_required: bool = False
    
    # Reminder behavior
    reminder_days_before: int = 1
    reminder_time: str = "morning"
    
    # Synthetic data for testing
    synthetic_patients: list[dict] = field(default_factory=lambda: [
        {
            "name": "John Doe",
            "phone": "+15551234567",
            "email": "john.doe@example.com",
        },
        {
            "name": "Jane Smith",
            "phone": "+15559876543",
            "email": "jane.smith@example.com",
        },
    ])


# Global configuration instance
_config: Optional[PracticeConfiguration] = None


def get_practice_config() -> PracticeConfiguration:
    """Get the practice configuration instance.
    
    Returns:
        The practice configuration instance.
    """
    global _config
    if _config is None:
        _config = PracticeConfiguration()
    return _config


def set_practice_config(config: PracticeConfiguration) -> None:
    """Set the practice configuration instance.
    
    Args:
        config: The practice configuration to use.
    """
    global _config
    _config = config


def reset_practice_config() -> None:
    """Reset the practice configuration instance (for testing)."""
    global _config
    _config = None