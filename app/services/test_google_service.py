# services/google_calendar.py
from sqlalchemy.orm import Session
from sqlmodel import select
from ..models import User, Event, Project, Team, Member, EventMemberLink # Import all necessary models
from typing import Optional, List
import requests
from ..utils.time import get_time_stamp
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

class GoogleCalendarService:
    def __init__(self, user: User, session: Session):
        self.user = user
        self.session = session
        # Ensure access_token and calendar_id are available
        self.access_token = self.ensure_valid_access_token()
        self.calendar_id = self.user.google_calendar_id # This might be None initially

        if not self.access_token:
            raise Exception("Missing or invalid Google access token for user.")

    def exchange_code_for_tokens(self, code: str) -> Optional[dict]:
        """Exchanges an authorization code for access and refresh tokens."""
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error exchanging code for tokens: {response.status_code} - {response.text}")
            return None

    def refresh_google_token(self) -> Optional[dict]:
        """Refreshes the Google access token using the refresh token."""
        if not self.user.google_refresh_token:
            print("No refresh token available for user.")
            return None

        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": self.user.google_refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to refresh token: {response.status_code} - {response.text}")
            return None

    def ensure_valid_access_token(self) -> Optional[str]:
        """
        Ensures the user has a valid access token, refreshing it if necessary.
        Updates the user's token fields in the database.
        """
        now = get_time_stamp()

        # If access token is missing or expired
        if not self.user.google_access_token or \
           (self.user.google_token_expiry and self.user.google_token_expiry < now):

            print(f"Access token for user {self.user.email} is missing or expired. Attempting refresh...")
            new_tokens = self.refresh_google_token()
            if new_tokens and "access_token" in new_tokens:
                self.user.google_access_token = new_tokens["access_token"]
                if "expires_in" in new_tokens:
                    # Calculate expiry time relative to now, ensuring it's timezone-aware
                    expiry_seconds = new_tokens["expires_in"]
                    self.user.google_token_expiry = now + timedelta(seconds=expiry_seconds)
                    print(f"New token expiry: {self.user.google_token_expiry}")
                else:
                    # If expires_in is not provided, assume it's a short-lived token
                    # or that the refresh token itself is being used directly.
                    # For safety, set a short expiry or mark as needing refresh often.
                    self.user.google_token_expiry = now + timedelta(minutes=5) # Arbitrary short expiry
                    print("Warning: 'expires_in' not in refresh response. Setting short expiry.")

                # A new refresh token might be issued, though less common with offline access
                if "refresh_token" in new_tokens:
                    self.user.google_refresh_token = new_tokens["refresh_token"]
                    print("New refresh token received and updated.")

                self.session.add(self.user)
                self.session.commit()
                self.session.refresh(self.user) # Refresh the user object to get latest state

                return self.user.google_access_token
            else:
                print(f"Failed to refresh token for user {self.user.email}. User needs to re-authorize.")
                return None
        return self.user.google_access_token

    def get_user_email_from_google(self, access_token: str) -> Optional[str]:
        """Fetches the user's email from Google's UserInfo API."""
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(userinfo_url, headers=headers)
        if response.status_code == 200:
            user_info = response.json()
            return user_info.get("email")
        else:
            print(f"Error fetching user email from Google: {response.status_code} - {response.text}")
            return None

    def create_user_calendar(self, summary: str = "My App Calendar", time_zone: str = "Europe/Berlin") -> Optional[str]:
        """
        Creates a new Google Calendar for the authorized user.
        Returns the new calendar's ID if successful.
        """
        if not self.access_token:
            print("Cannot create calendar: Access token is missing.")
            return None

        calendar_body = {
            'summary': summary,
            'timeZone': time_zone
        }
        response = requests.post(
            "https://www.googleapis.com/calendar/v3/calendars",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json=calendar_body,
        )

        if response.status_code == 200:
            calendar = response.json()
            self.user.google_calendar_id = calendar["id"]
            self.session.add(self.user)
            self.session.commit()
            self.session.refresh(self.user)
            print(f"Calendar '{calendar['summary']}' created with ID: {calendar['id']}")
            return calendar["id"]
        else:
            print(f"Error creating calendar: {response.status_code} - {response.text}")
            return None

    def sync_events_to_google_calendar(self):
        """
        Fetches all events for the current user from the local database
        and syncs them to their Google Calendar.
        Creates events that don't exist, updates existing ones.
        """
        if not self.calendar_id:
            print(f"No Google Calendar ID found for user {self.user.email}. Cannot sync events.")
            return {"status": "error", "message": "Google Calendar not set up for user."}

        # Fetch events created by this user from your database
        # Eagerly load relationships needed for event details (project, team, members, member.user)
        events_from_db = self.session.exec(
            select(Event)
            .where(Event.created_by == self.user.id)
            .options(
                # Load project and its team
                Relationship.load(Event.project).load_only(Project.name).options(
                    Relationship.load(Project.team).load_only(Team.name)
                ),
                # Load event members and their user details (for email)
                Relationship.load(Event.members).options(
                    Relationship.load(Member.user).load_only(User.email)
                )
            )
        ).all()

        print(f"Found {len(events_from_db)} events in DB for user {self.user.email}.")

        synced_count = 0
        for event_db in events_from_db:
            if event_db.google_event_id:
                # Event already exists in Google Calendar, try to update
                print(f"Updating event {event_db.title} (ID: {event_db.id}) in Google Calendar...")
                self.update_event(event_db.google_event_id, event_db)
            else:
                # Event does not exist in Google Calendar, create it
                print(f"Creating event {event_db.title} (ID: {event_db.id}) in Google Calendar...")
                google_event_id = self.create_event(event_db)
                if google_event_id:
                    event_db.google_event_id = google_event_id
                    self.session.add(event_db)
                    self.session.commit()
                    self.session.refresh(event_db)
                    synced_count += 1
                else:
                    print(f"Failed to create Google event for {event_db.title}.")
        print(f"Finished syncing events. {synced_count} new events created/updated.")
        return {"status": "success", "message": f"Synced {synced_count} events."}

    def create_event(self, event: Event) -> Optional[str]:
        """
        Creates a single event in the user's Google Calendar.
        Returns the Google Event ID if successful.
        """
        if not self.access_token or not self.calendar_id:
            print("Cannot create event: Missing access token or calendar ID.")
            return None

        # Safely get team and project names
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
            "attendees": [{"email": email} for email in assignee_emails]
        }

        response = requests.post(
            f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json=event_body
        )

        if response.status_code in (200, 201):
            return response.json().get("id")
        else:
            print(f"Error creating event: {response.status_code} - {response.text}")
            return None

    def update_event(self, google_event_id: str, event: Event):
        """
        Updates an existing event in the user's Google Calendar.
        """
        if not self.access_token or not self.calendar_id:
            print("Cannot update event: Missing access token or calendar ID.")
            return

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
            "attendees": [{"email": email} for email in assignee_emails]
        }

        response = requests.patch( # Use PATCH for partial updates
            f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events/{google_event_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json=event_body
        )

        if response.status_code not in (200, 201):
            print(f"Error updating event {google_event_id}: {response.status_code} - {response.text}")
        else:
            print(f"Successfully updated event {google_event_id}.")

    def delete_event(self, google_event_id: str):
        """
        Deletes an event from the user's Google Calendar.
        """
        if not self.access_token or not self.calendar_id:
            print("Cannot delete event: Missing access token or calendar ID.")
            return

        response = requests.delete(
            f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events/{google_event_id}",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )

        if response.status_code != 204:
            print(f"Error deleting event {google_event_id}: {response.status_code} - {response.text}")
        else:
            print(f"Successfully deleted event {google_event_id}.")