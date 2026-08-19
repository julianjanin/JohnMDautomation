"""John Li ENT Scheduling Service.

This module provides scheduling functionality for John Li, MD's ENT practice.
It includes:
- Domain models for appointments, providers, locations
- Scheduler abstraction for integration with external systems
- Mock scheduler for testing and local development
- Service layer for business logic
- Practice configuration
- Voice workflow configuration
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
from .practice_config import (
    PracticeConfiguration,
    get_practice_config,
    set_practice_config,
    reset_practice_config,
)
from .scheduler import MockSchedulerAdapter, SchedulerAdapter
from .service import SchedulingService, get_scheduling_service, reset_scheduling_service
from .workflow import JohnLiWorkflow, get_john_li_workflow, reset_john_li_workflow

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
    "PracticeConfiguration",
    "get_practice_config",
    "set_practice_config",
    "reset_practice_config",
    "SchedulingService",
    "get_scheduling_service",
    "reset_scheduling_service",
    "JohnLiWorkflow",
    "get_john_li_workflow",
    "reset_john_li_workflow",
]