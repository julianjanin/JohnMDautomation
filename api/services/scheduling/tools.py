"""Dograh tools for John Li ENT scheduling operations.

These tools are exposed to the voice workflow and can be called by the LLM
during conversation. All state-changing operations are validated server-side.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, Field

from .models import (
    AppointmentType,
    AvailabilitySlot,
    CallDisposition,
    CallIntent,
    SchedulingRequest,
    SchedulingResult,
)
from .scheduler import MockSchedulerAdapter


# Global scheduler instance (in production, this would be injected via DI)
_scheduler: Optional[MockSchedulerAdapter] = None


def get_scheduler() -> MockSchedulerAdapter:
    """Get the scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = MockSchedulerAdapter()
    return _scheduler


def reset_scheduler() -> None:
    """Reset the scheduler instance (for testing)."""
    global _scheduler
    _scheduler = None


def generate_idempotency_key(**kwargs) -> str:
    """Generate an idempotency key from the given parameters.
    
    This ensures that repeated calls with the same parameters
    return the same result without creating duplicate appointments.
    """
    key_parts = []
    for k, v in sorted(kwargs.items()):
        if v is not None:
            key_parts.append(f"{k}={v}")
    key_string = "|".join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()


# Tool schemas for Dograh integration

class FindAvailabilityToolInput(BaseModel):
    """Input for finding appointment availability."""

    appointment_type: str = Field(..., description="Type of appointment")
    preferred_date: Optional[str] = Field(
        None, description="Preferred date (YYYY-MM-DD)"
    )
    preferred_time: Optional[str] = Field(
        None, description="Preferred time of day (morning, afternoon, evening)"
    )
    days_ahead: int = Field(
        default=14, ge=1, le=60, description="Number of days to search ahead"
    )


class BookAppointmentToolInput(BaseModel):
    """Input for booking an appointment."""

    patient_name: str = Field(..., description="Patient's full name")
    patient_phone: str = Field(..., description="Patient's phone number")
    appointment_type: str = Field(..., description="Type of appointment")
    start_time: str = Field(..., description="Appointment start time (ISO format)")
    reason: Optional[str] = Field(None, description="Reason for appointment")
    new_patient: bool = Field(False, description="Whether this is a new patient")


class RescheduleAppointmentToolInput(BaseModel):
    """Input for rescheduling an appointment."""

    appointment_id: str = Field(..., description="Appointment ID to reschedule")
    new_start_time: str = Field(..., description="New start time (ISO format)")


class CancelAppointmentToolInput(BaseModel):
    """Input for canceling an appointment."""

    appointment_id: str = Field(..., description="Appointment ID to cancel")
    confirmation: str = Field(
        ..., description="Must be 'yes' to confirm cancellation"
    )


class ConfirmAppointmentToolInput(BaseModel):
    """Input for confirming an appointment."""

    appointment_id: str = Field(..., description="Appointment ID to confirm")
    confirmation: str = Field(
        ..., description="Must be 'yes' to confirm"
    )


class LookupPatientToolInput(BaseModel):
    """Input for looking up a patient by phone."""

    phone: str = Field(..., description="Patient's phone number")


class GetAppointmentToolInput(BaseModel):
    """Input for getting appointment details."""

    appointment_id: str = Field(..., description="Appointment ID")


class GetOfficeInfoToolInput(BaseModel):
    """Input for getting office information."""

    info_type: str = Field(
        default="hours", description="Type of info: hours, address, phone"
    )


# Tool implementations

async def find_availability_tool(
    appointment_type: str,
    preferred_date: Optional[str] = None,
    preferred_time: Optional[str] = None,
    days_ahead: int = 14,
) -> dict:
    """Find available appointment slots.

    Returns a list of available time slots for the specified appointment type.
    """
    try:
        appt_type = AppointmentType(appointment_type)
    except ValueError:
        return {
            "success": False,
            "error": f"Invalid appointment type: {appointment_type}",
            "available_slots": [],
        }

    scheduler = get_scheduler()

    # Calculate date range using timezone-aware datetime
    now = datetime.now(timezone.utc)
    start_date = now
    end_date = now + timedelta(days=days_ahead)

    if preferred_date:
        try:
            # Parse as naive datetime and make it timezone-aware
            preferred_dt = datetime.strptime(preferred_date, "%Y-%m-%d")
            preferred_dt = preferred_dt.replace(tzinfo=timezone.utc)
            start_date = preferred_dt
            end_date = preferred_dt + timedelta(days=1)
        except ValueError:
            pass

    slots = await scheduler.find_availability(
        appointment_type=appt_type,
        start_date=start_date,
        end_date=end_date,
        preferred_time=preferred_time,
    )

    return {
        "success": True,
        "available_slots": [slot.model_dump() for slot in slots],
    }


async def book_appointment_tool(
    patient_name: str,
    patient_phone: str,
    appointment_type: str,
    start_time: str,
    reason: Optional[str] = None,
    new_patient: bool = False,
) -> dict:
    """Book a new appointment.

    Creates a new appointment with the specified details.
    """
    try:
        appt_type = AppointmentType(appointment_type)
    except ValueError:
        return {
            "success": False,
            "error": f"Invalid appointment type: {appointment_type}",
        }

    try:
        # Parse ISO format datetime
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    except ValueError:
        return {
            "success": False,
            "error": f"Invalid start time format: {start_time}",
        }

    scheduler = get_scheduler()

    # Find provider and location (mock defaults)
    provider_id = "dr-john-li"
    location_id = "main-office"

    # Calculate end time (30 minute appointment) using timedelta
    end_dt = start_dt + timedelta(minutes=30)

    # Generate idempotency key for this booking
    idempotency_key = generate_idempotency_key(
        patient_name=patient_name,
        patient_phone=patient_phone,
        appointment_type=appointment_type,
        start_time=start_time,
    )

    # Validate that the requested slot is available
    available_slots = await scheduler.find_availability(
        appointment_type=appt_type,
        start_date=start_dt,
        end_date=start_dt + timedelta(minutes=1),
        provider_id=provider_id,
        location_id=location_id,
    )
    
    slot_available = any(
        slot.start_time == start_dt and slot.end_time == end_dt
        for slot in available_slots
    )
    
    if not slot_available:
        return {
            "success": False,
            "error": "Requested time slot is no longer available. Please select another time.",
            "alternative_slots": [],
        }

    result = await scheduler.create_appointment(
        patient_name=patient_name,
        patient_phone=patient_phone,
        appointment_type=appt_type,
        provider_id=provider_id,
        location_id=location_id,
        start_time=start_dt,
        end_time=end_dt,
        reason=reason,
        new_patient=new_patient,
        idempotency_key=idempotency_key,
    )

    if result.success and result.appointment:
        return {
            "success": True,
            "appointment": result.appointment.model_dump(),
            "message": f"Appointment booked for {result.appointment.start_time.strftime('%Y-%m-%d %H:%M')}",
        }
    else:
        return {
            "success": False,
            "error": result.error_message or "Failed to book appointment",
            "alternative_slots": [
                slot.model_dump() for slot in result.alternative_slots
            ],
        }


async def reschedule_appointment_tool(
    appointment_id: str,
    new_start_time: str,
) -> dict:
    """Reschedule an existing appointment.

    Changes the time of an existing appointment.
    """
    try:
        new_dt = datetime.fromisoformat(new_start_time.replace("Z", "+00:00"))
    except ValueError:
        return {
            "success": False,
            "error": f"Invalid new start time format: {new_start_time}",
        }

    scheduler = get_scheduler()

    # Generate idempotency key
    idempotency_key = generate_idempotency_key(
        appointment_id=appointment_id,
        new_start_time=new_start_time,
    )

    result = await scheduler.reschedule_appointment(
        appointment_id=appointment_id,
        new_start_time=new_dt,
        new_end_time=new_dt + timedelta(minutes=30),
        idempotency_key=idempotency_key,
    )

    if result.success and result.appointment:
        return {
            "success": True,
            "appointment": result.appointment.model_dump(),
            "message": f"Appointment rescheduled to {result.appointment.start_time.strftime('%Y-%m-%d %H:%M')}",
        }
    else:
        return {
            "success": False,
            "error": result.error_message or "Failed to reschedule appointment",
        }


async def cancel_appointment_tool(
    appointment_id: str,
    confirmation: str,
) -> dict:
    """Cancel an existing appointment.

    Cancels an appointment after explicit confirmation.
    """
    if confirmation.lower() != "yes":
        return {
            "success": False,
            "error": "Cancellation not confirmed. Please confirm with 'yes'.",
        }

    scheduler = get_scheduler()

    # Generate idempotency key
    idempotency_key = generate_idempotency_key(
        appointment_id=appointment_id,
        action="cancel",
    )

    result = await scheduler.cancel_appointment(
        appointment_id, idempotency_key=idempotency_key
    )

    if result.success and result.appointment:
        return {
            "success": True,
            "appointment": result.appointment.model_dump(),
            "message": "Appointment canceled successfully.",
        }
    else:
        return {
            "success": False,
            "error": result.error_message or "Failed to cancel appointment",
        }


async def confirm_appointment_tool(
    appointment_id: str,
    confirmation: str,
) -> dict:
    """Confirm an existing appointment.

    Confirms an appointment after explicit confirmation.
    """
    if confirmation.lower() != "yes":
        return {
            "success": False,
            "error": "Confirmation not confirmed. Please confirm with 'yes'.",
        }

    scheduler = get_scheduler()

    # Generate idempotency key
    idempotency_key = generate_idempotency_key(
        appointment_id=appointment_id,
        action="confirm",
    )

    result = await scheduler.confirm_appointment(
        appointment_id, idempotency_key=idempotency_key
    )

    if result.success and result.appointment:
        return {
            "success": True,
            "appointment": result.appointment.model_dump(),
            "message": "Appointment confirmed successfully.",
        }
    else:
        return {
            "success": False,
            "error": result.error_message or "Failed to confirm appointment",
        }


async def lookup_patient_tool(phone: str) -> dict:
    """Look up a patient by phone number.

    Returns patient information if found, or indicates a new patient.
    """
    scheduler = get_scheduler()

    patient = await scheduler.lookup_patient_by_phone(phone)

    if patient:
        return {
            "success": True,
            "found": True,
            "patient": patient,
        }
    else:
        return {
            "success": True,
            "found": False,
            "message": "Patient not found in system. This appears to be a new patient.",
        }


async def get_appointment_tool(appointment_id: str) -> dict:
    """Get details of a specific appointment."""
    scheduler = get_scheduler()

    appointment = await scheduler.get_appointment(appointment_id)

    if appointment:
        return {
            "success": True,
            "appointment": appointment.model_dump(),
        }
    else:
        return {
            "success": False,
            "error": "Appointment not found.",
        }


async def get_office_info_tool(info_type: str = "hours") -> dict:
    """Get office information.

    Returns office hours, address, phone, or other configured information.
    """
    # Placeholder for office configuration - should be moved to a config file
    office_info = {
        "hours": {
            "monday": "8:00 AM - 5:00 PM",
            "tuesday": "8:00 AM - 5:00 PM",
            "wednesday": "8:00 AM - 5:00 PM",
            "thursday": "8:00 AM - 5:00 PM",
            "friday": "8:00 AM - 1:00 PM",
            "saturday": "Closed",
            "sunday": "Closed",
        },
        "address": "John Li, MD - ENT Specialists\n[Address to be provided by Dr. Li]",
        "phone": "[Office phone number to be provided by Dr. Li]",
        "provider": "Dr. John Li, MD",
        "specialty": "ENT / Otolaryngology",
    }

    if info_type in office_info:
        return {
            "success": True,
            "info_type": info_type,
            "info": office_info[info_type],
        }
    else:
        return {
            "success": False,
            "error": f"Unknown info type: {info_type}",
        }


# Tool registration for Dograh

TOOLS = [
    {
        "name": "find_availability",
        "description": "Find available appointment slots for scheduling",
        "input_schema": FindAvailabilityToolInput.model_json_schema(),
        "handler": find_availability_tool,
    },
    {
        "name": "book_appointment",
        "description": "Book a new appointment with the patient",
        "input_schema": BookAppointmentToolInput.model_json_schema(),
        "handler": book_appointment_tool,
    },
    {
        "name": "reschedule_appointment",
        "description": "Reschedule an existing appointment to a new time",
        "input_schema": RescheduleAppointmentToolInput.model_json_schema(),
        "handler": reschedule_appointment_tool,
    },
    {
        "name": "cancel_appointment",
        "description": "Cancel an existing appointment",
        "input_schema": CancelAppointmentToolInput.model_json_schema(),
        "handler": cancel_appointment_tool,
    },
    {
        "name": "confirm_appointment",
        "description": "Confirm an existing appointment",
        "input_schema": ConfirmAppointmentToolInput.model_json_schema(),
        "handler": confirm_appointment_tool,
    },
    {
        "name": "lookup_patient",
        "description": "Look up a patient by phone number to check if they are new or existing",
        "input_schema": LookupPatientToolInput.model_json_schema(),
        "handler": lookup_patient_tool,
    },
    {
        "name": "get_appointment",
        "description": "Get details of a specific appointment by ID",
        "input_schema": GetAppointmentToolInput.model_json_schema(),
        "handler": get_appointment_tool,
    },
    {
        "name": "get_office_info",
        "description": "Get office information (hours, address, phone)",
        "input_schema": GetOfficeInfoToolInput.model_json_schema(),
        "handler": get_office_info_tool,
    },
]