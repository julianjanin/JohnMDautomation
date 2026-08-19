"""Scheduling domain models for John Li ENT practice.

This module defines the core domain entities for the scheduling system.
These are separate from the main Dograh database models and represent
the medical office scheduling domain.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AppointmentType(str, Enum):
    """ENT appointment types for John Li, MD."""

    NEW_PATIENT_CONSULT = "new_patient_consult"
    FOLLOW_UP = "follow_up"
    PROCEDURE_CONSULT = "procedure_consult"
    POST_OP_FOLLOW_UP = "post_op_follow_up"
    EMERGENCY = "emergency"
    ROUTINE_CHECKUP = "routine_checkup"


class CallIntent(str, Enum):
    """Call intents for the inbound virtual receptionist."""

    NEW_APPOINTMENT = "new_appointment"
    CONFIRM_APPOINTMENT = "confirm_appointment"
    RESCHEDULE_APPOINTMENT = "reschedule_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    OFFICE_INFORMATION = "office_information"
    LEAVE_MESSAGE = "leave_message"
    CLINICAL_QUESTION = "clinical_question"
    HUMAN_REQUEST = "human_request"
    OTHER = "other"
    EMERGENCY_OR_URGENT_ESCALATION = "emergency_or_urgent_escalation"


class CallDisposition(str, Enum):
    """Call disposition values for tracking call outcomes."""

    APPOINTMENT_BOOKED = "appointment_booked"
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    APPOINTMENT_RESCHEDULED = "appointment_rescheduled"
    APPOINTMENT_CANCELED = "appointment_canceled"
    OFFICE_INFO_PROVIDED = "office_info_provided"
    MESSAGE_LEFT = "message_left"
    ESCALATED_TO_STAFF = "escalated_to_staff"
    CLINICAL_QUESTION_ESCALATED = "clinical_question_escalated"
    CALL_ENDED = "call_ended"
    NO_ANSWER = "no_answer"
    VOICEMAIL = "voicemail"
    BUSY = "busy"
    FAILED = "failed"


class Provider(BaseModel):
    """Medical provider information."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    specialty: str = "ENT / Otolaryngology"
    is_active: bool = True


class Location(BaseModel):
    """Office location information."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    address: str
    phone_number: str
    is_active: bool = True


class Appointment(BaseModel):
    """Appointment model for scheduling."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_name: str
    patient_phone: str
    appointment_type: AppointmentType
    provider_id: str
    location_id: str
    start_time: datetime
    end_time: datetime
    status: str = "scheduled"  # scheduled, completed, canceled, no_show, confirmed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    external_id: Optional[str] = None  # ID from external scheduling system
    idempotency_key: Optional[str] = None  # For idempotent operations


class AvailabilitySlot(BaseModel):
    """Available time slot for scheduling."""

    start_time: datetime
    end_time: datetime
    provider_id: str
    location_id: str
    appointment_type: AppointmentType
    is_available: bool = True


class SchedulingRequest(BaseModel):
    """Request for scheduling an appointment."""

    patient_name: str
    patient_phone: str
    preferred_date: Optional[datetime] = None
    preferred_time: Optional[str] = None  # e.g., "morning", "afternoon", "evening"
    appointment_type: AppointmentType
    reason: Optional[str] = None
    new_patient: bool = False


class SchedulingResult(BaseModel):
    """Result of a scheduling operation."""

    success: bool
    appointment: Optional[Appointment] = None
    error_message: Optional[str] = None
    alternative_slots: list[AvailabilitySlot] = Field(default_factory=list)


class StaffEscalation(BaseModel):
    """Staff escalation request."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reason: str
    caller_name: str
    caller_phone: str
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"  # pending, contacted, completed
    staff_member: Optional[str] = None