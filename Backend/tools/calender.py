import os
import logging
import json
from typing import List, Dict, Any, Optional, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from datetime import datetime, timedelta
import re
import calendar
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.local")

try:
    from gcsa.google_calendar import GoogleCalendar
    from gcsa.event import Event, Reminder
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
except ImportError:
    GoogleCalendar = None
    Event = None
    Reminder = None
    service_account = None
    Request = None

logger = logging.getLogger(__name__)


class CalendarDate(TypedDict):
    """Date structure for calendar events"""
    month: int
    day: int
    year: int
    hour: int
    minute: int


class FollowUpMeetingInfo(TypedDict):
    """Information about a detected follow-up meeting"""
    summary: str
    date: Optional[CalendarDate]
    location: Optional[str]
    description: Optional[str]
    participants: Optional[List[str]]


def _get_google_calendar_client(email: str) -> Optional[GoogleCalendar]:
    """
    Get Google Calendar client for a user email.
    Uses service account authentication.
    """
    if GoogleCalendar is None:
        logger.error("gcsa package not installed")
        return None
    
    try:
        # Check for service account credentials
        service_account_json = os.environ.get("GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON")
        if not service_account_json:
            logger.warning("GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON not set")
            return None
        
        # Parse service account JSON (can be string or file path)
        credentials_dict = None
        try:
            if os.path.isfile(service_account_json):
                # Read from file
                with open(service_account_json, 'r') as f:
                    credentials_dict = json.load(f)
                logger.debug(f"Loaded service account from file: {service_account_json}")
            else:
                # Try to parse as JSON string
                try:
                    credentials_dict = json.loads(service_account_json)
                    logger.debug("Loaded service account from JSON string")
                except json.JSONDecodeError as e:
                    # If it's not valid JSON, treat it as a file path that might not exist
                    logger.error(f"GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON is not a valid file path or JSON string: {service_account_json}, error: {e}")
                    return None
        except FileNotFoundError:
            logger.error(f"Service account file not found: {service_account_json}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse service account JSON from {service_account_json}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading service account file {service_account_json}: {e}")
            return None
        
        # Check if credentials_dict is valid
        if not credentials_dict or not isinstance(credentials_dict, dict):
            logger.error(f"Service account JSON is empty or not a dictionary: {type(credentials_dict)}")
            return None
        
        # Validate required fields
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id', 'token_uri']
        missing_fields = [field for field in required_fields if field not in credentials_dict]
        if missing_fields:
            logger.error(f"Service account JSON missing required fields: {missing_fields}")
            logger.error(f"Available fields in JSON: {list(credentials_dict.keys())}")
            logger.error(f"File path: {service_account_json}")
            return None
        
        # Verify it's a service account (not OAuth client)
        if credentials_dict.get('type') != 'service_account':
            logger.error(f"Credentials type is '{credentials_dict.get('type')}', expected 'service_account'")
            return None
        
        # Create credentials
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        # Create calendar client with service account
        # Note: For service account, the user's calendar must be shared with the service account email
        # Use the user's email as the calendar ID (not 'primary' which would be the service account's calendar)
        calendar = GoogleCalendar(credentials=credentials, default_calendar=email)
        logger.info(f"Created Google Calendar client for user calendar: {email}")
        return calendar
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing service account JSON: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error creating Google Calendar client: {e}", exc_info=True)
        return None


@tool
def add_event(
    event_summary: str,
    date: CalendarDate,
    email: str,
    location: str = "",
    reminder_before: int = 15,
    description: str = ""
) -> str:
    """
    Add an event to the user's Google Calendar.
    
    Args:
        event_summary: Summary/title of the event
        date: Dictionary with year, month, day, hour, minute
        email: User's email address
        location: Location of the event (optional)
        reminder_before: Minutes before event to send reminder (default: 15)
        description: Description of the event (optional)
        
    Returns:
        Success or error message
    """
    try:
        if Event is None or GoogleCalendar is None:
            return "Error: Google Calendar library not installed. Please install gcsa package."
        
        calendar = _get_google_calendar_client(email)
        if calendar is None:
            return "Error: Could not connect to Google Calendar. Please check service account configuration."
        
        # Try to verify calendar access before adding event
        try:
            # Attempt to get calendar info to verify access
            calendar_list = list(calendar.get_calendar_list())
            logger.debug(f"Calendar access verified for {email}")
        except Exception as verify_error:
            error_str = str(verify_error)
            if "404" in error_str or "notFound" in error_str:
                # Get service account email for error message
                service_account_email = "cloud-admin@sunlit-hub-443019-r4.iam.gserviceaccount.com"
                try:
                    service_account_json = os.environ.get("GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON")
                    if service_account_json:
                        if os.path.isfile(service_account_json):
                            with open(service_account_json, 'r') as f:
                                creds = json.load(f)
                                service_account_email = creds.get('client_email', service_account_email)
                        else:
                            creds = json.loads(service_account_json)
                            service_account_email = creds.get('client_email', service_account_email)
                except:
                    pass
                
                return f"""Error: Calendar '{email}' is not accessible to the service account.

The service account cannot access this calendar. Please share your calendar:

1. Go to Google Calendar (calendar.google.com)
2. Click the gear icon ⚙️ → Settings
3. In the left sidebar, click "Share with specific people"
4. Click "Add people"
5. Enter: {service_account_email}
6. Set permission to "Make changes to events"
7. Click "Send"
8. Wait 1-2 minutes, then try again

Note: For personal Gmail accounts, you must share the calendar with the service account."""
            # If it's a different error, continue and let add_event handle it
        
        # Create datetime object
        event_datetime = datetime(
            date["year"],
            date["month"],
            date["day"],
            date["hour"],
            date["minute"]
        )
        
        # Create event with reminder if specified
        if reminder_before > 0 and Reminder is not None:
            # Create reminder object - use minutes_before_start parameter
            reminder = Reminder(method='email', minutes_before_start=reminder_before)
            event = Event(
                summary=event_summary,
                start=event_datetime,
                location=location if location else None,
                description=description if description else None,
                reminders=[reminder]
            )
        else:
            # Create event without reminder
            event = Event(
                summary=event_summary,
                start=event_datetime,
                location=location if location else None,
                description=description if description else None,
            )
        
        # Add event to calendar
        # Explicitly add to the user's calendar by using the email as calendar ID
        try:
            added_event = calendar.add_event(event)
            event_id = added_event.id if hasattr(added_event, 'id') else 'unknown'
            logger.info(f"Added event '{event_summary}' to calendar {email} (Event ID: {event_id})")
            
            # Return success message with helpful information
            return f"""Successfully added event '{event_summary}' to your calendar ({email}) for {event_datetime.strftime('%Y-%m-%d %H:%M')}.

Event ID: {event_id}

Note: If you don't see the event in your calendar, please ensure:
1. Your calendar '{email}' is shared with the service account email
2. The service account has "Make changes to events" permission
3. Refresh your calendar view"""
        except Exception as add_error:
            logger.error(f"Error during calendar.add_event: {add_error}", exc_info=True)
            raise
    except Exception as e:
        error_str = str(e)
        logger.error(f"Error adding event to calendar: {e}", exc_info=True)
        
        # Provide helpful error messages for common issues
        if "accessNotConfigured" in error_str or "API has not been used" in error_str:
            # Extract project ID if available
            project_match = re.search(r'project (\d+)', error_str)
            project_id = project_match.group(1) if project_match else "your-project-id"
            
            return f"""Error: Google Calendar API is not enabled for your project.

To fix this:
1. Go to Google Cloud Console: https://console.cloud.google.com/apis/api/calendar-json.googleapis.com/overview?project={project_id}
2. Click "Enable" to enable the Google Calendar API
3. Wait a few minutes for the changes to propagate
4. Try again

Alternatively, enable it via:
https://console.developers.google.com/apis/api/calendar-json.googleapis.com/overview?project={project_id}

Also ensure:
- The calendar '{email}' is shared with the service account email
- The service account has proper permissions"""
        
        elif "404" in error_str or "notFound" in error_str or "Not Found" in error_str:
            # Get service account email from credentials
            service_account_email = "the service account email"
            try:
                service_account_json = os.environ.get("GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON")
                if service_account_json:
                    if os.path.isfile(service_account_json):
                        with open(service_account_json, 'r') as f:
                            creds = json.load(f)
                            service_account_email = creds.get('client_email', 'the service account email')
                    else:
                        creds = json.loads(service_account_json)
                        service_account_email = creds.get('client_email', 'the service account email')
            except:
                pass
            
            return f"""Error: Calendar '{email}' not found or not accessible.

The service account cannot access this calendar. To fix this:

1. Share your Google Calendar with the service account:
   - Open Google Calendar (calendar.google.com)
   - Click the gear icon ⚙️ → Settings
   - In the left sidebar, click "Share with specific people"
   - Click "Add people"
   - Enter: {service_account_email}
   - Set permission to "Make changes to events"
   - Click "Send"

2. Wait a few minutes for the sharing to take effect

3. Try adding the event again

Note: The calendar must be shared with the service account email for it to add events on your behalf."""
        
        elif "403" in error_str or "Forbidden" in error_str:
            # Get service account email from credentials
            service_account_email = "the service account email"
            try:
                service_account_json = os.environ.get("GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON")
                if service_account_json:
                    if os.path.isfile(service_account_json):
                        with open(service_account_json, 'r') as f:
                            creds = json.load(f)
                            service_account_email = creds.get('client_email', 'the service account email')
                    else:
                        creds = json.loads(service_account_json)
                        service_account_email = creds.get('client_email', 'the service account email')
            except:
                pass
            
            return f"""Error: Access denied to calendar '{email}'.

To fix this:
1. Share your Google Calendar with the service account email: {service_account_email}
   - Go to Google Calendar settings
   - Click "Share with specific people"
   - Add the service account email
   - Grant "Make changes to events" permission
2. Ensure Google Calendar API is enabled in your Google Cloud project
3. Wait a few minutes and try again"""
        
        elif "401" in error_str or "Unauthorized" in error_str:
            return f"""Error: Authentication failed.

Please check:
1. Service account credentials are correct
2. GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON environment variable is set correctly
3. The service account has the necessary permissions"""
        
        else:
            return f"Error adding event to calendar: {error_str}"


@tool
def detect_followup_meetings(
    transcript_text: str,
    transcript_start_date: Optional[str] = None,
    current_date: Optional[str] = None
) -> str:
    """
    Detect follow-up meetings mentioned in transcript text using LLM analysis.
    Analyzes the transcript to find mentions of future meetings, scheduled events, or follow-ups.
    Uses transcript start date as reference for relative dates like "next Friday" or "next week".
    
    Args:
        transcript_text: The transcript text to analyze
        transcript_start_date: The date when the transcript/meeting started (YYYY-MM-DD format, optional)
                              Used as reference for calculating relative dates like "next Friday"
        current_date: Current date in YYYY-MM-DD format (optional, defaults to transcript_start_date or today)
        
    Returns:
        JSON string with detected meeting information or error message
    """
    try:
        if not transcript_text or not transcript_text.strip():
            return json.dumps({"meetings": [], "message": "No transcript text provided"})
        
        # Use transcript start date as reference if provided, otherwise use current date
        reference_date = transcript_start_date
        if not reference_date:
            reference_date = current_date
        if not reference_date:
            reference_date = datetime.now().strftime("%Y-%m-%d")
        
        # Parse reference date to get day of week and other info for better context
        try:
            ref_datetime = datetime.strptime(reference_date, "%Y-%m-%d")
            day_of_week = ref_datetime.strftime("%A")  # Monday, Tuesday, etc.
            week_number = ref_datetime.isocalendar()[1]  # ISO week number
            date_context = f"{reference_date} ({day_of_week}, week {week_number})"
        except Exception as e:
            logger.warning(f"Could not parse reference date {reference_date}: {e}")
            date_context = reference_date
        
        # Initialize LLM for extraction
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            return json.dumps({"meetings": [], "error": "OPENAI_API_KEY not configured"})
        
        llm = ChatOpenAI(
            model=os.environ.get("CHATBOT_MODEL", "gpt-4o-mini"),
            temperature=0.3,
            openai_api_key=openai_api_key
        )
        
        # Create prompt for LLM with date calculation instructions
        system_prompt = """You are an expert at extracting meeting information from transcripts and calculating dates.
Analyze the transcript and identify any follow-up meetings, scheduled events, or future meetings mentioned.
Extract the following information for each meeting:
- summary: A clear title/summary of the meeting
- date: If a specific date is mentioned (e.g., "January 4th, 2026", "4th January 2026"), extract it.
        If relative date is mentioned (e.g., "next Friday", "next week", "tomorrow", "in 2 weeks"), 
        calculate the actual date based on the transcript reference date.
        IMPORTANT: Use the transcript reference date as the starting point for calculations.
        Examples:
        - "next Friday" = find the next Friday after the reference date
        - "next week" = 7 days after the reference date
        - "tomorrow" = 1 day after the reference date
        - "in 2 weeks" = 14 days after the reference date
        - "next month" = same day next month
- time: If a specific time is mentioned (e.g., "4 PM", "4pm", "16:00"), extract it in 24-hour format.
        Default to hour=14, minute=0 if only "afternoon" or similar is mentioned.
        Use null if no time is specified.
- location: If a location is mentioned, extract it. Otherwise, use null.
- description: Any additional context about the meeting. Include the original mention from transcript.
- participants: List of people mentioned who will attend (if any)

Transcript reference date (use this as the base for relative date calculations): {reference_date}
Current date (for context): {current_date}

Return a JSON object with this structure:
{{
    "meetings": [
        {{
            "summary": "Meeting title",
            "date": {{"year": 2026, "month": 1, "day": 4, "hour": 16, "minute": 0}} or null if not specified,
            "location": "Location" or null,
            "description": "Description" or null,
            "participants": ["Name1", "Name2"] or null
        }}
    ]
}}

If no meetings are found, return {{"meetings": []}}.
Only extract meetings that are clearly scheduled or planned for the future.
Always calculate relative dates from the transcript reference date, not the current date.""".format(
            reference_date=date_context,
            current_date=datetime.now().strftime("%Y-%m-%d")
        )
        
        user_prompt = f"Analyze this transcript and extract any follow-up meetings:\n\n{transcript_text[:4000]}"  # Limit to avoid token limits
        
        # Call LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        response_text = response.content.strip()
        
        # Try to extract JSON from response
        # Sometimes LLM wraps JSON in markdown code blocks
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
        
        # Parse and validate JSON
        try:
            result = json.loads(response_text)
            if "meetings" not in result:
                result = {"meetings": []}
            return json.dumps(result)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response as JSON: {e}")
            logger.error(f"Response was: {response_text}")
            return json.dumps({
                "meetings": [],
                "error": f"Could not parse meeting information: {str(e)}",
                "raw_response": response_text[:500]
            })
    except Exception as e:
        logger.error(f"Error detecting follow-up meetings: {e}", exc_info=True)
        return json.dumps({
            "meetings": [],
            "error": f"Error analyzing transcript: {str(e)}"
        })


@tool
def search_events(
    query: str,
    email: str,
    max_results: int = 10
) -> str:
    """
    Search the user's Google Calendar for events matching a query.
    
    Args:
        query: Search query (searches in event titles and descriptions)
        email: User's email address
        max_results: Maximum number of results to return (default: 10)
        
    Returns:
        JSON string with matching events or error message
    """
    try:
        if GoogleCalendar is None:
            return json.dumps({"events": [], "error": "Google Calendar library not installed"})
        
        calendar = _get_google_calendar_client(email)
        if calendar is None:
            return json.dumps({"events": [], "error": "Could not connect to Google Calendar"})
        
        # Search for events
        # Note: gcsa doesn't have a direct search method, so we'll get upcoming events
        # and filter them
        events = []
        try:
            # Get events from now onwards
            for event in calendar.get_events(time_min=datetime.now(), max_results=max_results * 2):
                # Filter by query (case-insensitive search in summary and description)
                event_summary = event.summary or ""
                event_description = event.description or ""
                
                if query.lower() in event_summary.lower() or query.lower() in event_description.lower():
                    events.append({
                        "summary": event_summary,
                        "start": event.start.strftime("%Y-%m-%d %H:%M") if hasattr(event.start, 'strftime') else str(event.start),
                        "location": event.location or "",
                        "description": event_description[:200] if event_description else ""
                    })
                    
                    if len(events) >= max_results:
                        break
        except Exception as e:
            logger.error(f"Error fetching events: {e}", exc_info=True)
            return json.dumps({"events": [], "error": f"Error fetching events: {str(e)}"})
        
        return json.dumps({"events": events, "count": len(events)})
    except Exception as e:
        logger.error(f"Error searching calendar events: {e}", exc_info=True)
        return json.dumps({"events": [], "error": f"Error searching calendar: {str(e)}"})
