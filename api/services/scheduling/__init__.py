"""John Li ENT Scheduling Service.

This module provides scheduling functionality for John Li, MD's ENT practice.
It includes:
- Domain models for appointments, providers, locations
- Scheduler abstraction for integration with external systems
- Mock scheduler for testing and local development
"""

from .models import (
    Appointment,
    AppointmentType,
    AvailabilitySlot,
    CallDisposition,
    CallIntent,
    Location,
    Provider,
    SchedulingRequest,
    SchedulingResult,
    StaffEscalation,
)
from .scheduler import MockSchedulerAdapter, SchedulerAdapter

__all__ = [
    "Appointment",
    "AppointmentType",
    "AvailabilitySlot",
    "CallDisposition",
    "CallIntent",
    "Location",
    "Provider",
    "SchedulingRequest",
    "SchedulingResult",
    "SchedulerAdapter",
    "MockSchedulerAdapter",
    "StaffEscalation",
]