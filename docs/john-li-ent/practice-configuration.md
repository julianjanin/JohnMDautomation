# John Li, MD ENT Practice Configuration

This document lists the information needed from Dr. Li to configure the ENT practice automation.

## Information Still Needed from Dr. Li

### Practice Information

- [ ] **Office Name** - The official name of the practice
- [ ] **Phone Number** - Main office phone number for the caller ID
- [ ] **Address** - Full mailing address for the practice
- [ ] **Website URL** - Practice website (if any)

### Office Hours

- [ ] **Monday** - Opening and closing times
- [ ] **Tuesday** - Opening and closing times
- [ ] **Wednesday** - Opening and closing times
- [ ] **Thursday** - Opening and closing times
- [ ] **Friday** - Opening and closing times
- [ ] **Saturday** - Open/Closed, and hours if open
- [ ] **Sunday** - Open/Closed, and hours if open

### Appointment Types

- [ ] **New Patient Consult** - Duration (e.g., 30 min, 60 min)
- [ ] **Follow-up Visit** - Duration
- [ ] **Procedure Consult** - Duration
- [ ] **Post-Op Follow-up** - Duration
- [ ] **Routine Checkup** - Duration
- [ ] **Emergency/Urgent** - Duration and handling

### Scheduling Rules

- [ ] **New Patient Requirements** - Any special requirements for new patients
- [ ] **Referral Requirements** - Do appointments require referrals?
- [ ] **Insurance Requirements** - Any insurance-related scheduling rules
- [ ] **Cancellation Policy** - Notice required for cancellations
- [ ] **Rescheduling Policy** - Any restrictions on rescheduling

### Provider Information

- [ ] **Provider Name** - Full name (e.g., "John Li, MD")
- [ ] **Specialty** - ENT / Otolaryngology
- [ ] **Provider ID** - Internal ID if applicable
- [ ] **Provider Photo** - For any customer-facing materials

### Staff Information

- [ ] **Receptionist Name(s)** - For transfer messages
- [ ] **Nurse Name(s)** - For clinical questions
- [ ] **Staff Phone Numbers** - Direct lines for transfers
- [ ] **After-hours Contact** - For emergency calls

### Emergency/Urgent Routing

- [ ] **Emergency Phone Number** - Direct line for emergencies
- [ ] **Urgent Care Hours** - When urgent care is available
- [ ] **Emergency Protocol** - How to handle emergency calls

### Reminder Policy

- [ ] **Reminder Cadence** - How many days before appointment
- [ ] **Reminder Method** - Phone call, text, email
- [ ] **Confirmation Required** - Must confirm before reminder

### Voicemail Policy

- [ ] **Voicemail Greeting** - What to say when leaving voicemail
- [ ] **Callback Timeframe** - When staff will call back
- [ ] **Voicemail Transcription** - Should messages be transcribed?

### Voice Persona

- [ ] **Preferred Voice Style** - Professional, warm, formal, etc.
- [ ] **Exact Greeting** - The opening line for calls
- [ ] **Tone Guidelines** - Any specific tone preferences
- [ ] **Disclosures** - Any required legal disclosures

### Integration Requirements

- [ ] **Scheduling System/EHR** - Name and API details
- [ ] **Patient Portal** - For patient verification
- [ ] **Insurance Verification** - Integration needed?
- [ ] **Billing System** - Any integration requirements

### Telephony Configuration

- [ ] **Primary Phone Number** - For inbound calls
- [ ] **Secondary Numbers** - Additional lines
- [ ] **Call Transfer Numbers** - Where to transfer calls
- [ ] **After-hours Number** - For after-hours calls

## Current Configuration Status

### Configured (Placeholders)

The following are currently set with placeholder values:

- **Office Name**: "John Li, MD - ENT Specialists"
- **Provider**: "Dr. John Li, MD"
- **Specialty**: "ENT / Otolaryngology"
- **Location ID**: "main-office"
- **Provider ID**: "dr-john-li"
- **Appointment Types**: 6 types defined (NEW_PATIENT_CONSULT, FOLLOW_UP, PROCEDURE_CONSULT, POST_OP_FOLLOW_UP, EMERGENCY, ROUTINE_CHECKUP)
- **Office Hours**: Standard business hours (placeholder)
- **Appointment Durations**: 30 minutes (placeholder)

### Not Configured

The following require input from Dr. Li:

- [ ] All office hours
- [ ] All appointment type durations
- [ ] All scheduling rules
- [ ] All staff information
- [ ] Emergency routing
- [ ] Reminder policy
- [ ] Voice persona
- [ ] Integration details

## Implementation Notes

### Current State

The system is currently using:
- Mock scheduler for testing
- Placeholder office information
- Default 30-minute appointment duration
- Standard business hours (9am-5pm)

### Next Steps

1. Provide office hours and contact information
2. Define appointment types and durations
3. Configure scheduling rules
4. Set up emergency routing
5. Configure voice persona and greeting
6. Integrate with scheduling system (when ready)

## Testing with Mock Data

For local testing, the system uses synthetic data:

- **Test Patient**: "John Doe", phone: "+15551234567"
- **Test Appointment**: 30-minute slots at 9am, 10:30am, 2pm, 3:30pm
- **Test Provider**: "dr-john-li"
- **Test Location**: "main-office"

## Privacy Considerations

When providing information, please note:

- No real patient data will be stored
- No real credentials will be committed to the repository
- All test data is synthetic
- Production integration will require proper security review

## Contact

For questions about the configuration, please contact the development team.