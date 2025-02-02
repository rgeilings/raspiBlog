import os
from dotenv import load_dotenv
from psycopg2 import connect
from datetime import datetime
from psycopg2.extras import RealDictCursor 

load_dotenv()

# Definieer de databaseconnectie en de variabelen die uit het .env file zijn gelezen
database = os.getenv("PGDB_NAME")
username = os.getenv("PGDB_USER")
password = os.getenv("PGDB_PASSWORD")
host = os.getenv("PGDB_HOST")
port = os.getenv("PGDB_PORT", 5432)  # Voeg een default waarde toe als de poort niet is ingesteld

# Definieer de connectie met de database
try:
    conn = connect(database=database, user=username, password=password, host=host, port=port)
except Exception as e:
    print(f"Error connecting to the database: {e}")
    exit(1)

# Maak een cursor om te communiceren met de database
cur = conn.cursor()

# Voeg een nieuwe rij toe aan de tabel rb_runs
def add_new_row(start_datetime,type):
    cur.execute("INSERT INTO rb_runs (start_datetime, status, type) VALUES (%s, %s, %s) RETURNING id", (start_datetime, 'S', type))
    new_id = cur.fetchone()[0]  # Gebruik tuple index in plaats van dictionary key
    conn.commit()
    return new_id

def add_new_row_rb_runs(start_datetime,type, action):
    cur.execute("INSERT INTO rb_runs (start_datetime, status, type, action) VALUES (%s, %s, %s, %s) RETURNING id", (start_datetime, 'S', type, action))
    new_id = cur.fetchone()[0]  # Gebruik tuple index in plaats van dictionary key
    conn.commit()
    return new_id

# Update een bestaande rij in de tabel rb_runs
def update_row_rb_runs(id, end_datetime, status, action, ai_provider):
    cur.execute("UPDATE rb_runs SET end_datetime = %s, status = %s, action = %s, ai_provider = %s WHERE id = %s", (end_datetime, status, id))
    conn.commit()

def update_row(id, end_datetime, status):
    cur.execute("UPDATE rb_runs SET end_datetime = %s, status = %s WHERE id = %s", (end_datetime, status, id))
    conn.commit()

# Maak een nieuwe trend aan en voeg deze toe aan de tabel rb_trends
def add_new_trend(run_id, trend_text):
    cur.execute("INSERT INTO rb_trends (run_id, trend_text) VALUES (%s, %s)", (run_id, trend_text))
    conn.commit()

# Update een bestaande trend in de tabel rb_trends
def update_trend(id, run_id, trend_text):
    cur.execute("UPDATE rb_trends SET run_id = %s, trend_text = %s WHERE id = %s", (run_id, trend_text, id))
    conn.commit()

# Haal de eerste X trend_id en trend_text rijen op uit de rb_trends tabel
def get_first_trends(run_id):
    cur.execute("SELECT id, trend_text FROM rb_trends WHERE run_id = %s LIMIT 10", (run_id,))
    rows = cur.fetchall()
    return rows  # Return tuples (trend_id, trend_text)

# Voeg een nieuwe rij toe aan de tabel rb_articles en geef de gegenereerde id terug
def insert_article(row):
    try:
        cur.execute("""
            INSERT INTO rb_articles (run_id, url, topic, summary, text, pub_date, title, supply_channel)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (row["run_id"], row["full_url"], row["topic"], row["summary"], row["text"], row["pub_date"] , row["title"], row["supply_channel"]))
        row_id = cur.fetchone()[0]
        conn.commit()
        return row_id
    except Exception as e:
        print(f"Error inserting article: {e}")
        conn.rollback()
        return None
        
# Controleer of een URL al in de database bestaat
def url_exists(url):
    cur.execute("SELECT 1 FROM rb_articles WHERE url = %s", (url,))
    return cur.fetchone() is not None

# Update een bestaand artikel in de tabel rb_articles
def update_article(id, run_id, url, topic, summary, text):
    cur.execute("UPDATE rb_articles SET run_id = %s, url = %s, topic = %s, summary = %s, text = %s WHERE id = %s", (run_id, url, topic, summary, text, id))
    conn.commit()

# Haal de article text op voor een bepaald id
def get_article_text_by_id(id):
    try:
        with connect(database=database, user=username, password=password, host=host, port=port) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                SELECT text
                FROM rb_articles 
                WHERE text IS NOT NULL
                  AND id = %s;
                """
                cursor.execute(query, (id,))
                results = cursor.fetchall()
                return results
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Haal de samenvattingen op voor een bepaalde run_id
def get_summaries_by_run_id(run_id):
    try:
        with connect(database=database, user=username, password=password, host=host, port=port) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                SELECT t.trend_text, a.summary 
                FROM rb_articles a
                JOIN rb_trends t ON t.id = a.run_id
                JOIN rb_runs r ON t.run_id = r.id
                WHERE a.summary IS NOT NULL
                  AND r.id = %s;
                """
                cursor.execute(query, (run_id,))
                results = cursor.fetchall()
                return results
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_trending_articles(where_clause):
    # Definieer de SQL-query met de variabele WHERE-clausule
    try:
        with connect(database=database, user=username, password=password, host=host, port=port) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = f"""
                select trend_text, text 
                from rb_v_trending_articles {where_clause};
                """
                cursor.execute(query)
                results = cursor.fetchall()
                return results
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_trending_summaries(where_clause):
    # Definieer de SQL-query met de variabele WHERE-clausule
    try:
        with connect(database=database, user=username, password=password, host=host, port=port) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = f"""
                select trend_text, summary
                from rb_v_trending_summaries {where_clause};
                """
                cursor.execute(query)
                results = cursor.fetchall()
                return results
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
