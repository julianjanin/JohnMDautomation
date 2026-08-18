"""Scheduler abstraction for John Li ENT practice.

This module defines the abstract interface for scheduling operations.
The actual implementation can be swapped out for different scheduling systems
(EHR, practice management, etc.).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from .models import (
    Appointment,
    AppointmentType,
    AvailabilitySlot,
    SchedulingRequest,
    SchedulingResult,
)


class SchedulerAdapter(ABC):
    """Abstract base class for scheduler adapters.

    This interface defines the contract for scheduling operations.
    Implementations can integrate with EHR systems, practice management
    systems, or other scheduling backends.
    """

    @abstractmethod
    async def list_appointment_types(self) -> list[AppointmentType]:
        """List all available appointment types."""
        pass

    @abstractmethod
    async def find_availability(
        self,
        appointment_type: AppointmentType,
        start_date: datetime,
        end_date: datetime,
        provider_id: Optional[str] = None,
        location_id: Optional[str] = None,
        preferred_time: Optional[str] = None,
    ) -> list[AvailabilitySlot]:
        """Find available appointment slots matching the criteria."""
        pass

    @abstractmethod
    async def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        """Get an appointment by its ID."""
        pass

    @abstractmethod
    async def create_appointment(
        self,
        patient_name: str,
        patient_phone: str,
        appointment_type: AppointmentType,
        provider_id: str,
        location_id: str,
        start_time: datetime,
        end_time: datetime,
        reason: Optional[str] = None,
        new_patient: bool = False,
    ) -> SchedulingResult:
        """Create a new appointment."""
        pass

    @abstractmethod
    async def reschedule_appointment(
        self,
        appointment_id: str,
        new_start_time: datetime,
        new_end_time: datetime,
    ) -> SchedulingResult:
        """Reschedule an existing appointment."""
        pass

    @abstractmethod
    async def cancel_appointment(self, appointment_id: str) -> SchedulingResult:
        """Cancel an existing appointment."""
        pass

    @abstractmethod
    async def confirm_appointment(self, appointment_id: str) -> SchedulingResult:
        """Confirm an existing appointment."""
        pass

    @abstractmethod
    async def lookup_patient_by_phone(
        self, phone: str
    ) -> Optional[dict]:
        """Look up a patient by phone number.

        Returns patient info if found, None otherwise.
        """
        pass


class MockSchedulerAdapter(SchedulerAdapter):
    """Mock scheduler adapter for testing and local development.

    This implementation uses deterministic synthetic data and does not
    require external credentials or systems.
    """

    def __init__(self):
        """Initialize the mock scheduler with synthetic data."""
        self._appointments: dict[str, Appointment] = {}
        self._providers = {
            "dr-john-li": AppointmentType.NEW_PATIENT_CONSULT,
        }
        self._locations = {
            "main-office": "Main Office",
        }
        self._appointment_types = list(AppointmentType)

    async def list_appointment_types(self) -> list[AppointmentType]:
        """List all available appointment types."""
        return self._appointment_types

    async def find_availability(
        self,
        appointment_type: AppointmentType,
        start_date: datetime,
        end_date: datetime,
        provider_id: Optional[str] = None,
        location_id: Optional[str] = None,
        preferred_time: Optional[str] = None,
    ) -> list[AvailabilitySlot]:
        """Find available appointment slots matching the criteria."""
        slots = []

        # Generate mock availability for the next 2 weeks
        current = start_date
        while current < end_date:
            # Skip weekends for mock data
            if current.weekday() < 5:
                # Generate slots at 9am, 10:30am, 2pm, 3:30pm
                for hour, minute in [(9, 0), (10, 30), (14, 0), (15, 30)]:
                    slot_start = current.replace(hour=hour, minute=minute)
                    slot_end = current.replace(
                        hour=hour + 1, minute=minute
                    ) if hour < 15 else current.replace(hour=hour, minute=minute + 30)

                    # Check if slot is already booked
                    is_booked = any(
                        a.start_time == slot_start
                        for a in self._appointments.values()
                        if a.status == "scheduled"
                    )

                    if not is_booked:
                        slots.append(
                            AvailabilitySlot(
                                start_time=slot_start,
                                end_time=slot_end,
                                provider_id=provider_id or "dr-john-li",
                                location_id=location_id or "main-office",
                                appointment_type=appointment_type,
                            )
                        )

            # Move to next day
            current = datetime(
                current.year, current.month, current.day,
                hour=0, minute=0, second=0, microsecond=0
            )
            current = datetime.fromtimestamp(current.timestamp() + 86400)

        return slots[:10]  # Return up to 10 slots

    async def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        """Get an appointment by its ID."""
        return self._appointments.get(appointment_id)

    async def create_appointment(
        self,
        patient_name: str,
        patient_phone: str,
        appointment_type: AppointmentType,
        provider_id: str,
        location_id: str,
        start_time: datetime,
        end_time: datetime,
        reason: Optional[str] = None,
        new_patient: bool = False,
    ) -> SchedulingResult:
        """Create a new appointment."""
        # Check for double booking
        for existing in self._appointments.values():
            if (
                existing.start_time == start_time
                and existing.status == "scheduled"
            ):
                return SchedulingResult(
                    success=False,
                    error_message="Slot is no longer available. Please select another time.",
                )

        appointment = Appointment(
            patient_name=patient_name,
            patient_phone=patient_phone,
            appointment_type=appointment_type,
            provider_id=provider_id,
            location_id=location_id,
            start_time=start_time,
            end_time=end_time,
            status="scheduled",
        )

        self._appointments[appointment.id] = appointment
        return SchedulingResult(success=True, appointment=appointment)

    async def reschedule_appointment(
        self,
        appointment_id: str,
        new_start_time: datetime,
        new_end_time: datetime,
    ) -> SchedulingResult:
        """Reschedule an existing appointment."""
        appointment = self._appointments.get(appointment_id)
        if not appointment:
            return SchedulingResult(
                success=False,
                error_message="Appointment not found.",
            )

        # Check for double booking
        for existing in self._appointments.values():
            if (
                existing.id != appointment_id
                and existing.start_time == new_start_time
                and existing.status == "scheduled"
            ):
                return SchedulingResult(
                    success=False,
                    error_message="New slot is no longer available. Please select another time.",
                )

        appointment.start_time = new_start_time
        appointment.end_time = new_end_time
        appointment.updated_at = datetime.utcnow()
        return SchedulingResult(success=True, appointment=appointment)

    async def cancel_appointment(self, appointment_id: str) -> SchedulingResult:
        """Cancel an existing appointment."""
        appointment = self._appointments.get(appointment_id)
        if not appointment:
            return SchedulingResult(
                success=False,
                error_message="Appointment not found.",
            )

        appointment.status = "canceled"
        appointment.updated_at = datetime.utcnow()
        return SchedulingResult(success=True, appointment=appointment)

    async def confirm_appointment(self, appointment_id: str) -> SchedulingResult:
        """Confirm an existing appointment."""
        appointment = self._appointments.get(appointment_id)
        if not appointment:
            return SchedulingResult(
                success=False,
                error_message="Appointment not found.",
            )

        if appointment.status == "canceled":
            return SchedulingResult(
                success=False,
                error_message="Cannot confirm a canceled appointment.",
            )

        appointment.status = "confirmed"
        appointment.updated_at = datetime.utcnow()
        return SchedulingResult(success=True, appointment=appointment)

    async def lookup_patient_by_phone(
        self, phone: str
    ) -> Optional[dict]:
        """Look up a patient by phone number."""
        # Mock implementation - return None to indicate new patient
        return None

    def add_mock_appointment(self, appointment: Appointment) -> None:
        """Add a mock appointment (for testing)."""
        self._appointments[appointment.id] = appointment

    def clear_appointments(self) -> None:
        """Clear all mock appointments (for testing)."""
        self._appointments.clear()