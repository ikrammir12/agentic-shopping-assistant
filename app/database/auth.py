#Get connection

from .connection import get_connection
from contextlib import closing

def create_users_table():

    with closing(get_connection()) as conn:
        cursor = conn.cursor()

        #Writing the code to create the table 

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
        user_id TEXT PRIMARY KEY NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP )""")


        conn.commit()



#Function to insert the users into users table

def create_user(user_id:str,email:str,password_hash:str):
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        #Here we used parametrized sql , Beause they seperate the sql 
        #from user provided values so then we prevent the sql injections 
        cursor.execute("""
        INSERT INTO users
        (user_id,email,password_hash) VALUES(?,?,?)""",(user_id,email,password_hash)) #Values outside the called paramert bindings
        

        conn.commit()



#function to retrived the user by email


def get_user_by_email(email: str):

    with closing(get_connection()) as conn:

        user = conn.execute(
            """
            SELECT user_id, email, password_hash, is_active
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        # Check whether user exists
        if user is None:
            return None

        # Convert SQLite Row into dictionary
        return dict(user)


def get_user_by_id(user_id: str):
    with closing(get_connection()) as conn:

        user = conn.execute("""
            SELECT user_id, email, is_active
            FROM users
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        if user is None:
            return None

        return dict(user)