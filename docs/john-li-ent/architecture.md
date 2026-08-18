# John Li, MD ENT Call & Scheduling Automation - Architecture

This document describes the system architecture for the John Li ENT receptionist automation built on Dograh.

## Overview

The John Li ENT automation is a voice AI system that handles inbound calls for appointment scheduling, office information, and patient inquiries. It is built on the Dograh voice AI platform and extends it with ENT-specific functionality.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    John Li ENT Automation                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Inbound   │    │   Outbound  │    │   Tools     │         │
│  │   Call      │    │   Call      │    │             │         │
│  │   Flow      │    │   Flow      │    │             │         │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘         │
│         │                  │                  │                │
│         └──────────────────┼──────────────────┘                │
│                            │                                     │
│                   ┌───────▼───────┐                             │
│                   │  Voice Agent  │                             │
│                   │   (Dograh)    │                             │
│                   └───────┬───────┘                             │
│                           │                                     │
│                   ┌───────▼───────┐                             │
│                   │  Scheduling   │                             │
│                   │   Service     │                             │
│                   │  (John Li)    │                             │
│                   └───────┬───────┘                             │
│                           │                                     │
│                   ┌───────▼───────┐                             │
│                   │  Scheduler    │                             │
│                   │  Adapter      │                             │
│                   │ (Mock/Real)   │                             │
│                   └───────────────┘                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Dograh Voice Platform (Base)

The foundation is the Dograh voice AI platform, which provides:

- **FastAPI Backend** - REST API for workflow management, telephony, and tools
- **Next.js Frontend** - Visual workflow builder and dashboard
- **PostgreSQL Database** - Persistent storage for workflows, runs, and data
- **Redis** - Background job queue and caching
- **Pipecat Pipeline** - Voice streaming and conversation orchestration
- **Telephony Integration** - Twilio, Telnyx, Plivo, Vonage, etc.

### 2. John Li Scheduling Service

Custom scheduling functionality built on top of Dograh:

- **Domain Models** (`api/services/scheduling/models.py`)
  - `Appointment` - Appointment entity
  - `AppointmentType` - Types of ENT appointments
  - `AvailabilitySlot` - Available time slots
  - `CallIntent` - Call intent classification
  - `CallDisposition` - Call outcome tracking

- **Scheduler Abstraction** (`api/services/scheduling/scheduler.py`)
  - `SchedulerAdapter` - Abstract interface for scheduling operations
  - `MockSchedulerAdapter` - In-memory implementation for testing

- **Tools** (`api/services/scheduling/tools.py`)
  - `find_availability` - Find available appointment slots
  - `book_appointment` - Create a new appointment
  - `reschedule_appointment` - Change appointment time
  - `cancel_appointment` - Cancel an appointment
  - `confirm_appointment` - Confirm an appointment
  - `lookup_patient` - Check if patient exists
  - `get_appointment` - Retrieve appointment details
  - `get_office_info` - Get office hours, address, phone

### 3. Voice Agent Configuration

The voice agent is configured through Dograh's workflow system:

- **Persona** - Receptionist persona for Dr. Li's practice
- **Greeting** - Configurable placeholder greeting
- **Conversation Flow** - Intent-based routing
- **Tools** - Scheduling tools exposed to the agent
- **Escalation** - Human transfer for clinical questions

## Inbound Call Flow

```
Call Received
     │
     ▼
┌─────────────────┐
│   Greeting      │
│   (Configurable)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Identify      │
│   Reason for    │
│   Call          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Intent        │
│   Classification│
└────────┬────────┘
         │
    ┌────┴────┬─────────────┬─────────────┬─────────────┐
    │         │             │             │             │
    ▼         ▼             ▼             ▼             ▼
┌───────┐ ┌───────┐   ┌───────────┐ ┌───────────┐ ┌───────────┐
│NEW_APPT│ │CONFIRM│   │RESCHEDULE │ │CANCEL     │ │CLINICAL   │
│       │ │APPT   │   │APPT       │ │APPT       │ │QUESTION   │
└────┬──┘ └───────┘   └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
     │                     │             │             │
     ▼                     ▼             ▼             ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Collect       │ │   Verify        │ │   Verify        │
│   Scheduling    │ │   Appointment   │ │   Appointment   │
│   Info          │ │   Details       │ │   Details       │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Find          │ │   Confirm       │ │   Reschedule/   │
│   Availability  │ │   Appointment   │ │   Cancel        │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Offer Slots   │ │   Confirm       │ │   Confirm       │
│   to Caller     │ │   with Caller   │ │   with Caller   │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Book          │ │   Update        │ │   Update        │
│   Appointment   │ │   Status        │ │   Status        │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Return        │ │   Return        │ │   Return        │
│   Confirmation  │ │   Confirmation  │ │   Confirmation  │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Call          │
                    │   Disposition   │
                    └─────────────────┘
```

## Outbound Call Flow (Future)

```
Scheduled Appointment
         │
         ▼
┌─────────────────┐
│   Initiate      │
│   Outbound Call │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Verify        │
│   Correct Person│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Remind        │
│   of Appointment│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Offer Options │
│   - Confirm     │
│   - Reschedule  │
│   - Cancel      │
│   - Speak with  │
│     Staff       │
└────────┬────────┘
         │
    ┌────┴────┬─────────────┬─────────────┐
    │         │             │             │
    ▼         ▼             ▼             ▼
┌───────┐ ┌───────┐   ┌───────────┐ ┌───────────┐
│CONFIRM│ │RESCHED│   │CANCEL     │ │TRANSFER   │
│       │ │ULE    │   │           │ │TO STAFF   │
└────┬──┘ └───────┘   └───────────┘ └───────────┘
     │                                     │
     ▼                                     ▼
┌─────────────────┐              ┌─────────────────┐
│   Update        │              │   Create        │
│   Appointment   │              │   Escalation    │
│   Status        │              │   Request       │
└─────────────────┘              └─────────────────┘
```

## Intent Routing Model

The system uses a generic intent-routing model with the following categories:

| Intent | Description | Actions |
|--------|-------------|---------|
| NEW_APPOINTMENT | Caller wants to schedule a new appointment | Collect info, find slots, book |
| CONFIRM_APPOINTMENT | Caller wants to confirm an existing appointment | Verify details, confirm |
| RESCHEDULE_APPOINTMENT | Caller wants to change appointment time | Find new slots, reschedule |
| CANCEL_APPOINTMENT | Caller wants to cancel an appointment | Verify, cancel |
| OFFICE_INFORMATION | Caller asking about office hours, location | Provide info |
| LEAVE_MESSAGE | Caller wants to leave a message | Capture message |
| CLINICAL_QUESTION | Caller asking medical questions | Escalate to staff |
| HUMAN_REQUEST | Caller explicitly requesting staff | Transfer |
| OTHER | Unrecognized request | Clarify or escalate |
| EMERGENCY_OR_URGENT_ESCALATION | Urgent medical concern | Immediate escalation |

## Privacy / Healthcare Safety Boundary

This system is designed as a **scheduling and office automation assistant**, NOT a medical diagnostic agent.

### What the AI CAN do:
- Schedule appointments
- Confirm/reschedule/cancel appointments
- Provide office information
- Take messages
- Transfer to staff

### What the AI CANNOT do:
- Diagnose patients
- Recommend treatment
- Interpret symptoms clinically
- Alter medications
- Make medical decisions
- Determine medical eligibility

### Clinical Questions:
All clinical questions are escalated to staff immediately. The AI captures minimal necessary information and transfers the call.

## Data Flow

```
Caller ──► Telephony Provider (Twilio/Telnyx/etc.)
               │
               ▼
         Dograh Inbound Router
               │
               ▼
         Voice Agent (Pipecat)
               │
               ▼
         LLM (Conversation)
               │
               ▼
         Scheduling Tools
               │
               ▼
         Scheduler Adapter
               │
               ▼
         [Mock Scheduler | Real EHR/PM System]
               │
               ▼
         Database (PostgreSQL)
               │
               ▼
         Call Disposition
```

## Configuration

Practice-specific configuration is stored in:
- `api/services/scheduling/tools.py` - Office info placeholders
- `docs/john-li-ent/practice-configuration.md` - Configuration requirements

## Testing

Run tests with:
```bash
python -m pytest api/services/scheduling/tests/ -v
```

## Future Production Integration Points

1. **Real Scheduler Adapter** - Replace MockSchedulerAdapter with EHR/PM integration
2. **Database Persistence** - Store appointments in PostgreSQL
3. **Webhook Integration** - Sync with external scheduling system
4. **Patient Portal Integration** - Verify patient identity
5. **Insurance Verification** - Check eligibility before booking
6. **Reminder System** - Automated outbound reminders