import requests
from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from getNieuwsLib import * # Importeer alle functies uit getNieuwsLib

# Laad omgevingsvariabelen uit .env bestand
load_dotenv()

database = os.getenv("PGDB_NAME")
username = os.getenv("PGDB_USER")
password = os.getenv("PGDB_PASSWORD")
host = os.getenv("PGDB_HOST")
port = os.getenv("PGDB_PORT", 5432)

def update_run_status():
    try:
        with connect(database=database, user=username, password=password, host=host, port=port) as conn:
            with conn.cursor() as cursor:
                # Eerste update statement
                cursor.execute("""
                    UPDATE rb_runs r
                    SET status = 'C'
                    WHERE r.id IN (
                        SELECT run_id from rb_v_recent_articles
                    );
                """)

                # Tweede update statement
                cursor.execute("""
                    UPDATE rb_articles
                    SET status = 'V' 
                    WHERE id IN (
                        SELECT id from rb_v_recent_articles
                    );
                """)

                # Commit beide veranderingen
                conn.commit()
                print("Statussen zijn succesvol bijgewerkt.")
    except Exception as e:
        print(f"Er is een fout opgetreden bij het bijwerken van de run-status: {e}")
        sys.exit(1)

def generate_summaries():
    try:
        with connect(database=database, user=username, password=password, host=host, port=port) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT topic as label, url, text as summary
                    FROM rb_v_recent_articles
                    ORDER by RANDOM()
                    LIMIT 6;
                    """
                )
                rows = cursor.fetchall()

                with open(SUMMARIES_FILE, 'w', encoding='utf-8') as file:
                    for row in rows:
                        url = row['url']
                        if '112-nieuws' in url:
                            print(f"URL met '112-nieuws' overgeslagen: {url}")
                            continue
                        label = row['label']
                        summary = row['summary']
                        file.write(f"Label: {label}\n")
                        file.write(f"URL: {url}\n")
                        file.write(f"Samenvatting: {summary}\n\n")

                print(f"Samenvattingen zijn geschreven naar {SUMMARIES_FILE}.")
    except Exception as e:
        print(f"Er is een fout opgetreden bij het genereren van de samenvattingen: {e}")

def main():
    # Bestandsnamen
    files_to_delete = [DALLE3_PROMPT, BLOG_FILE]

    # Verwijder de bestanden
    for file in files_to_delete:
       if os.path.exists(file):
           os.remove(file)
           print(f"{file} is verwijderd.")
       else:
           print(f"{file} bestaat niet.")
    #  
    generate_summaries()
    summaries = read_summaries(SUMMARIES_FILE)
    client = OpenAI(api_key=OPENAI_API_KEY)
    blog_content = generate_blog_content(client, summaries)
    ai_prompt = maak_DALLE3_PROMPT(client, blog_content)
    print(f"ai_prompt: {ai_prompt}")
    with open(DALLE3_PROMPT, 'w', encoding='utf-8') as file:
      file.write(ai_prompt) 

    with open(BLOG_FILE, 'w', encoding='utf-8') as file:
        file.write(blog_content)
    
    print(f"Blog content is geschreven naar '{BLOG_FILE}'")
    update_run_status()

if __name__ == "__main__":
    main()
