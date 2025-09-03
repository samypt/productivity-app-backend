from sqlalchemy.orm import Session
from ..models import Event, GoogleSyncedEvent
from typing import Optional, List
import requests
from dotenv import load_dotenv
import os

# Google API specific imports for Service Account
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()
SERVICE_ACCOUNT_KEY_FILE = os.getenv("GOOGLE_CREDENTIALS_PATH")
# Scopes required for the Service Account to manage calendars
SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarService:
    def __init__(self):
        self.service = self._build_service_account_client()
        if not self.service:
            raise Exception("Failed to initialize Google Calendar Service Account client.")

    def _build_service_account_client(self):
        """
        Builds and returns a Google Calendar API service instance using a Service Account.
        """
        try:
            # Load credentials from the service account key file
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_KEY_FILE, scopes=SCOPES
            )
            # Build the Google Calendar API service
            service = build('calendar', 'v3', credentials=credentials)
            print("Google Calendar Service Account client initialized successfully.")
            return service
        except FileNotFoundError:
            print(f"Error: Service account key file not found at {SERVICE_ACCOUNT_KEY_FILE}. "
                  "Please ensure it's in the correct path and named 'service_account_key.json'.")
            return None
        except Exception as e:
            print(f"Error initializing Google Calendar Service Account client: {e}")
            return None

    def get_email_from_access_token(self, access_token: str) -> str:
        response = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        user_info = response.json()
        return user_info["email"]


    def list_calendars(self):
        """
        Lists all calendars owned by the service account.
        Returns a list of calendar objects.
        """
        if not self.service:
            return []

        calendars = []
        page_token = None

        try:
            while True:
                calendar_list = self.service.calendarList().list(pageToken=page_token).execute()
                items = calendar_list.get('items', [])
                calendars.extend(items)

                page_token = calendar_list.get('nextPageToken')
                if not page_token:
                    break

            print(f"Found {len(calendars)} calendars.")
            return calendars

        except Exception as e:
            print(f"Error retrieving calendar list: {e}")
            return []


    def create_calendar(self, summary: str, time_zone: str = "Europe/Berlin") -> Optional[dict]:
        """
        Creates a new Google Calendar owned by the service account.
        Returns a dictionary with calendar ID and HTML link if successful.
        """
        if not self.service:
            return None

        calendar_body = {
            'summary': summary,
            'timeZone': time_zone
        }
        try:
            created_calendar = self.service.calendars().insert(body=calendar_body).execute()
            print(f"Calendar '{created_calendar['summary']}' created with ID: {created_calendar['id']}")
            return {
                "id": created_calendar['id'],
                "htmlLink": created_calendar.get('htmlLink')
            }
        except HttpError as error:
            print(f"Error creating calendar: {error}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while creating calendar: {e}")
            return None


    def delete_calendar(self, calendar_id: str) -> bool:
        """
        Deletes a Google Calendar by calendar ID.
        Returns True if deletion was successful, False otherwise.
        """
        if not self.service:
            return False

        try:
            self.service.calendars().delete(calendarId=calendar_id).execute()
            print(f"Calendar with ID {calendar_id} deleted successfully.")
            return True
        except HttpError as error:
            print(f"Error deleting calendar: {error}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred while deleting calendar: {e}")
            return False


    def share_calendar_to_user(self, user_email: str, calendar_id:str) -> Optional[dict]:
        """
        Share Google Calendar owned by the service account to the user.
        Returns a dictionary with calendar ID and HTML link if successful.
        """
        try:
            rule = {
                "scope": {
                    "type": "user",
                    "value": user_email,
                },
                "role": "reader",  # or 'writer'
            }
            self.service.acl().insert(calendarId=calendar_id, body=rule).execute()
        except HttpError as error:
            print(f"Error sharing calendar: {error}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while sharing calendar: {e}")
            return None



    def sync_events_to_google_calendar(self,
                                       user_id:str,
                                       calendar_id: str,
                                       events_from_db: List[Event],
                                       session: Session):
        """
        Syncs a list of events from the local database to a specific Google Calendar ID.
        Creates events that don't exist, updates existing ones.
        """
        if not self.service:
            return {"status": "error", "message": "Google Calendar service not initialized."}
        if not calendar_id:
            return {"status": "error", "message": "No Google Calendar ID provided for syncing."}

        synced_count = 0
        created_count = 0
        updated_count = 0
        failed_count = 0

        for event_db in events_from_db:
            try:
                # Try to find a GoogleSyncedEvent for the current user
                synced_event = next(
                    (event for event in event_db.google_events if event.user_id == user_id and event.google_event_id),
                    None
                )

                if synced_event:
                    print(f"Attempting to update event {event_db.title} (DB ID: {event_db.id},"
                          f" Google ID: {synced_event.google_event_id})...")
                    success = self.update_event(synced_event, event_db)
                    if success:
                        updated_count += 1
                    else:
                        failed_count += 1
                else:
                    # Event does not exist in Google Calendar, create it
                    print(f"Attempting to create event {event_db.title} (DB ID: {event_db.id})...")
                    google_event_id = self.create_event(calendar_id, event_db)
                    if google_event_id:
                        google_event = GoogleSyncedEvent(
                            event_id=event_db.id,
                            user_id=user_id,
                            google_event_id=google_event_id,
                            google_calendar_id=calendar_id
                        )
                        session.add(google_event)
                        session.commit()
                        session.refresh(google_event)
                        created_count += 1
                    else:
                        failed_count += 1
            except Exception as e:
                print(f"Unhandled error syncing event {event_db.id}: {e}")
                failed_count += 1


        synced_count = created_count + updated_count
        print(f"Finished syncing events. Created: {created_count},"
              f" Updated: {updated_count}, Failed: {failed_count}.")

        # google_event_ids = self.get_all_event_ids_from_calendar(calendar_id)
        # local_google_ids = [event.google_event.google_event_id for event in events_from_db if event.google_event]
        #
        # # Find deleted or orphaned events
        # missing_in_db = set(google_event_ids) - set(local_google_ids)

        return {
            "status": "success",
            "message": f"Synced {synced_count} events."
                       f" Created: {created_count}, Updated: {updated_count},"
                       f" Failed: {failed_count}.",
            "created_count": created_count,
            "updated_count": updated_count,
            "failed_count": failed_count
        }


    def get_all_event_ids_from_calendar(self, calendar_id: str) -> List[str]:
        """
        Fetches all event IDs from a specific Google Calendar.
        Returns a list of Google event IDs.
        """
        if not self.service:
            return []

        event_ids = []
        page_token = None

        try:
            while True:
                events_result = self.service.events().list(
                    calendarId=calendar_id,
                    pageToken=page_token,
                    showDeleted=False,
                    singleEvents=True,
                    maxResults=2500
                ).execute()

                for event in events_result.get("items", []):
                    if "id" in event:
                        event_ids.append(event["id"])

                page_token = events_result.get("nextPageToken")
                if not page_token:
                    break
        except Exception as e:
            print(f"Error fetching events from calendar {calendar_id}: {e}")

        return event_ids

    def create_event(self, calendar_id: str, event: Event) -> Optional[str]:
        """
        Creates a single event in the specified Google Calendar.
        Returns the Google Event ID if successful.
        """
        if not self.service:
            return None

        # Safely get related names (ensure relationships are loaded in main.py query)
        team_name = event.project.team.name if event.project and event.project.team else ""
        project_name = event.project.name if event.project else ""
        assignee_emails = [member.user.email for member in event.members if member.user]



        summary = f"{event.title} | {team_name} - {project_name}" if team_name or project_name else event.title
        description = f"{event.description or ''}\n\nTeam: {team_name}\nProject: {project_name}".strip()

        event_body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": event.start_time.isoformat(), "timeZone": "Europe/Berlin"},
            "end": {"dateTime": event.end_time.isoformat(), "timeZone": "Europe/Berlin"},
            # "attendees": [{"email": email} for email in assignee_emails]
        }

        try:
            created_event = self.service.events().insert(calendarId=calendar_id, body=event_body).execute()
            print(f"Google event created: {created_event.get('id')}")
            return created_event.get("id")
        except HttpError as error:
            print(f"Error creating event: {error}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while creating event: {e}")
            return None


    def update_event(self, google_event: GoogleSyncedEvent, db_event: Event) -> bool:
        """
        Updates an existing event in the specified Google Calendar.
        Returns True if successful, False otherwise.
        """
        if not self.service:
            return False

        team_name = db_event.project.team.name if db_event.project and db_event.project.team else ""
        project_name = db_event.project.name if db_event.project else ""
        assignee_emails = [member.user.email for member in db_event.members if member.user]

        summary = f"{db_event.title} | {team_name} - {project_name}" if team_name or project_name else db_event.title
        description = f"{db_event.description or ''}\n\nTeam: {team_name}\nProject: {project_name}".strip()

        event_body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": db_event.start_time.isoformat(), "timeZone": "Europe/Berlin"},
            "end": {"dateTime": db_event.end_time.isoformat(), "timeZone": "Europe/Berlin"},
            # "attendees": [{"email": email} for email in assignee_emails]
        }

        try:
            self.service.events().patch(calendarId=google_event.google_calendar_id,
                                        eventId=google_event.google_event_id,
                                        body=event_body).execute()
            print(f"Successfully updated event {google_event.google_event_id}.")
            return True
        except HttpError as error:
            print(f"Error updating event {google_event.google_event_id}: {error}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred while updating event {google_event.google_event_id}: {e}")
            return False

    def delete_event(self, google_event: GoogleSyncedEvent) -> bool:
        """
        Deletes an event from the specified Google Calendar.
        Returns True if successful, False otherwise.
        """
        if not self.service:
            return False

        try:
            self.service.events().delete(calendarId=google_event.google_calendar_id,
                                         eventId=google_event.google_event_id).execute()
            print(f"Successfully deleted event {google_event.google_event_id}.")
            return True
        except HttpError as error:
            print(f"Error deleting event {google_event.google_event_id}: {error}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred while deleting event {google_event.google_event_id}: {e}")
            return False

    def get_calendar_html_link(self, calendar_id: str) -> Optional[str]:
        """
        Retrieves the HTML link for a given calendar ID, which users can use to subscribe.
        """
        if not self.service:
            return None
        try:
            calendar = self.service.calendars().get(calendarId=calendar_id).execute()
            return calendar.get('htmlLink')
        except HttpError as error:
            print(f"Error getting calendar link for {calendar_id}: {error}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while getting calendar link: {e}")
            return None