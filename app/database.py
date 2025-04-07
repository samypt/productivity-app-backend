from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session
import os

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create the database engine
engine = create_engine(DATABASE_URL, echo=True)

# Function to get a database session
def get_session():
    with Session(engine) as session:
        yield session


# Function to create tables
def init_db():
    SQLModel.metadata.create_all(engine)