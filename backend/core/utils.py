import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
import dateparser

logger = logging.getLogger(__name__)


def extract_datetime(text: str) -> Optional[Tuple[str, str]]:
    """
    Extract date and time from natural language text.
    Returns tuple of (date_str, time_str) in YYYY-MM-DD and HH:MM format.
    """
    try:
        # Use dateparser to handle natural language dates
        parsed_date = dateparser.parse(
            text,
            settings={
                'PREFER_DATES_FROM': 'future',
                'RETURN_AS_TIMEZONE_AWARE': False
            }
        )
        
        if parsed_date:
            date_str = parsed_date.strftime("%Y-%m-%d")
            time_str = parsed_date.strftime("%H:%M")
            return date_str, time_str
            
    except Exception as e:
        logger.error(f"Error parsing datetime from text '{text}': {e}")
    
    return None


def format_appointment_details(appointment: Dict[str, Any]) -> str:
    """Format appointment details for display"""
    try:
        date_obj = appointment.get('datetime')
        if isinstance(date_obj, datetime):
            formatted_date = date_obj.strftime("%A, %B %d, %Y at %I:%M %p")
        else:
            # Fallback to date and time strings
            date_str = appointment.get('date', '')
            time_str = appointment.get('time', '')
            if date_str and time_str:
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                formatted_date = dt.strftime("%A, %B %d, %Y at %I:%M %p")
            else:
                formatted_date = "Date/time not available"
        
        purpose = appointment.get('purpose', 'General consultation')
        status = appointment.get('status', 'confirmed').title()
        
        return f"{formatted_date} - {purpose} ({status})"
        
    except Exception as e:
        logger.error(f"Error formatting appointment details: {e}")
        return "Appointment details unavailable"


def clean_phone_number(phone: str) -> str:
    """Clean and format phone number"""
    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', phone)
    
    # Handle US phone numbers
    if len(cleaned) == 10:
        return cleaned
    elif len(cleaned) == 11 and cleaned.startswith('1'):
        return cleaned[1:]  # Remove country code
    
    return cleaned


def validate_appointment_time(date_str: str, time_str: str) -> bool:
    """Validate if appointment time is in the future and during business hours"""
    try:
        appointment_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        now = datetime.now()
        
        # Check if appointment is in the future
        if appointment_dt <= now:
            return False
        
        # Check business hours (9 AM to 5 PM)
        hour = appointment_dt.hour
        if hour < 9 or hour >= 17:
            return False
        
        # Check if it's a weekday (Monday = 0, Sunday = 6)
        if appointment_dt.weekday() >= 5:  # Saturday or Sunday
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating appointment time: {e}")
        return False


def generate_available_slots(date_str: str, booked_slots: list) -> list:
    """Generate available appointment slots for a given date"""
    try:
        # Business hours: 9 AM to 5 PM
        base_slots = []
        for hour in range(9, 17):  # 9 AM to 4 PM (last slot)
            base_slots.append(f"{hour:02d}:00")
        
        # Filter out booked slots
        booked_times = [slot.split(' ')[1] for slot in booked_slots if slot.startswith(date_str)]
        available_slots = [slot for slot in base_slots if slot not in booked_times]
        
        return available_slots
        
    except Exception as e:
        logger.error(f"Error generating available slots: {e}")
        return []


def format_conversation_summary(summary_data: Dict[str, Any]) -> str:
    """Format conversation summary for display"""
    try:
        parts = []
        
        # Add date
        conv_date = summary_data.get('conversation_date')
        if isinstance(conv_date, datetime):
            parts.append(f"Conversation on {conv_date.strftime('%B %d, %Y at %I:%M %p')}")
        
        # Add appointments discussed
        appointments = summary_data.get('appointments_discussed', [])
        if appointments:
            parts.append("Appointments discussed:")
            for apt in appointments:
                parts.append(f"  - {apt.get('date')} at {apt.get('time')}: {apt.get('purpose')}")
        
        # Add user preferences
        preferences = summary_data.get('user_preferences', [])
        if preferences:
            parts.append(f"User preferences: {', '.join(preferences)}")
        
        # Add summary text
        summary_text = summary_data.get('summary_text', '')
        if summary_text:
            parts.append(f"Summary: {summary_text}")
        
        return '\n'.join(parts)
        
    except Exception as e:
        logger.error(f"Error formatting conversation summary: {e}")
        return "Summary unavailable"


def extract_user_preferences(conversation_text: str) -> list:
    """Extract user preferences from conversation text"""
    preferences = []
    
    # Common preference patterns
    preference_patterns = [
        r"prefer (\w+)",
        r"like (\w+)",
        r"usually (\w+)",
        r"always (\w+)",
        r"never (\w+)"
    ]
    
    try:
        for pattern in preference_patterns:
            matches = re.findall(pattern, conversation_text.lower())
            preferences.extend(matches)
        
        # Remove duplicates and common words
        common_words = {'to', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'by'}
        preferences = list(set([pref for pref in preferences if pref not in common_words]))
        
    except Exception as e:
        logger.error(f"Error extracting preferences: {e}")
    
    return preferences[:5]  # Limit to 5 preferences


def calculate_response_time(start_time: datetime, end_time: datetime) -> float:
    """Calculate response time in seconds"""
    try:
        delta = end_time - start_time
        return delta.total_seconds()
    except Exception as e:
        logger.error(f"Error calculating response time: {e}")
        return 0.0


def log_tool_call(tool_name: str, parameters: Dict[str, Any], result: str, duration: float):
    """Log tool call for debugging and monitoring"""
    logger.info(
        f"Tool call: {tool_name} | "
        f"Parameters: {parameters} | "
        f"Duration: {duration:.2f}s | "
        f"Result length: {len(result)} chars"
    )