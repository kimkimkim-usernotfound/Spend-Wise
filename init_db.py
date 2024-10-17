import sqlite3

# Connect to the database (it will create it if it doesn't exist)
connection = sqlite3.connect('database.db')

# Check if the schema.sql file exists before trying to read it
try:
    # Read the schema file and execute the commands
    with open('schema.sql', 'r') as f:
        connection.executescript(f.read())

    cur = connection.cursor()

    # Insert sample posts with image URL (set to None or a default image path if no image is available)
    # You can customize these values as needed.
    cur.execute("INSERT INTO posts (title, content, image_url) VALUES (?, ?, ?)",
                ('First Post', 'Content for the first post', None)
                )
    cur.execute("INSERT INTO posts (title, content, image_url) VALUES (?, ?, ?)",
                ('Second Post', 'Content for the second post', None)
                )

    # Insert a sample user (please hash the password in a production scenario)
    cur.execute("INSERT INTO users (email, password) VALUES (?, ?)",
                ('example@example.com', 'hashed_password_here')  # Use actual hashed password ideally
                )

    # Commit the changes and close the connection
    connection.commit()
    
    print("Database initialized and sample data inserted successfully.")

except FileNotFoundError:
    print("Error: The schema.sql file was not found.")
except sqlite3.Error as e:
    print(f"SQLite error occurred: {e}")
finally:
    connection.close()