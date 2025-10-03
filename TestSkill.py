import sqlite3
import json

# Path to your SQLite database
DB_PATH = 'storage/configs/ValueData.db'
# Output JSON file
OUTPUT_JSON = 'ValueData.json'

def fetch_database_data(db_path):
    data = {}
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table_name_tuple in tables:
        table_name = table_name_tuple[0]
        table_data = []

        # Get all rows for this table
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        # Get column names
        column_names = [description[0] for description in cursor.description]

        # Combine rows with column names
        for row in rows:
            row_dict = dict(zip(column_names, row))
            table_data.append(row_dict)

        # Store in final data
        data[table_name] = table_data

    conn.close()
    return data

def save_to_json(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    db_data = fetch_database_data(DB_PATH)
    save_to_json(db_data, OUTPUT_JSON)
    print(f"Database dumped successfully to {OUTPUT_JSON}")