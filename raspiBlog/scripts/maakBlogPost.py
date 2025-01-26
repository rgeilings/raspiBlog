import requests
from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from getNieuwsLib import * # Importeer alle functies uit getNieuwsLib
import sys

# Laad omgevingsvariabelen uit .env bestand
load_dotenv()

database = os.getenv("PGDB_NAME")
username = os.getenv("PGDB_USER")
password = os.getenv("PGDB_PASSWORD")
host = os.getenv("PGDB_HOST")
port = os.getenv("PGDB_PORT", 5432)

def fetch_latest_run_id():
    try:
        with connect(database=database, user=username, password=password, host=host, port=port) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT MAX(id)
                    FROM rb_runs
                    WHERE type = 'C' AND status = 'S';
                """)
                result = cursor.fetchone()
                if result and result[0]:
                    return result[0]
                else:
                    print("Geen geldig run_id gevonden in de database.")
                    sys.exit(1)
    except Exception as e:
        print(f"Er is een fout opgetreden bij het ophalen van het run_id: {e}")
        sys.exit(1)

def update_run_status(run_id):
    print(f"run_id: {run_id}")
    try:
        with connect(database=database, user=username, password=password, host=host, port=port) as conn:
            with conn.cursor() as cursor:
                # Eerste update statement
                cursor.execute("""
                    UPDATE rb_runs r
                    SET status = 'C'
                    WHERE id = %s
                """, (run_id,))

                # Tweede update statement
                cursor.execute("""
                    UPDATE rb_articles
                    SET status = 'C'
                    WHERE run_id = %s
                """, (run_id,))

                # Commit beide veranderingen
                conn.commit()
                print(f"Status van run_id {run_id} bijgewerkt naar 'X'.")
    except Exception as e:
        print(f"Er is een fout opgetreden bij het bijwerken van de run-status: {e}")
        sys.exit(1)

def generate_summaries(run_id):
    try:
        with connect(database=database, user=username, password=password, host=host, port=port) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    select topic as label, url,text as  summary, pub_date
                    from rb_articles
                    where summary is not null and run_id = %s
                    order by RANDOM()
                    limit 6;
                    """,
                    (run_id,)
                )
                rows = cursor.fetchall()

                with open(SUMMARIES_FILE, 'w', encoding='utf-8') as file:
                    for row in rows:
                        url = row['url']
                        if '112-nieuws' in url:
                            print(f"URL met '112-nieuws' overgeslagen: {url}")
                            continue
                        label = row['label']
                        pub_date = row['pub_date']
                        summary = row['summary']
                        file.write(f"Label: {label}\n")
                        file.write(f"PublicatieDatum: {pub_date}\n")
                        file.write(f"URL: {url}\n")
                        file.write(f"Samenvatting: {summary}\n\n")

                print(f"Samenvattingen zijn geschreven naar {SUMMARIES_FILE}.")
    except Exception as e:
        print(f"Er is een fout opgetreden bij het genereren van de samenvattingen: {e}")

def main(run_id):
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
    generate_summaries(run_id)
    summaries = read_summaries(SUMMARIES_FILE)
    client = OpenAI(api_key=OPENAI_API_KEY)
    blog_content = generate_blog_content(client, summaries)
    #blog_samenvatting = maak_blog_summary(blog_content)
    #ai_prompt = maak_DALLE3_PROMPT(client, blog_samenvatting)
    ai_prompt = maak_DALLE3_PROMPT(client, blog_content)
    print(f"ai_prompt: {ai_prompt}")
    with open(DALLE3_PROMPT, 'w', encoding='utf-8') as file:
      file.write(ai_prompt) 

    with open(BLOG_FILE, 'w', encoding='utf-8') as file:
        file.write(blog_content)
    
    print(f"Blog content is geschreven naar '{BLOG_FILE}'")
    update_run_status(run_id)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Geen run_id opgegeven, probeer op te halen uit de database.")
        run_id = fetch_latest_run_id()
    else:
        try:
            run_id = int(sys.argv[1])
        except ValueError:
            print("<run_id> must be an integer.")
            sys.exit(1)

    main(run_id)
