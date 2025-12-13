# Import the engine and Base from our existing database and model files.
# The engine is our connection, and Base knows about all the tables we defined.
from database.connection import engine, Base
from database import models # Import models to ensure they are registered with Base

def reset_database():
    """
    Wipes all existing tables and data, then rebuilds the entire schema.
    """
    print("--- ⚠️  WARNING: This will delete all data in your database. ---")
    # A simple confirmation step to prevent accidental deletion.
    confirm = input("Are you sure you want to continue? (yes/no): ")

    if confirm.lower() != 'yes':
        print("Database reset cancelled.")
        return

    try:
        print("\nStep 1: Dropping all existing tables...")
        # This command connects to the database and issues DROP TABLE commands
        # for all tables associated with our Base metadata.
        Base.metadata.drop_all(bind=engine)
        print("✅ Tables dropped successfully.")

        print("\nStep 2: Creating all tables from scratch...")
        # Now, this command issues CREATE TABLE commands for all our models.
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully.")

        print("\n✨ Database has been reset successfully! ✨")

    except Exception as e:
        print(f"❌ An error occurred during the database reset: {e}")


if __name__ == "__main__":
    reset_database()