"""API routes for John Li ENT scheduling operations.

These routes provide HTTP endpoints for the scheduling service,
which can be called by Dograh workflows.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from api.services.scheduling.service import get_scheduling_service, reset_scheduling_service
from api.services.scheduling.models import (
    AppointmentType,
    CallDisposition,
)

router = APIRouter(prefix="/scheduling")

__all__ = [
    "router",
]


@router.get("/appointment-types")
async def list_appointment_types():
    """List all available appointment types."""
    service = get_scheduling_service()
    types = service.list_appointment_types()
    return {
        "success": True,
        "appointment_types": [t.value for t in types],
    }


@router.get("/availability")
async def find_availability(
    appointment_type: str,
    preferred_date: Optional[str] = None,
    preferred_time: Optional[str] = None,
    days_ahead: int = 14,
) -> dict:
    """Find available appointment slots.
    
    Args:
        appointment_type: Type of appointment (e.g., 'new_patient_consult')
        preferred_date: Preferred date in YYYY-MM-DD format
        preferred_time: Preferred time of day (morning, afternoon, evening)
        days_ahead: Number of days to search ahead
    """
    service = get_scheduling_service()
    
    try:
        appt_type = AppointmentType(appointment_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid appointment type: {appointment_type}",
        )
    
    start_date = None
    if preferred_date:
        try:
            start_date = datetime.strptime(preferred_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {preferred_date}. Use YYYY-MM-DD.",
            )
    
    slots = await service.find_availability(
        appointment_type=appt_type,
        preferred_date=start_date,
        preferred_time=preferred_time,
        days_ahead=days_ahead,
    )
    
    return {
        "success": True,
        "available_slots": [slot.model_dump() for slot in slots],
    }


@router.post("/book")
async def book_appointment(
    patient_name: str,
    patient_phone: str,
    appointment_type: str,
    start_time: str,
    reason: Optional[str] = None,
    new_patient: bool = False,
) -> dict:
    """Book a new appointment.
    
    Args:
        patient_name: Patient's full name
        patient_phone: Patient's phone number
        appointment_type: Type of appointment
        start_time: Appointment start time in ISO format
        reason: Reason for appointment
        new_patient: Whether this is a new patient
    """
    service = get_scheduling_service()
    
    try:
        appt_type = AppointmentType(appointment_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid appointment type: {appointment_type}",
        )
    
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid start time format: {start_time}. Use ISO format.",
        )
    
    result = await service.book_appointment(
        patient_name=patient_name,
        patient_phone=patient_phone,
        appointment_type=appt_type,
        start_time=start_dt,
        reason=reason,
        new_patient=new_patient,
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
            "alternative_slots": [slot.model_dump() for slot in result.alternative_slots],
        }


@router.post("/reschedule")
async def reschedule_appointment(
    appointment_id: str,
    new_start_time: str,
) -> dict:
    """Reschedule an existing appointment.
    
    Args:
        appointment_id: ID of the appointment to reschedule
        new_start_time: New start time in ISO format
    """
    service = get_scheduling_service()
    
    try:
        new_dt = datetime.fromisoformat(new_start_time.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid new start time format: {new_start_time}. Use ISO format.",
        )
    
    result = await service.reschedule_appointment(
        appointment_id=appointment_id,
        new_start_time=new_dt,
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


@router.post("/cancel")
async def cancel_appointment(
    appointment_id: str,
    confirmation: str,
) -> dict:
    """Cancel an existing appointment.
    
    Args:
        appointment_id: ID of the appointment to cancel
        confirmation: Must be 'yes' to confirm cancellation
    """
    service = get_scheduling_service()
    
    result = await service.cancel_appointment(
        appointment_id=appointment_id,
        confirmation=confirmation,
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


@router.post("/confirm")
async def confirm_appointment(
    appointment_id: str,
    confirmation: str,
) -> dict:
    """Confirm an existing appointment.
    
    Args:
        appointment_id: ID of the appointment to confirm
        confirmation: Must be 'yes' to confirm
    """
    service = get_scheduling_service()
    
    result = await service.confirm_appointment(
        appointment_id=appointment_id,
        confirmation=confirmation,
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


@router.get("/patient")
async def lookup_patient(phone: str) -> dict:
    """Look up a patient by phone number.
    
    Args:
        phone: Patient's phone number
    """
    service = get_scheduling_service()
    
    patient = await service.lookup_patient(phone)
    
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


@router.get("/appointment/{appointment_id}")
async def get_appointment(appointment_id: str) -> dict:
    """Get details of a specific appointment.
    
    Args:
        appointment_id: ID of the appointment
    """
    service = get_scheduling_service()
    
    appointment = await service.get_appointment(appointment_id)
    
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


@router.get("/office-info")
async def get_office_info(info_type: str = "hours") -> dict:
    """Get office information.
    
    Args:
        info_type: Type of information to retrieve (hours, address, phone)
    """
    service = get_scheduling_service()
    
    info = await service.get_office_info(info_type)
    
    if "error" in info:
        return {
            "success": False,
            "error": info["error"],
        }
    else:
        return {
            "success": True,
            "info_type": info_type,
            "info": info,
        }


@router.post("/escalation")
async def create_escalation(
    reason: str,
    caller_name: str,
    caller_phone: str,
    message: Optional[str] = None,
) -> dict:
    """Create a staff escalation request.
    
    Args:
        reason: Reason for escalation
        caller_name: Caller's name
        caller_phone: Caller's phone number
        message: Optional message
    """
    service = get_scheduling_service()
    
    escalation = await service.create_staff_escalation(
        reason=reason,
        caller_name=caller_name,
        caller_phone=caller_phone,
        message=message,
    )
    
    return {
        "success": True,
        "escalation": escalation.model_dump(),
    }