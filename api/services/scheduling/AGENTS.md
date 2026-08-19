# John Li ENT Scheduling Service

This module provides scheduling functionality for John Li, MD's ENT practice.

## Architecture

```
scheduling/
├── __init__.py           # Module exports
├── models.py             # Domain models (Appointment, Provider, Location, etc.)
├── scheduler.py          # SchedulerAdapter interface and MockSchedulerAdapter
├── service.py            # Service layer for business logic
├── practice_config.py    # Practice configuration
├── workflow.py           # Voice workflow configuration
├── tools.py              # Dograh tools for scheduling operations
├── routes.py             # HTTP API routes for scheduling
└── tests/                # Unit tests
```

## Key Components

### SchedulerAdapter

Abstract base class defining the contract for scheduling operations:
- `list_appointment_types()` - List available appointment types
- `find_availability()` - Find available time slots
- `get_appointment()` - Get an appointment by ID
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
- Supports timezone-aware datetime operations
- Implements proper interval overlap detection for double-booking prevention
- Provides idempotency key support for safe retries

### SchedulingService

Service layer that provides business logic for scheduling operations:
- Wraps the scheduler adapter
- Provides validation and error handling
- Manages provider/location defaults
- Handles availability validation before booking

### PracticeConfiguration

Configuration class for practice-specific values:
- Provider information
- Office hours and locations
- Appointment types and durations
- Transfer destinations
- Emergency messages
- Greeting messages

### JohnLiWorkflow

Voice workflow configuration for the John Li ENT receptionist:
- Greeting and emergency messages
- Office hours and provider info
- Clinical question detection
- Emergency statement detection
- Disposition mapping

### Domain Models

- `Appointment` - Appointment entity with status, timing, and patient info
- `AppointmentType` - Types of ENT appointments (NEW_PATIENT_CONSULT, FOLLOW_UP, etc.)
- `AvailabilitySlot` - Available time slot
- `SchedulingRequest` - Request for scheduling
- `SchedulingResult` - Result of scheduling operation
- `CallIntent` - Call intent classification
- `CallDisposition` - Call disposition values
- `StaffEscalation` - Staff escalation request

## Integration with Dograh

The scheduling service integrates with Dograh through:

1. **HTTP API Routes** (`api/routes/scheduling.py`) - REST endpoints for scheduling operations
2. **Tools** (`api/services/scheduling/tools.py`) - Tool definitions for Dograh workflows
3. **Service Layer** (`api/services/scheduling/service.py`) - Business logic layer
4. **Practice Configuration** (`api/services/scheduling/practice_config.py`) - Configurable practice values
5. **Voice Workflow** (`api/services/scheduling/workflow.py`) - Workflow configuration

## Tool Registration

Tools are registered via the `TOOLS` list in `tools.py`. Each tool includes:
- `name` - The function name used by the LLM
- `description` - Human-readable description
- `input_schema` - JSON schema for tool parameters
- `handler` - Async function that executes the tool

Available tools:
- `find_availability` - Find available appointment slots
- `book_appointment` - Create a new appointment
- `reschedule_appointment` - Change appointment time
- `cancel_appointment` - Cancel an appointment
- `confirm_appointment` - Confirm an appointment
- `lookup_patient` - Check if patient exists
- `get_appointment` - Retrieve appointment details
- `get_office_info` - Get office hours, address, phone

## HTTP API Endpoints

The scheduling service exposes the following HTTP endpoints:

- `GET /scheduling/appointment-types` - List all appointment types
- `GET /scheduling/availability` - Find available slots
- `POST /scheduling/book` - Book a new appointment
- `POST /scheduling/reschedule` - Reschedule an appointment
- `POST /scheduling/cancel` - Cancel an appointment
- `POST /scheduling/confirm` - Confirm an appointment
- `GET /scheduling/patient` - Look up a patient by phone
- `GET /scheduling/appointment/{id}` - Get appointment details
- `GET /scheduling/office-info` - Get office information
- `POST /scheduling/escalation` - Create a staff escalation

## Testing

Run tests with:
```bash
python -m pytest api/services/scheduling/tests/ -v
```

Or run standalone tests:
```bash
python api/test_scheduling_standalone.py
```

## Design Decisions

### Timezone Handling

The scheduler uses timezone-aware datetime objects. The `PRACTICE_TZ` constant
can be configured to the practice's local timezone (e.g., `America/New_York`).

### Double-Booking Prevention

Uses half-open interval semantics `[start, end)` for overlap detection:
- Two intervals overlap if `start1 < end2 AND start2 < end1`
- Considers provider, location, and time
- Active statuses: `scheduled`, `confirmed`
- Non-blocking status: `canceled`

### Idempotency

All state-changing operations support an optional `idempotency_key` parameter.
This allows safe retries of booking operations without creating duplicates.

### Patient Lookup

Returns synthetic patient data for testing:
- Known phones return patient info
- Unknown phones return None (indicating new patient)

### Availability Generation

Slots are generated using robust datetime arithmetic:
- 9:00 → 9:30
- 10:30 → 11:00
- 2:00 → 2:30
- 3:30 → 4:00
- Weekends excluded
- No invalid datetime creation (e.g., minute=60)

## Future Work

- Implement real scheduler adapter for EHR/practice management system
- Add database persistence for appointments
- Add webhook integration for external system sync
- Integrate with Dograh's native tool system for proper tool registration