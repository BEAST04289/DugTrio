# This script is a one-time utility to initialize our database tables.
from database.connection import create_all_tables

if __name__ == "__main__":
    # This line ensures the code runs only when you execute this file directly.
    # It calls the function from database.py to create the tables.
    create_all_tables()