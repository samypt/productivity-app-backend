from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session
import os

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create the database engine
engine = create_engine(DATABASE_URL, echo=True)

# Function to get a database session
async def get_session():
    session = Session(engine, autoflush=False, autocommit=False)
    try:
        yield session
    finally:
        session.close()


# Function to create tables
def init_db():
    SQLModel.metadata.create_all(engine)