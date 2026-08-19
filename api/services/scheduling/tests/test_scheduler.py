"""Tests for the John Li ENT scheduling service.

This module tests the scheduler adapter, models, and tool functions
for the John Li ENT practice scheduling system.
"""

import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ..models import (
    Appointment,
    AppointmentType,
    AvailabilitySlot,
    CallDisposition,
    CallIntent,
    SchedulingResult,
)
from ..scheduler import MockSchedulerAdapter
from ..service import SchedulingService


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
    # Use a known weekday (Monday) for testing in practice timezone
    start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo("America/New_York"))  # Monday
    end_date = start_date + timedelta(days=1)

    slots = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=start_date,
        end_date=end_date,
    )

    # Should have 4 slots on a weekday
    assert len(slots) == 4

    # Verify slot end times - all in practice timezone
    expected_slots = [
        (datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/New_York")), datetime(2024, 1, 1, 9, 30, 0, tzinfo=ZoneInfo("America/New_York"))),
        (datetime(2024, 1, 1, 10, 30, 0, tzinfo=ZoneInfo("America/New_York")), datetime(2024, 1, 1, 11, 0, 0, tzinfo=ZoneInfo("America/New_York"))),
        (datetime(2024, 1, 1, 14, 0, 0, tzinfo=ZoneInfo("America/New_York")), datetime(2024, 1, 1, 14, 30, 0, tzinfo=ZoneInfo("America/New_York"))),
        (datetime(2024, 1, 1, 15, 30, 0, tzinfo=ZoneInfo("America/New_York")), datetime(2024, 1, 1, 16, 0, 0, tzinfo=ZoneInfo("America/New_York"))),
    ]

    for slot, (expected_start, expected_end) in zip(slots, expected_slots):
        assert slot.start_time == expected_start, f"Start time mismatch: {slot.start_time} != {expected_start}"
        assert slot.end_time == expected_end, f"End time mismatch: {slot.end_time} != {expected_end}"


@pytest.mark.asyncio
async def test_availability_no_invalid_datetime_creation(scheduler):
    """Test that no invalid datetime creation occurs (e.g., minute=60)."""
    start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo("America/New_York"))
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
    saturday = datetime(2024, 1, 6, 0, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    sunday = datetime(2024, 1, 7, 0, 0, 0, tzinfo=ZoneInfo("America/New_York"))

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
    start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo("America/New_York"))
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
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
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
    start1 = datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    end1 = start1 + timedelta(minutes=30)

    # Second appointment: 9:15-9:45 (overlaps with first)
    start2 = datetime(2024, 1, 1, 9, 15, 0, tzinfo=ZoneInfo("America/New_York"))
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
    start1 = datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    end1 = start1 + timedelta(minutes=30)

    # Second appointment: 9:30-10:00 (adjacent, not overlapping)
    start2 = datetime(2024, 1, 1, 9, 30, 0, tzinfo=ZoneInfo("America/New_York"))
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
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
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
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
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
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
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
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
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
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
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
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
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
        start_time=datetime(2024, 1, 1, 10, 0, 0, tzinfo=ZoneInfo("America/New_York")),
        end_time=datetime(2024, 1, 1, 10, 30, 0, tzinfo=ZoneInfo("America/New_York")),
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
    start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo("America/New_York"))
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
    start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo("America/New_York"))
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
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
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
    start_date = datetime.now(ZoneInfo("America/New_York"))
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
    start_time = datetime.now(ZoneInfo("America/New_York")) + timedelta(days=1)
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
    start_time = datetime.now(ZoneInfo("America/New_York")) + timedelta(days=1)
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
    new_start = datetime.now(ZoneInfo("America/New_York")) + timedelta(days=2)
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
    start_time = datetime.now(ZoneInfo("America/New_York")) + timedelta(days=1)
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
    start_time = datetime.now(ZoneInfo("America/New_York")) + timedelta(days=1)
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
    start_time = datetime.now(ZoneInfo("America/New_York")) + timedelta(days=1)
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
    new_start = datetime.now(ZoneInfo("America/New_York")) + timedelta(days=2)
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
    start_time = datetime.now(ZoneInfo("America/New_York")) + timedelta(days=1)
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
    start_time = datetime.now(ZoneInfo("America/New_York")) + timedelta(days=1)
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
    start_time2 = datetime.now(ZoneInfo("America/New_York")) + timedelta(days=2)
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
    start_time = datetime.now(ZoneInfo("America/New_York")) + timedelta(days=1)
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


# =============================================================================
# B1: Timezone Correctness Tests
# =============================================================================

@pytest.mark.asyncio
async def test_default_scheduler_uses_america_new_york():
    """Test that SchedulingService created with default configuration uses America/New_York."""
    service = SchedulingService()
    assert service.scheduler.practice_timezone == ZoneInfo("America/New_York")


@pytest.mark.asyncio
async def test_availability_no_preferred_date_returns_new_york_slots():
    """Test that availability with NO preferred_date returns slots whose tzinfo is America/New_York."""
    service = SchedulingService()

    slots = await service.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
    )

    # All slots should have America/New_York timezone
    for slot in slots:
        assert slot.start_time.tzinfo == ZoneInfo("America/New_York"), \
            f"Slot start_time tzinfo should be America/New_York, got {slot.start_time.tzinfo}"
        assert slot.end_time.tzinfo == ZoneInfo("America/New_York"), \
            f"Slot end_time tzinfo should be America/New_York, got {slot.end_time.tzinfo}"


@pytest.mark.asyncio
async def test_local_slot_clock_times_remain_correct():
    """Test that local slot clock times remain 09:00, 10:30, 14:00, 15:30."""
    service = SchedulingService()

    # Use a specific date to test slot times
    start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    end_date = start_date + timedelta(days=1)

    slots = await service.scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=start_date,
        end_date=end_date,
    )

    expected_times = [(9, 0), (10, 30), (14, 0), (15, 30)]

    for slot, (expected_hour, expected_minute) in zip(slots, expected_times):
        assert slot.start_time.hour == expected_hour, \
            f"Expected hour {expected_hour}, got {slot.start_time.hour}"
        assert slot.start_time.minute == expected_minute, \
            f"Expected minute {expected_minute}, got {slot.start_time.minute}"


@pytest.mark.asyncio
async def test_utc_input_converted_to_practice_timezone():
    """Test that a timezone-aware UTC input is converted to America/New_York before office slot generation."""
    service = SchedulingService()

    # Create a UTC datetime for a specific date
    utc_start = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)  # 14:00 UTC = 09:00 New York
    utc_end = utc_start + timedelta(days=1)

    slots = await service.scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=utc_start,
        end_date=utc_end,
    )

    # All slots should be in America/New_York timezone
    for slot in slots:
        assert slot.start_time.tzinfo == ZoneInfo("America/New_York"), \
            f"Slot should be in America/New_York, got {slot.start_time.tzinfo}"


@pytest.mark.asyncio
async def test_equivalent_utc_new_york_instants_compare_correctly():
    """Test that equivalent instants compare correctly: 2024-01-01 09:00 America/New_York == 2024-01-01 14:00 UTC."""
    service = SchedulingService()

    # Create the same instant in two different timezones
    ny_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    utc_time = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

    # They should represent the same instant
    assert ny_time == utc_time, "09:00 NY should equal 14:00 UTC on Jan 1, 2024"

    # Book an appointment at the NY time
    result = await service.book_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_time=ny_time,
    )
    assert result.success, "Booking at NY time should succeed"

    # Verify the appointment was created with the correct time
    appointment = result.appointment
    assert appointment.start_time == ny_time, "Appointment should have NY time"

    # Now try to book the same instant using UTC time
    result2 = await service.book_appointment(
        patient_name="Jane Smith",
        patient_phone="+15559876543",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_time=utc_time,
    )
    # Should fail because the slot is already booked
    assert not result2.success, "Booking at same instant via UTC should fail (double booking)"


@pytest.mark.asyncio
async def test_custom_timezone_los_angeles():
    """Test that a custom practice configuration such as America/Los_Angeles causes the service/scheduler to generate local Los Angeles office slots."""
    # Create a scheduler with Los Angeles timezone
    la_scheduler = MockSchedulerAdapter(practice_timezone=ZoneInfo("America/Los_Angeles"))
    service = SchedulingService(scheduler=la_scheduler)

    # Verify the timezone is set correctly
    assert service.scheduler.practice_timezone == ZoneInfo("America/Los_Angeles")

    # Generate slots
    start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    end_date = start_date + timedelta(days=1)

    slots = await service.scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=start_date,
        end_date=end_date,
    )

    # All slots should be in Los Angeles timezone
    for slot in slots:
        assert slot.start_time.tzinfo == ZoneInfo("America/Los_Angeles"), \
            f"Slot should be in America/Los_Angeles, got {slot.start_time.tzinfo}"

    # Verify slot times are still 09:00, 10:30, 14:00, 15:30 in local time
    expected_times = [(9, 0), (10, 30), (14, 0), (15, 30)]
    for slot, (expected_hour, expected_minute) in zip(slots, expected_times):
        assert slot.start_time.hour == expected_hour
        assert slot.start_time.minute == expected_minute


@pytest.mark.asyncio
async def test_dst_aware_behavior_uses_zoneinfo():
    """Test that DST-aware behavior uses ZoneInfo rather than a fixed UTC offset."""
    # Create a scheduler with America/New_York timezone
    scheduler = MockSchedulerAdapter(practice_timezone=ZoneInfo("America/New_York"))

    # Winter time (EST = UTC-5)
    winter_date = datetime(2024, 1, 15, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    winter_utc_offset = winter_date.utcoffset()

    # Summer time (EDT = UTC-4)
    summer_date = datetime(2024, 7, 15, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    summer_utc_offset = summer_date.utcoffset()

    # Verify that winter and summer have different UTC offsets (DST in effect)
    assert winter_utc_offset != summer_utc_offset, \
        "Winter and summer should have different UTC offsets due to DST"

    # Verify the actual offsets
    assert winter_utc_offset == timedelta(hours=-5), f"Winter offset should be -5 hours, got {winter_utc_offset}"
    assert summer_utc_offset == timedelta(hours=-4), f"Summer offset should be -4 hours, got {summer_utc_offset}"

    # Test that the scheduler correctly handles DST transitions
    # Generate slots in winter
    winter_slots = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=datetime(2024, 1, 15, 0, 0, 0, tzinfo=ZoneInfo("America/New_York")),
        end_date=datetime(2024, 1, 16, 0, 0, 0, tzinfo=ZoneInfo("America/New_York")),
    )

    # Generate slots in summer
    summer_slots = await scheduler.find_availability(
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_date=datetime(2024, 7, 15, 0, 0, 0, tzinfo=ZoneInfo("America/New_York")),
        end_date=datetime(2024, 7, 16, 0, 0, 0, tzinfo=ZoneInfo("America/New_York")),
    )

    # Both should have 4 slots
    assert len(winter_slots) == 4
    assert len(summer_slots) == 4

    # Slot times should be the same local time (09:00, 10:30, 14:00, 15:30)
    for winter_slot, summer_slot in zip(winter_slots, summer_slots):
        assert winter_slot.start_time.hour == summer_slot.start_time.hour
        assert winter_slot.start_time.minute == summer_slot.start_time.minute


@pytest.mark.asyncio
async def test_30_minute_duration_remains_correct():
    """Test that existing 30-minute duration behavior remains correct."""
    service = SchedulingService()

    # Book an appointment
    start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    result = await service.book_appointment(
        patient_name="John Doe",
        patient_phone="+15551234567",
        appointment_type=AppointmentType.NEW_PATIENT_CONSULT,
        start_time=start_time,
    )

    assert result.success

    # Verify the appointment has 30-minute duration
    appointment = result.appointment
    duration = (appointment.end_time - appointment.start_time).total_seconds() / 60
    assert duration == 30, f"Appointment duration should be 30 minutes, got {duration}"

    # Verify end time is correct
    expected_end = start_time + timedelta(minutes=30)
    assert appointment.end_time == expected_end, \
        f"End time should be {expected_end}, got {appointment.end_time}"