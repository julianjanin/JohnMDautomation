"""Scheduling service layer for John Li ENT practice.

This module provides a service layer that wraps the scheduler adapter
and provides business logic for scheduling operations.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from .models import (
    Appointment,
    AppointmentType,
    AvailabilitySlot,
    CallDisposition,
    CallIntent,
    SchedulingRequest,
    SchedulingResult,
    StaffEscalation,
)
from .scheduler import MockSchedulerAdapter


class SchedulingService:
    """Service layer for scheduling operations.
    
    This class provides business logic for scheduling operations,
    including validation, idempotency, and state management.
    """
    
    def __init__(self, scheduler: Optional[MockSchedulerAdapter] = None):
        """Initialize the scheduling service.
        
        Args:
            scheduler: Optional scheduler adapter. If not provided, a new
                      MockSchedulerAdapter will be created.
        """
        self._scheduler = scheduler or MockSchedulerAdapter()
    
    @property
    def scheduler(self) -> MockSchedulerAdapter:
        """Get the scheduler adapter."""
        return self._scheduler
    
    async def find_availability(
        self,
        appointment_type: AppointmentType,
        preferred_date: Optional[datetime] = None,
        preferred_time: Optional[str] = None,
        days_ahead: int = 14,
        provider_id: Optional[str] = None,
        location_id: Optional[str] = None,
    ) -> list[AvailabilitySlot]:
        """Find available appointment slots.
        
        Args:
            appointment_type: Type of appointment to find slots for
            preferred_date: Preferred date (if None, searches from today)
            preferred_time: Preferred time of day (morning, afternoon, evening)
            days_ahead: Number of days to search ahead
            provider_id: Optional provider ID to filter by
            location_id: Optional location ID to filter by
            
        Returns:
            List of available time slots
        """
        now = datetime.now(timezone.utc)
        start_date = preferred_date or now
        end_date = start_date + timedelta(days=days_ahead)
        
        return await self._scheduler.find_availability(
            appointment_type=appointment_type,
            start_date=start_date,
            end_date=end_date,
            provider_id=provider_id,
            location_id=location_id,
            preferred_time=preferred_time,
        )
    
    async def book_appointment(
        self,
        patient_name: str,
        patient_phone: str,
        appointment_type: AppointmentType,
        start_time: datetime,
        reason: Optional[str] = None,
        new_patient: bool = False,
        provider_id: Optional[str] = None,
        location_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> SchedulingResult:
        """Book a new appointment.
        
        Args:
            patient_name: Patient's full name
            patient_phone: Patient's phone number
            appointment_type: Type of appointment
            start_time: Appointment start time
            reason: Reason for appointment
            new_patient: Whether this is a new patient
            provider_id: Provider ID (defaults to dr-john-li)
            location_id: Location ID (defaults to main-office)
            idempotency_key: Optional idempotency key for retry safety
            
        Returns:
            SchedulingResult with success status and appointment details
        """
        # Validate provider and location
        provider_id = provider_id or "dr-john-li"
        location_id = location_id or "main-office"
        
        # Calculate end time (30 minute appointment)
        end_time = start_time + timedelta(minutes=30)
        
        # Validate that the requested slot is available
        available_slots = await self._scheduler.find_availability(
            appointment_type=appointment_type,
            start_date=start_time,
            end_date=start_time + timedelta(minutes=1),
            provider_id=provider_id,
            location_id=location_id,
        )
        
        slot_available = any(
            slot.start_time == start_time and slot.end_time == end_time
            for slot in available_slots
        )
        
        if not slot_available:
            return SchedulingResult(
                success=False,
                error_message="Requested time slot is no longer available. Please select another time.",
            )
        
        # Create the appointment
        return await self._scheduler.create_appointment(
            patient_name=patient_name,
            patient_phone=patient_phone,
            appointment_type=appointment_type,
            provider_id=provider_id,
            location_id=location_id,
            start_time=start_time,
            end_time=end_time,
            reason=reason,
            new_patient=new_patient,
            idempotency_key=idempotency_key,
        )
    
    async def reschedule_appointment(
        self,
        appointment_id: str,
        new_start_time: datetime,
        idempotency_key: Optional[str] = None,
    ) -> SchedulingResult:
        """Reschedule an existing appointment.
        
        Args:
            appointment_id: ID of the appointment to reschedule
            new_start_time: New start time
            idempotency_key: Optional idempotency key for retry safety
            
        Returns:
            SchedulingResult with success status and appointment details
        """
        new_end_time = new_start_time + timedelta(minutes=30)
        
        return await self._scheduler.reschedule_appointment(
            appointment_id=appointment_id,
            new_start_time=new_start_time,
            new_end_time=new_end_time,
            idempotency_key=idempotency_key,
        )
    
    async def cancel_appointment(
        self,
        appointment_id: str,
        confirmation: str,
        idempotency_key: Optional[str] = None,
    ) -> SchedulingResult:
        """Cancel an existing appointment.
        
        Args:
            appointment_id: ID of the appointment to cancel
            confirmation: Must be 'yes' to confirm cancellation
            idempotency_key: Optional idempotency key for retry safety
            
        Returns:
            SchedulingResult with success status and appointment details
        """
        if confirmation.lower() != "yes":
            return SchedulingResult(
                success=False,
                error_message="Cancellation not confirmed. Please confirm with 'yes'.",
            )
        
        return await self._scheduler.cancel_appointment(
            appointment_id=appointment_id,
            idempotency_key=idempotency_key,
        )
    
    async def confirm_appointment(
        self,
        appointment_id: str,
        confirmation: str,
        idempotency_key: Optional[str] = None,
    ) -> SchedulingResult:
        """Confirm an existing appointment.
        
        Args:
            appointment_id: ID of the appointment to confirm
            confirmation: Must be 'yes' to confirm
            idempotency_key: Optional idempotency key for retry safety
            
        Returns:
            SchedulingResult with success status and appointment details
        """
        if confirmation.lower() != "yes":
            return SchedulingResult(
                success=False,
                error_message="Confirmation not confirmed. Please confirm with 'yes'.",
            )
        
        return await self._scheduler.confirm_appointment(
            appointment_id=appointment_id,
            idempotency_key=idempotency_key,
        )
    
    async def lookup_patient(self, phone: str) -> Optional[dict]:
        """Look up a patient by phone number.
        
        Args:
            phone: Patient's phone number
            
        Returns:
            Patient info if found, None otherwise
        """
        return await self._scheduler.lookup_patient_by_phone(phone)
    
    async def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        """Get an appointment by ID.
        
        Args:
            appointment_id: ID of the appointment
            
        Returns:
            Appointment if found, None otherwise
        """
        return await self._scheduler.get_appointment(appointment_id)
    
    async def get_office_info(self, info_type: str = "hours") -> dict:
        """Get office information.
        
        Args:
            info_type: Type of information to retrieve (hours, address, phone)
            
        Returns:
            Dictionary with office information
        """
        # This should be moved to a configuration file in the future
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
            return office_info[info_type]
        
        return {"error": f"Unknown info type: {info_type}"}
    
    async def create_staff_escalation(
        self,
        reason: str,
        caller_name: str,
        caller_phone: str,
        message: Optional[str] = None,
    ) -> StaffEscalation:
        """Create a staff escalation request.
        
        Args:
            reason: Reason for escalation
            caller_name: Caller's name
            caller_phone: Caller's phone number
            message: Optional message
            
        Returns:
            StaffEscalation object
        """
        return StaffEscalation(
            reason=reason,
            caller_name=caller_name,
            caller_phone=caller_phone,
            message=message,
        )
    
    def list_appointment_types(self) -> list[AppointmentType]:
        """List all available appointment types.
        
        Returns:
            List of appointment types
        """
        return self._scheduler.list_appointment_types()


# Global service instance (in production, this would be injected via DI)
_service: Optional[SchedulingService] = None


def get_scheduling_service() -> SchedulingService:
    """Get the scheduling service instance."""
    global _service
    if _service is None:
        _service = SchedulingService()
    return _service


def reset_scheduling_service() -> None:
    """Reset the scheduling service instance (for testing)."""
    global _service
    _service = None