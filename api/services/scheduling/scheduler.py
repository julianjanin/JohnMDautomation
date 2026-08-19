"""Scheduler abstraction for John Li ENT practice.

This module defines the abstract interface for scheduling operations.
The actual implementation can be swapped out for different scheduling systems
(EHR, practice management, etc.).
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

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
        idempotency_key: Optional[str] = None,
    ) -> SchedulingResult:
        """Create a new appointment."""
        pass

    @abstractmethod
    async def reschedule_appointment(
        self,
        appointment_id: str,
        new_start_time: datetime,
        new_end_time: datetime,
        idempotency_key: Optional[str] = None,
    ) -> SchedulingResult:
        """Reschedule an existing appointment."""
        pass

    @abstractmethod
    async def cancel_appointment(
        self, appointment_id: str, idempotency_key: Optional[str] = None
    ) -> SchedulingResult:
        """Cancel an existing appointment."""
        pass

    @abstractmethod
    async def confirm_appointment(
        self, appointment_id: str, idempotency_key: Optional[str] = None
    ) -> SchedulingResult:
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

    # Daily slot start times (in 24-hour format)
    SLOT_START_TIMES = [
        (9, 0),   # 9:00 AM
        (10, 30), # 10:30 AM
        (14, 0),  # 2:00 PM
        (15, 30), # 3:30 PM
    ]

    # Appointment duration in minutes
    APPOINTMENT_DURATION_MINUTES = 30

    def __init__(self, practice_timezone: Optional[ZoneInfo] = None):
        """Initialize the mock scheduler with synthetic data.

        Args:
            practice_timezone: The timezone for scheduling. Defaults to
                America/New_York if not provided.
        """
        self._practice_tz = practice_timezone or ZoneInfo("America/New_York")
        self._appointments: dict[str, Appointment] = {}
        self._providers = {
            "dr-john-li": AppointmentType.NEW_PATIENT_CONSULT,
        }
        self._locations = {
            "main-office": "Main Office",
        }
        self._appointment_types = list(AppointmentType)
        
        # Synthetic patient fixtures
        self._patients = {
            "+15551234567": {
                "name": "John Doe",
                "phone": "+15551234567",
                "email": "john.doe@example.com",
            },
            "+15559876543": {
                "name": "Jane Smith",
                "phone": "+15559876543",
                "email": "jane.smith@example.com",
            },
        }

    @property
    def practice_timezone(self) -> ZoneInfo:
        """Get the practice timezone."""
        return self._practice_tz

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

        # Ensure start_date is timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=self._practice_tz)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=self._practice_tz)

        # Generate mock availability for the date range
        current = start_date
        while current < end_date:
            # Skip weekends (Monday=0, Sunday=6)
            if current.weekday() < 5:
                # Generate slots at configured times using timedelta for robust arithmetic
                for hour, minute in self.SLOT_START_TIMES:
                    # Use timedelta for robust slot end calculation
                    slot_start = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    slot_end = slot_start + timedelta(minutes=self.APPOINTMENT_DURATION_MINUTES)

                    # Check if slot is already booked (considering all active statuses)
                    is_booked = self._is_slot_booked(
                        slot_start, slot_end, provider_id, location_id
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

            # Move to next day using timedelta (not Unix timestamp arithmetic)
            current = current + timedelta(days=1)

        return slots[:10]  # Return up to 10 slots

    def _is_slot_booked(
        self,
        slot_start: datetime,
        slot_end: datetime,
        provider_id: Optional[str],
        location_id: Optional[str],
    ) -> bool:
        """Check if a slot is already booked by an active appointment.
        
        An appointment is considered "active" if its status is 'scheduled' or 'confirmed'.
        'canceled' appointments do not block slots.
        """
        for appointment in self._appointments.values():
            # Only check active appointments (scheduled or confirmed)
            if appointment.status not in ("scheduled", "confirmed"):
                continue
            
            # Check provider match
            if provider_id and appointment.provider_id != provider_id:
                continue
            
            # Check location match
            if location_id and appointment.location_id != location_id:
                continue
            
            # Check for time overlap using half-open interval [start, end)
            # Two intervals [a, b) and [c, d) overlap if a < d and c < b
            if self._intervals_overlap(
                appointment.start_time, appointment.end_time, slot_start, slot_end
            ):
                return True
        
        return False

    def _intervals_overlap(
        self, start1: datetime, end1: datetime, start2: datetime, end2: datetime
    ) -> bool:
        """Check if two time intervals overlap using half-open interval semantics.
        
        Intervals [start1, end1) and [start2, end2) overlap if:
        start1 < end2 AND start2 < end1
        
        This is the standard half-open interval overlap check.
        """
        return start1 < end2 and start2 < end1

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
        idempotency_key: Optional[str] = None,
    ) -> SchedulingResult:
        """Create a new appointment."""
        # Check for idempotency - if same key was used, return existing result
        if idempotency_key:
            for existing in self._appointments.values():
                if existing.idempotency_key == idempotency_key:
                    if existing.status == "canceled":
                        # Allow retry for canceled appointments
                        pass
                    else:
                        # Return existing appointment for same key
                        return SchedulingResult(
                            success=True,
                            appointment=existing,
                        )

        # Check for double booking with proper interval overlap detection
        for existing in self._appointments.values():
            # Only check active appointments
            if existing.status not in ("scheduled", "confirmed"):
                continue
            
            # Check provider and location match
            if existing.provider_id == provider_id and existing.location_id == location_id:
                # Check for time overlap
                if self._intervals_overlap(
                    existing.start_time, existing.end_time, start_time, end_time
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
            idempotency_key=idempotency_key,
        )

        self._appointments[appointment.id] = appointment
        return SchedulingResult(success=True, appointment=appointment)

    async def reschedule_appointment(
        self,
        appointment_id: str,
        new_start_time: datetime,
        new_end_time: datetime,
        idempotency_key: Optional[str] = None,
    ) -> SchedulingResult:
        """Reschedule an existing appointment."""
        appointment = self._appointments.get(appointment_id)
        if not appointment:
            return SchedulingResult(
                success=False,
                error_message="Appointment not found.",
            )

        # Check for idempotency
        if idempotency_key:
            for existing in self._appointments.values():
                if existing.idempotency_key == idempotency_key and existing.id != appointment_id:
                    if existing.status not in ("canceled",):
                        return SchedulingResult(
                            success=True,
                            appointment=existing,
                        )

        # Check for double booking with other appointments
        for existing in self._appointments.values():
            if existing.id == appointment_id:
                continue
            if existing.status not in ("scheduled", "confirmed"):
                continue
            if existing.provider_id == appointment.provider_id and existing.location_id == appointment.location_id:
                if self._intervals_overlap(
                    existing.start_time, existing.end_time, new_start_time, new_end_time
                ):
                    return SchedulingResult(
                        success=False,
                        error_message="New slot is no longer available. Please select another time.",
                    )

        appointment.start_time = new_start_time
        appointment.end_time = new_end_time
        appointment.updated_at = datetime.now(timezone.utc)
        appointment.idempotency_key = idempotency_key
        return SchedulingResult(success=True, appointment=appointment)

    async def cancel_appointment(
        self, appointment_id: str, idempotency_key: Optional[str] = None
    ) -> SchedulingResult:
        """Cancel an existing appointment."""
        appointment = self._appointments.get(appointment_id)
        if not appointment:
            return SchedulingResult(
                success=False,
                error_message="Appointment not found.",
            )

        appointment.status = "canceled"
        appointment.updated_at = datetime.now(timezone.utc)
        appointment.idempotency_key = idempotency_key
        return SchedulingResult(success=True, appointment=appointment)

    async def confirm_appointment(
        self, appointment_id: str, idempotency_key: Optional[str] = None
    ) -> SchedulingResult:
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
        appointment.updated_at = datetime.now(timezone.utc)
        appointment.idempotency_key = idempotency_key
        return SchedulingResult(success=True, appointment=appointment)

    async def lookup_patient_by_phone(
        self, phone: str
    ) -> Optional[dict]:
        """Look up a patient by phone number.
        
        Returns synthetic patient data if found, None otherwise.
        """
        return self._patients.get(phone)

    def add_mock_appointment(self, appointment: Appointment) -> None:
        """Add a mock appointment (for testing)."""
        self._appointments[appointment.id] = appointment

    def clear_appointments(self) -> None:
        """Clear all mock appointments (for testing)."""
        self._appointments.clear()

    def clear_patients(self) -> None:
        """Clear all synthetic patients (for testing)."""
        self._patients.clear()

    def add_synthetic_patient(self, phone: str, name: str) -> None:
        """Add a synthetic patient for testing."""
        self._patients[phone] = {
            "name": name,
            "phone": phone,
            "email": f"{name.lower().replace(' ', '.')}@example.com",
        }