"""John Li ENT inbound voice workflow configuration.

This module defines the workflow for the John Li ENT automated scheduling assistant.
The workflow handles various call intents including new appointments, confirmations,
rescheduling, cancellations, and more.
"""

from datetime import datetime, timezone
from typing import Optional

from api.services.scheduling.models import (
    AppointmentType,
    CallDisposition,
    CallIntent,
)
from api.services.scheduling.practice_config import get_practice_config


class JohnLiWorkflow:
    """John Li ENT inbound voice workflow.
    
    This class defines the workflow for the automated scheduling assistant
    for the office of John Li, MD, an ENT physician.
    """
    
    def __init__(self):
        """Initialize the workflow."""
        self.config = get_practice_config()
    
    def get_greeting(self) -> str:
        """Get the greeting message.
        
        Returns:
            The greeting message.
        """
        return self.config.greeting
    
    def get_emergency_message(self) -> str:
        """Get the emergency escalation message.
        
        Returns:
            The emergency message.
        """
        return self.config.emergency_message
    
    def get_office_hours(self) -> dict:
        """Get office hours.
        
        Returns:
            Dictionary with office hours by day.
        """
        hours = {}
        for day, (open_time, close_time) in self.config.office_hours.items():
            if open_time and close_time:
                hours[day] = f"{open_time.strftime('%I:%M %p')} - {close_time.strftime('%I:%M %p')}"
            else:
                hours[day] = "Closed"
        return hours
    
    def get_appointment_types(self) -> list[str]:
        """Get list of appointment types.
        
        Returns:
            List of appointment type values.
        """
        return [t.value for t in AppointmentType]
    
    def get_provider_info(self) -> dict:
        """Get provider information.
        
        Returns:
            Dictionary with provider information.
        """
        return {
            "name": self.config.provider_name,
            "id": self.config.provider_id,
            "specialty": self.config.specialty,
        }
    
    def get_location_info(self) -> dict:
        """Get location information.
        
        Returns:
            Dictionary with location information.
        """
        return {
            "name": self.config.office_name,
            "address": self.config.office_address,
            "phone": self.config.office_phone,
        }
    
    def is_clinical_question(self, text: str) -> bool:
        """Check if the text contains a clinical question.
        
        Args:
            text: The text to check.
            
        Returns:
            True if the text appears to be a clinical question.
        """
        clinical_keywords = [
            "what do you think",
            "is this",
            "should i",
            "why am i",
            "how do i",
            "diagnosis",
            "cancer",
            "tumor",
            "surgery",
            "medication",
            "pain",
            "bleeding",
            "swelling",
            "infection",
            "fever",
            "headache",
            "dizziness",
            "hearing",
            "ringing",
            "ear",
            "nose",
            "throat",
            "sinus",
            "allergy",
        ]
        
        text_lower = text.lower()
        for keyword in clinical_keywords:
            if keyword in text_lower:
                return True
        return False
    
    def is_emergency_statement(self, text: str) -> bool:
        """Check if the text contains an emergency statement.
        
        Args:
            text: The text to check.
            
        Returns:
            True if the text appears to be an emergency statement.
        """
        emergency_keywords = [
            "emergency",
            "urgent",
            "bleeding heavily",
            "can't breathe",
            "severe pain",
            "loss of consciousness",
            "difficulty breathing",
            "severe swelling",
            "hemorrhage",
        ]
        
        text_lower = text.lower()
        for keyword in emergency_keywords:
            if keyword in text_lower:
                return True
        return False
    
    def get_disposition_for_intent(self, intent: CallIntent) -> CallDisposition:
        """Get the disposition for a given intent.
        
        Args:
            intent: The call intent.
            
        Returns:
            The appropriate disposition.
        """
        disposition_map = {
            CallIntent.NEW_APPOINTMENT: CallDisposition.APPOINTMENT_BOOKED,
            CallIntent.CONFIRM_APPOINTMENT: CallDisposition.APPOINTMENT_CONFIRMED,
            CallIntent.RESCHEDULE_APPOINTMENT: CallDisposition.APPOINTMENT_RESCHEDULED,
            CallIntent.CANCEL_APPOINTMENT: CallDisposition.APPOINTMENT_CANCELED,
            CallIntent.OFFICE_INFORMATION: CallDisposition.OFFICE_INFO_PROVIDED,
            CallIntent.LEAVE_MESSAGE: CallDisposition.MESSAGE_LEFT,
            CallIntent.CLINICAL_QUESTION: CallDisposition.CLINICAL_QUESTION_ESCALATED,
            CallIntent.HUMAN_REQUEST: CallDisposition.ESCALATED_TO_STAFF,
            CallIntent.EMERGENCY_OR_URGENT_ESCALATION: CallDisposition.ESCALATED_TO_STAFF,
            CallIntent.OTHER: CallDisposition.CALL_ENDED,
        }
        
        return disposition_map.get(intent, CallDisposition.CALL_ENDED)


# Global workflow instance
_workflow: Optional[JohnLiWorkflow] = None


def get_john_li_workflow() -> JohnLiWorkflow:
    """Get the John Li workflow instance.
    
    Returns:
        The John Li workflow instance.
    """
    global _workflow
    if _workflow is None:
        _workflow = JohnLiWorkflow()
    return _workflow


def reset_john_li_workflow() -> None:
    """Reset the John Li workflow instance (for testing)."""
    global _workflow
    _workflow = None