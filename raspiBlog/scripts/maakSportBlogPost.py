from raspiBlogLib import * # Importeer alle functies uit raspiBlogLib

# Laad omgevingsvariabelen uit .env bestand
load_dotenv()

database = os.getenv("PGDB_NAME")
username = os.getenv("PGDB_USER")
password = os.getenv("PGDB_PASSWORD")
host = os.getenv("PGDB_HOST")
port = os.getenv("PGDB_PORT", 5432)

def update_run_status(run_id, AI_provider, action):
    now = datetime.now()  # Correcte manier om de huidige tijd op te halen

    try:
        # Maak een databaseverbinding
        with connect(database=database, user=username, password=password, host=host, port=port) as conn:
            with conn.cursor() as cursor:
                # Eerste update statement (voor rb_runs)
                cursor.execute("""
                    UPDATE rb_runs
                    SET status = 'C', ai_provider = %s, end_datetime = %s, action = %s 
                    WHERE id = %s
                """, (AI_provider, now, action, run_id))

                # Tweede update statement
                cursor.execute("""
                    UPDATE rb_articles
                    SET status = 'V' 
                    WHERE id IN (
                        SELECT id from rb_v_sport_articles
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
                    SELECT title as label, url, text as summary
                    FROM rb_v_sport_articles
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
    start_datetime = datetime.now()
    runid = add_new_row_rb_runs(start_datetime,'M', Path(sys.argv[0]).stem)

    # Bestandsnamen
    files_to_delete = [DALLE3_PROMPT, BLOG_FILE, SUMMARIES_FILE]

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
    
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_API_URL)
    try:
       AI_provider = 'DeepSeek'
       print(AI_provider)
       print(f" use DEEPSEEK_MODEL: {DEEPSEEK_MODEL} with base_url {DEEPSEEK_API_URL}")
       blog_content = generate_blog_content(client, summaries, DEEPSEEK_MODEL)
       print(f"blog_content:{blog_content}")
       ai_prompt = maak_DALLE3_PROMPT(client, blog_content, DEEPSEEK_MODEL)
       print(f"DEEPSEEK ai_prompt: {ai_prompt}")
       with open(DALLE3_PROMPT, 'w', encoding='utf-8') as file:
         file.write(ai_prompt)
    except Exception as e:
       AI_provider = 'OpenAI'
       print(AI_provider)
       print(f"Error using DEEPSEEK: {e}")
       print(f"DEEPSEEK failed so use OPENAI_MODEL: {OPENAI_MODEL}")
       client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_URL)
       blog_content = generate_blog_content(client, summaries, OPENAI_MODEL)
       ai_prompt = maak_DALLE3_PROMPT(client, blog_content, OPENAI_MODEL)
       print(f"OPENAI ai_prompt: {ai_prompt}")
       with open(DALLE3_PROMPT, 'w', encoding='utf-8') as file:
         file.write(ai_prompt)

    # ga hier verder
    with open(BLOG_FILE, 'w', encoding='utf-8') as file:
        file.write(blog_content)

    print(f"Blog content is geschreven naar '{BLOG_FILE}'")
    update_run_status(runid, AI_provider, Path(sys.argv[0]).stem)

if __name__ == "__main__":
    main()
