# John Li ENT Scheduling Service

This module provides scheduling functionality for John Li, MD's ENT practice.

## Architecture

```
scheduling/
├── __init__.py           # Module exports
├── models.py             # Domain models (Appointment, Provider, Location, etc.)
├── scheduler.py          # SchedulerAdapter interface and MockSchedulerAdapter
├── tools.py              # Dograh tools for scheduling operations
├── service.py            # Scheduling service layer
└── tests/                # Unit tests
```

## Key Components

### SchedulerAdapter

Abstract base class defining the contract for scheduling operations:
- `list_appointment_types()` - List available appointment types
- `find_availability()` - Find available time slots
- `create_appointment()` - Create a new appointment
- `reschedule_appointment()` - Reschedule an existing appointment
- `cancel_appointment()` - Cancel an appointment
- `confirm_appointment()` - Confirm an appointment
- `lookup_patient_by_phone()` - Look up patient by phone number

### MockSchedulerAdapter

Implementation for testing and local development:
- Uses in-memory storage
- Generates deterministic synthetic data
- No external dependencies

### Domain Models

- `Appointment` - Appointment entity
- `AppointmentType` - Types of appointments (NEW_PATIENT_CONSULT, FOLLOW_UP, etc.)
- `AvailabilitySlot` - Available time slot
- `SchedulingRequest` - Request for scheduling
- `SchedulingResult` - Result of scheduling operation
- `CallIntent` - Call intent classification
- `CallDisposition` - Call disposition values

## Integration with Dograh

The scheduling service integrates with Dograh through:

1. **Tools** - Custom HTTP tools exposed to the voice workflow
2. **Workflow configuration** - Practice-specific configuration
3. **Voice agent instructions** - Conversation policy

## Testing

Run tests with:
```bash
python -m pytest api/services/scheduling/tests/ -v
```

## Future Work

- Implement real scheduler adapter for EHR/practice management system
- Add database persistence for appointments
- Add webhook integration for external system sync