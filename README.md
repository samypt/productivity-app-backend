# Teamly – Team Productivity App (Backend)

*Teamly is a modern productivity platform for managing tasks and events, built for seamless team collaboration.*  

## Overview

Teamly is a web-based application that helps teams organize their work across multiple projects. It combines **project management** and **calendar scheduling** features in one place so teams can track tasks and plan events effortlessly. The platform is inspired by tools like Trello and Jira, offering kanban-style boards for task management alongside a shared calendar for events. 

This project was created as a **portfolio piece** to showcase full-stack development skills. It demonstrates how to build a robust backend for a real-world collaborative app – from secure user authentication and role-based access, to integrations with external services. Teamly is fully functional for team use, allowing members to collaborate on projects, assign tasks, schedule meetings, and stay productive in a modern, startup-like environment.

## Features

- **Multi-Team & Project Organization:** Organize work by creating multiple teams, each containing its own projects. This structure makes it easy to collaborate with different groups or departments in isolation. Within a team, owners can invite new members via email and assign them roles (Owner, Editor, or Viewer) to control access rights.  

- **Kanban Boards for Tasks:** Each project can have boards with customizable lists (to-do, in-progress, done, etc.), similar to Trello’s approach. Team members can create tasks on these boards, add detailed descriptions, set due-dates and priority levels (1-5), and assign tasks to one or more team members. Tasks can be moved between lists to reflect status changes, supporting a drag-and-drop workflow for agile project management.  

- **Event Calendar & Scheduling:** Teamly includes an integrated calendar for each project to schedule events, deadlines, and meetings. Events have titles, descriptions, and defined start/end times, giving the team a clear timeline of project activities. This helps synchronize everyone’s schedule and ensures important dates (like demos, sprint planning, or due dates) are visible to the whole team.  

- **Real-Time Notifications:** Stay updated with what’s happening in your team through notifications. Teamly generates in-app notifications for key activities – for example, when you’re assigned to a new task, invited to join a team, or when a team event is coming up. Using WebSocket technology, the backend can push real-time updates to connected clients, so notifications and data changes (like task status updates) can appear instantly for all team members.  

- **Google Calendar Integration:** To make scheduling even more convenient, Teamly syncs with Google Calendar. Users can connect their Google account, and Teamly will automatically create a dedicated calendar for their team events. Project events get synced to your Google Calendar, so you can view team meetings or deadlines alongside your personal schedule. This integration ensures that everyone can keep track of project events without manually duplicating them on external calendars.  

- **Email Invitations & User Profiles:** Inviting new team members is simple – just add their email and Teamly sends a branded invitation email. New users can sign up through the invite link and immediately join the correct team with a predefined role. Every user also has a profile with a customizable avatar and personal details (first/last name, email, etc.), giving the app a personal touch.  

## Tech Stack

Teamly’s backend is built with a focus on performance, security, and scalability:

- **FastAPI (Python)** – Implements a high-performance RESTful API with Python 3. FastAPI provides automatic interactive API docs and asynchronous capabilities for handling many requests efficiently.  
- **SQLModel & SQLAlchemy** – Defines the data models and ORM for the database. SQLModel (built on SQLAlchemy and Pydantic) makes it easy to define tables like Users, Teams, Tasks, Events, etc., and interact with a PostgreSQL database. The project uses Alembic for database migrations, ensuring the schema stays version-controlled and easy to upgrade.  
- **Authentication & Security** – Uses OAuth2 with **JWT (JSON Web Tokens)** for authentication. Passwords are hashed for security, and the API endpoints are protected so only authorized users can access their team’s data. Role-based access control is in place both at the user level (admin/member) and team level (owner/editor/viewer roles) to enforce permissions. CORS is enabled to allow a separate frontend (e.g., a React app) to interact with the API securely.  
- **Real-time Communication** – Incorporates **WebSocket** support for live updates. The server manages WebSocket connections per user to send real-time notifications or updates (for example, notifying team members instantly about a new task or an updated event). This keeps the user experience dynamic and in sync without needing to constantly refresh.  
- **External Integrations** – Integrates with external services to enhance functionality. For example, it uses the **Google Calendar API** (via a Google service account) to create and sync events on users’ Google Calendars. It also uses SMTP (via Gmail) to send out invite emails to new team members. Environment variables are used to securely store API keys, secrets, and credentials (like Google service account credentials, email server credentials, JWT secret keys, etc.).  
- **Task Scheduling** – Utilizes APScheduler for background jobs. A scheduled job runs periodically to clean up old notifications from the database, showcasing how to manage maintenance tasks in a long-running application.  

## Getting Started

If you’d like to run Teamly’s backend locally or inspect it further, follow these steps:

1. **Clone the repository:**  
   ```bash
   git clone https://github.com/samypt/productivity-app-backend.git
   cd productivity-app-backend
   ```  

2. **Install dependencies:** Make sure you have Python 3.10+ installed. Install the required packages using pip:  
   ```bash
   pip install -r requirements.txt
   ```  

3. **Set up environment variables:** Teamly requires certain environment variables to run. Create a `.env` file (or set environment variables) with the necessary configuration. At minimum you should provide:  
   - `DATABASE_URL` – connection string for the PostgreSQL database (for example, from a local Postgres or use SQLite for testing).  
   - `SECRET_KEY` and `ALGORITHM` – for JWT token signing (you can generate a random secret for development).  
   - `EMAIL` and `EMAIL_PASSKEY` – SMTP credentials for sending emails (optional if invite emails are not needed in dev).  
   - `GOOGLE_CREDENTIALS_PATH` – path to a Google service account JSON key file for calendar sync (optional, only needed if testing Google Calendar integration).  

4. **Apply database migrations:** The project uses Alembic for migrations. Run the migrations to set up the database schema:  
   ```bash
   alembic upgrade head
   ```  
   (Ensure your `DATABASE_URL` is set and the database is accessible before running this.)  

5. **Start the server:** Launch the FastAPI server using Uvicorn:  
   ```bash
   uvicorn app.main:app --reload
   ```  
   This will start the backend at `http://127.0.0.1:8000/` by default. You can visit `http://127.0.0.1:8000/docs` to view the interactive API documentation automatically generated by FastAPI, which lists all Teamly API endpoints for tasks, events, teams, etc.  

Teamly’s goal is to **empower teams** to work together efficiently, and this portfolio project demonstrates how such a complex application can be engineered from the ground up. 🎉 Feel free to explore, use it as a reference, or even contribute to its development. Happy collaborating!


