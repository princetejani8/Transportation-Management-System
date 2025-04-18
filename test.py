import mysql.connector

# Connect to MySQL (adjust your credentials if needed)
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # Use your password if set
    database="tms"
)
cursor = conn.cursor()

# Add 'status' column to staff and vehicle tables if not already present
alter_queries = [
    """
    ALTER TABLE staff 
    ADD COLUMN status ENUM('active', 'archived') DEFAULT 'active';
    """,
    """
    ALTER TABLE vehicle 
    ADD COLUMN status ENUM('active', 'archived') DEFAULT 'active';
    """
]

# Execute each query and handle if already exists
results = []
for query in alter_queries:
    try:
        cursor.execute(query)
        results.append("✅ Success: " + query.split('\n')[1].strip())
    except mysql.connector.Error as err:
        results.append(f"⚠️ Skipped: {err.msg}")

conn.commit()
cursor.close()
conn.close()

results
