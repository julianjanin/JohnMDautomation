"""Tests for the John Li ENT scheduling service."""

import pytest
from datetime import datetime, timedelta

from ..models import (
    Appointment,
    AppointmentType,
    AvailabilitySlot,
    CallDisposition,
    CallIntent,
    SchedulingResult,
)
from ..scheduler import MockSchedulerAdapter


@pytest.fixture
def scheduler():
    """Create a fresh mock scheduler for each test."""
    return MockSchedulerAdapter()


@pytest.mark.asyncio
async def test_list_appointment_types(scheduler):
    """Test that all appointment types are returned."""
    types = await scheduler.list_appointment_types()
    assert len(types) == 6
    assert AppointmentType.NEW_PATIENT_CONSULT in types
    assert AppointmentType.FOLLOW_UP in types
    assert AppointmentType.PROCEDURE_CONSULT in types


@pytest.mark.asyncio
async def test_find_availability_returns_slots(scheduler):
    """Test that availability slots are returned."""
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=7)

    slots = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=start_date,
        end_date=end_date,
    )

    assert len(slots) > 0
    assert all(isinstance(slot, AvailabilitySlot) for slot in slots)
    assert all(slot.is_available for slot in slots)


@pytest.mark.asyncio
async def test_create_appointment_success(scheduler):
    """Test successful appointment creation."""
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(minutes=30)

    result = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )

    assert result.success
    assert result.appointment is not None
    assert result.appointment.patient_name == "John Doe"
    assert result.appointment.appointment_type == AppointmentType.NEW_PATIENT_CONSULT


@pytest.mark.asyncio
async def test_create_appointment_double_booking_prevented(scheduler):
    """Test that double booking is prevented."""
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(minutes=30)

    # Create first appointment
    result1 = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )
    assert result1.success

    # Try to create second appointment at same time
    result2 = await scheduler.create_appointment(
        patient_name="Jane Smith",
        patient_phone="+15559876543",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )
    assert not result2.success
    assert "no longer available" in result2.error_message.lower()


@pytest.mark.asyncio
async def test_reschedule_appointment_success(scheduler):
    """Test successful appointment rescheduling."""
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(minutes=30)

    # Create appointment
    create_result = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )
    appointment_id = create_result.appointment.id

    # Reschedule
    new_start = datetime.utcnow() + timedelta(days=2)
    new_end = new_start + timedelta(minutes=30)

    result = await scheduler.reschedule_appointment(
        appointment_id=appointment_id,
        new_start_time=new_start,
        new_end_time=new_end,
    )

    assert result.success
    assert result.appointment.start_time == new_start


@pytest.mark.asyncio
async def test_cancel_appointment_success(scheduler):
    """Test successful appointment cancellation."""
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(minutes=30)

    # Create appointment
    create_result = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )
    appointment_id = create_result.appointment.id

    # Cancel
    result = await scheduler.cancel_appointment(appointment_id)

    assert result.success
    assert result.appointment.status == "canceled"


@pytest.mark.asyncio
async def test_confirm_appointment_success(scheduler):
    """Test successful appointment confirmation."""
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(minutes=30)

    # Create appointment
    create_result = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )
    appointment_id = create_result.appointment.id

    # Confirm
    result = await scheduler.confirm_appointment(appointment_id)

    assert result.success
    assert result.appointment.status == "confirmed"


@pytest.mark.asyncio
async def test_get_appointment_found(scheduler):
    """Test getting an existing appointment."""
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(minutes=30)

    # Create appointment
    create_result = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )
    appointment_id = create_result.appointment.id

    # Get appointment
    appointment = await scheduler.get_appointment(appointment_id)

    assert appointment is not None
    assert appointment.id == appointment_id
    assert appointment.patient_name == "John Doe"


@pytest.mark.asyncio
async def test_get_appointment_not_found(scheduler):
    """Test getting a non-existent appointment."""
    appointment = await scheduler.get_appointment("non-existent-id")
    assert appointment is None


@pytest.mark.asyncio
async def test_lookup_patient_by_phone_not_found(scheduler):
    """Test patient lookup when patient is not found."""
    patient = await scheduler.lookup_patient_by_phone("+15551234567")
    assert patient is None


@pytest.mark.asyncio
async def test_cancel_nonexistent_appointment(scheduler):
    """Test canceling a non-existent appointment."""
    result = await scheduler.cancel_appointment("non-existent-id")
    assert not result.success
    assert "not found" in result.error_message.lower()


@pytest.mark.asyncio
async def test_reschedule_nonexistent_appointment(scheduler):
    """Test rescheduling a non-existent appointment."""
    new_start = datetime.utcnow() + timedelta(days=2)
    new_end = new_start + timedelta(minutes=30)

    result = await scheduler.reschedule_appointment(
        appointment_id="non-existent-id",
        new_start_time=new_start,
        new_end_time=new_end,
    )
    assert not result.success
    assert "not found" in result.error_message.lower()


@pytest.mark.asyncio
async def test_confirm_canceled_appointment(scheduler):
    """Test confirming a canceled appointment."""
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(minutes=30)

    # Create and cancel appointment
    create_result = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )
    appointment_id = create_result.appointment.id

    await scheduler.cancel_appointment(appointment_id)

    # Try to confirm
    result = await scheduler.confirm_appointment(appointment_id)
    assert not result.success
    assert "canceled" in result.error_message.lower()


@pytest.mark.asyncio
async def test_double_booking_prevention_on_reschedule(scheduler):
    """Test that rescheduling to an occupied slot is prevented."""
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(minutes=30)

    # Create first appointment
    result1 = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )
    appointment_id = result1.appointment.id

    # Create second appointment
    start_time2 = datetime.utcnow() + timedelta(days=2)
    end_time2 = start_time2 + timedelta(minutes=30)

    result2 = await scheduler.create_appointment(
        patient_name="Jane Smith",
        patient_phone="+15559876543",
        appointment_type=AppointmentType.FOLLOW_UP,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time2,
        end_time=end_time2,
    )
    appointment_id2 = result2.appointment.id

    # Try to reschedule first appointment to second appointment's time
    result = await scheduler.reschedule_appointment(
        appointment_id=appointment_id,
        new_start_time=start_time2,
        new_end_time=end_time2,
    )
    assert not result.success
    assert "no longer available" in result.error_message.lower()


@pytest.mark.asyncio
async def test_mock_scheduler_clear_appointments(scheduler):
    """Test clearing all appointments."""
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(minutes=30)

    # Create appointment
    await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )

    # Clear appointments
    scheduler.clear_appointments()

    # Verify appointment is gone
    appointment = await scheduler.get_appointment(
        list(scheduler._appointments.keys())[0] if scheduler._appointments else "test"
    )
    assert len(scheduler._appointments) == 0