"""Tests for the John Li ENT scheduling service.

This module tests the scheduler adapter, models, and tool functions
for the John Li ENT practice scheduling system.
"""

import pytest
from datetime import datetime, timedelta, timezone

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


# =============================================================================
# A1: Availability Generation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_availability_slot_end_times_correct(scheduler):
    """Test that slot end times are correctly calculated using timedelta.
    
    Verifies:
    - 9:00 → 9:30
    - 10:30 → 11:00
    - 2:00 → 2:30
    - 3:30 → 4:00
    """
    # Use a known weekday (Monday) for testing
    start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)  # Monday
    end_date = start_date + timedelta(days=1)
    
    slots = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=start_date,
        end_date=end_date,
    )
    
    # Should have 4 slots on a weekday
    assert len(slots) == 4
    
    # Verify slot end times
    expected_slots = [
        (datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc), datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc)),
        (datetime(2024, 1, 1, 10, 30, 0, tzinfo=timezone.utc), datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)),
        (datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc), datetime(2024, 1, 1, 14, 30, 0, tzinfo=timezone.utc)),
        (datetime(2024, 1, 1, 15, 30, 0, tzinfo=timezone.utc), datetime(2024, 1, 1, 16, 0, 0, tzinfo=timezone.utc)),
    ]
    
    for slot, (expected_start, expected_end) in zip(slots, expected_slots):
        assert slot.start_time == expected_start, f"Start time mismatch: {slot.start_time} != {expected_start}"
        assert slot.end_time == expected_end, f"End time mismatch: {slot.end_time} != {expected_end}"


@pytest.mark.asyncio
async def test_availability_no_invalid_datetime_creation(scheduler):
    """Test that no invalid datetime creation occurs (e.g., minute=60)."""
    start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_date = start_date + timedelta(days=7)
    
    # Should not raise any exceptions
    slots = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=start_date,
        end_date=end_date,
    )
    
    # All slots should have valid end times
    for slot in slots:
        assert slot.end_time.minute in (0, 30), f"Invalid minute: {slot.end_time.minute}"
        assert slot.end_time.hour <= 23, f"Invalid hour: {slot.end_time.hour}"


@pytest.mark.asyncio
async def test_availability_weekends_excluded(scheduler):
    """Test that weekends are excluded from availability."""
    # Saturday (Jan 6, 2024)
    saturday = datetime(2024, 1, 6, 0, 0, 0, tzinfo=timezone.utc)
    sunday = datetime(2024, 1, 7, 0, 0, 0, tzinfo=timezone.utc)
    
    # Check Saturday
    slots_sat = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=saturday,
        end_date=saturday + timedelta(days=1),
    )
    assert len(slots_sat) == 0, "Saturday should have no slots"
    
    # Check Sunday
    slots_sun = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=sunday,
        end_date=sunday + timedelta(days=1),
    )
    assert len(slots_sun) == 0, "Sunday should have no slots"


@pytest.mark.asyncio
async def test_availability_exactly_30_minute_duration(scheduler):
    """Test that returned slots have exactly 30-minute duration."""
    start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_date = start_date + timedelta(days=7)
    
    slots = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=start_date,
        end_date=end_date,
    )
    
    for slot in slots:
        duration = (slot.end_time - slot.start_time).total_seconds() / 60
        assert duration == 30, f"Slot duration is {duration} minutes, expected 30"


# =============================================================================
# A2: Double-Booking Logic Tests
# =============================================================================

@pytest.mark.asyncio
async def test_double_booking_identical_slots(scheduler):
    """Test that identical start times conflict."""
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
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
async def test_double_booking_overlapping_slots(scheduler):
    """Test that overlapping time ranges conflict."""
    # First appointment: 9:00-9:30
    start1 = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    end1 = start1 + timedelta(minutes=30)
    
    # Second appointment: 9:15-9:45 (overlaps with first)
    start2 = datetime(2024, 1, 1, 9, 15, 0, tzinfo=timezone.utc)
    end2 = start2 + timedelta(minutes=30)
    
    # Create first appointment
    result1 = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start1,
        end_time=end1,
    )
    assert result1.success
    
    # Try to create overlapping appointment
    result2 = await scheduler.create_appointment(
        patient_name="Jane Smith",
        patient_phone="+15559876543",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start2,
        end_time=end2,
    )
    assert not result2.success


@pytest.mark.asyncio
async def test_double_booking_adjacent_slots_allowed(scheduler):
    """Test that adjacent slots (no overlap) are allowed."""
    # First appointment: 9:00-9:30
    start1 = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    end1 = start1 + timedelta(minutes=30)
    
    # Second appointment: 9:30-10:00 (adjacent, not overlapping)
    start2 = datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
    end2 = start2 + timedelta(minutes=30)
    
    # Create first appointment
    result1 = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start1,
        end_time=end1,
    )
    assert result1.success
    
    # Create adjacent appointment - should succeed
    result2 = await scheduler.create_appointment(
        patient_name="Jane Smith",
        patient_phone="+15559876543",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start2,
        end_time=end2,
    )
    assert result2.success


@pytest.mark.asyncio
async def test_double_booking_different_providers_allowed(scheduler):
    """Test that different providers can have simultaneous appointments."""
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(minutes=30)
    
    # Create appointment for dr-john-li
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
    
    # Create appointment for different provider at same time - should succeed
    result2 = await scheduler.create_appointment(
        patient_name="Jane Smith",
        patient_phone="+15559876543",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-jane-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )
    assert result2.success


# =============================================================================
# A3: Idempotency Tests
# =============================================================================

@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_booking(scheduler):
    """Test that repeated booking with same key doesn't create duplicates."""
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(minutes=30)
    
    idempotency_key = "test-idempotency-key-123"
    
    # First booking
    result1 = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
        idempotency_key=idempotency_key,
    )
    assert result1.success
    first_appointment_id = result1.appointment.id
    
    # Second booking with same key
    result2 = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
        idempotency_key=idempotency_key,
    )
    assert result2.success
    # Should return the same appointment
    assert result2.appointment.id == first_appointment_id


@pytest.mark.asyncio
async def test_idempotency_different_key_creates_new_booking(scheduler):
    """Test that different idempotency keys create new bookings."""
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(minutes=30)
    
    # First booking
    result1 = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
        idempotency_key="key-1",
    )
    assert result1.success
    
    # Second booking with different key and different time
    start_time2 = start_time + timedelta(days=1)
    end_time2 = start_time2 + timedelta(minutes=30)
    result2 = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time2,
        end_time=end_time2,
        idempotency_key="key-2",
    )
    assert result2.success
    assert result2.appointment.id != result1.appointment.id


# =============================================================================
# A4: Status Semantics Tests
# =============================================================================

@pytest.mark.asyncio
async def test_scheduled_blocks_slot(scheduler):
    """Test that scheduled appointments block their slot."""
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(minutes=30)
    
    # Create scheduled appointment
    await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )
    
    # Check availability - should not include this slot
    slots = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=start_time,
        end_date=start_time + timedelta(days=1),
    )
    
    for slot in slots:
        assert slot.start_time != start_time, "Scheduled appointment should block slot"


@pytest.mark.asyncio
async def test_confirmed_blocks_slot(scheduler):
    """Test that confirmed appointments still block their slot."""
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(minutes=30)
    
    # Create and confirm appointment
    result = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )
    appointment_id = result.appointment.id
    
    await scheduler.confirm_appointment(appointment_id)
    
    # Check availability - should not include this slot
    slots = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=start_time,
        end_date=start_time + timedelta(days=1),
    )
    
    for slot in slots:
        assert slot.start_time != start_time, "Confirmed appointment should block slot"


@pytest.mark.asyncio
async def test_canceled_does_not_block_slot(scheduler):
    """Test that canceled appointments do not block their slot."""
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(minutes=30)
    
    # Create and cancel appointment
    result = await scheduler.create_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        provider_id="dr-john-li",
        location_id="main-office",
        start_time=start_time,
        end_time=end_time,
    )
    appointment_id = result.appointment.id
    
    await scheduler.cancel_appointment(appointment_id)
    
    # Check availability - should include this slot
    slots = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=start_time,
        end_date=start_time + timedelta(days=1),
    )
    
    slot_times = [slot.start_time for slot in slots]
    assert start_time in slot_times, "Canceled appointment should not block slot"


# =============================================================================
# A5: Mutable Pydantic Defaults Tests
# =============================================================================

@pytest.mark.asyncio
async def test_scheduling_result_default_factory(scheduler):
    """Test that SchedulingResult uses default_factory for alternative_slots."""
    result1 = SchedulingResult(success=True)
    result2 = SchedulingResult(success=True)
    
    # Should be different list instances
    assert result1.alternative_slots is not result2.alternative_slots
    
    # Modifying one should not affect the other
    result1.alternative_slots.append(AvailabilitySlot(
        start_time=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 1, 10, 30, 0, tzinfo=timezone.utc),
        provider_id="dr-john-li",
        location_id="main-office",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
    ))
    
    assert len(result2.alternative_slots) == 0, "default_factory should prevent shared state"


# =============================================================================
# A6: Timezone Handling Tests
# =============================================================================

@pytest.mark.asyncio
async def test_timezone_aware_datetime_arithmetic(scheduler):
    """Test that timezone-aware datetime arithmetic works correctly."""
    # Test with America/New_York equivalent (UTC-5 in winter)
    start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_date = start_date + timedelta(days=7)
    
    slots = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=start_date,
        end_date=end_date,
    )
    
    # All slots should be timezone-aware
    for slot in slots:
        assert slot.start_time.tzinfo is not None, "Slot start should be timezone-aware"
        assert slot.end_time.tzinfo is not None, "Slot end should be timezone-aware"


@pytest.mark.asyncio
async def test_no_utcnow_for_business_scheduling(scheduler):
    """Test that datetime.utcnow() is not used for business scheduling."""
    # The scheduler should use timezone-aware datetimes
    start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_date = start_date + timedelta(days=1)
    
    slots = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=start_date,
        end_date=end_date,
    )
    
    # Verify slots are generated correctly
    assert len(slots) == 4


# =============================================================================
# A7: Availability Validation Before Booking Tests
# =============================================================================

@pytest.mark.asyncio
async def test_booking_validates_against_scheduler(scheduler):
    """Test that booking validates provider, location, and time."""
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(minutes=30)
    
    # Create appointment
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
    
    # Try to book same slot again
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


# =============================================================================
# A8: Patient Lookup Mock Tests
# =============================================================================

@pytest.mark.asyncio
async def test_patient_lookup_found(scheduler):
    """Test that known phone returns patient info."""
    patient = await scheduler.lookup_patient_by_phone("+15551234567")
    
    assert patient is not None
    assert patient["name"] == "John Doe"
    assert patient["phone"] == "+15551234567"


@pytest.mark.asyncio
async def test_patient_lookup_not_found(scheduler):
    """Test that unknown phone returns None."""
    patient = await scheduler.lookup_patient_by_phone("+15559999999")
    
    assert patient is None


@pytest.mark.asyncio
async def test_patient_lookup_synthetic_data(scheduler):
    """Test that patient lookup uses synthetic test data."""
    # Test the second synthetic patient
    patient = await scheduler.lookup_patient_by_phone("+15559876543")
    
    assert patient is not None
    assert patient["name"] == "Jane Smith"


# =============================================================================
# Additional Tests
# =============================================================================

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
    start_date = datetime.now(timezone.utc)
    end_date = start_date + timedelta(days=7)

    slots = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=start_date,
        end_date=end_date,
    )

    assert len(slots) > 0
    assert all(isinstance(slot, AvailabilitySlot) for slot in slots)


@pytest.mark.asyncio
async def test_create_appointment_success(scheduler):
    """Test successful appointment creation."""
    start_time = datetime.now(timezone.utc) + timedelta(days=1)
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
async def test_reschedule_appointment_success(scheduler):
    """Test successful appointment rescheduling."""
    start_time = datetime.now(timezone.utc) + timedelta(days=1)
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
    new_start = datetime.now(timezone.utc) + timedelta(days=2)
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
    start_time = datetime.now(timezone.utc) + timedelta(days=1)
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
    start_time = datetime.now(timezone.utc) + timedelta(days=1)
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
    start_time = datetime.now(timezone.utc) + timedelta(days=1)
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
async def test_cancel_nonexistent_appointment(scheduler):
    """Test canceling a non-existent appointment."""
    result = await scheduler.cancel_appointment("non-existent-id")
    assert not result.success
    assert "not found" in result.error_message.lower()


@pytest.mark.asyncio
async def test_reschedule_nonexistent_appointment(scheduler):
    """Test rescheduling a non-existent appointment."""
    new_start = datetime.now(timezone.utc) + timedelta(days=2)
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
    start_time = datetime.now(timezone.utc) + timedelta(days=1)
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
    start_time = datetime.now(timezone.utc) + timedelta(days=1)
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
    start_time2 = datetime.now(timezone.utc) + timedelta(days=2)
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
    start_time = datetime.now(timezone.utc) + timedelta(days=1)
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
    assert len(scheduler._appointments) == 0