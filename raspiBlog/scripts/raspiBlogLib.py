from PIL import Image
from bs4 import BeautifulSoup
from datetime import datetime
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path
from pgdbActions import *  # Importeer alle functies uit pgdbActions
from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from psycopg2.sql import SQL, Identifier
from urllib.parse import urljoin
import base64
import json
import locale
import markdown
import os
import random
import re
import requests
import subprocess
import sys
import time
import base64

# Laad omgevingsvariabelen uit .env bestand
load_dotenv()

WORDPRESS_USER = os.getenv('WORDPRESS_USER')
WORDPRESS_APP_PASSWORD = os.getenv('WORDPRESS_APP_PASSWORD')
# WP users
WPQWEN_USER = os.getenv('WPQWEN_USER')
WPQWEN_APP_PASSWORD = os.getenv('WPQWEN_APP_PASSWORD')
WPDEEPSEEK_USER = os.getenv('WPDEEPSEEK_USER')
WPDEEPSEEK_APP_PASSWORD = os.getenv('WPDEEPSEEK_APP_PASSWORD')
WPOPENROUTER_USER = os.getenv('WPOPENROUTER_USER')
WPOPENROUTER_APP_PASSWORD = os.getenv('WPOPENROUTER_APP_PASSWORD')
WPOPENAI_USER = os.getenv('WPOPENAI_USER')
WPOPENAI_APP_PASSWORD = os.getenv('WPOPENAI_APP_PASSWORD')
WP_BASE = os.getenv('WP_BASE')
BLOG_FILE = os.getenv('BLOG_FILE', '/app/blog_post.txt')
BLOG_IMG = os.getenv('BLOG_IMG', '/app/temp_image.png')
SUMMARIES_FILE = os.getenv('SUMMARIES_FILE', '/app/summaries.txt')
DALLE3_PROMPT = os.getenv('DALLE3_PROMPT', '/app/dall-e_3_prompt.txt')
# openai
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_URL = os.getenv('OPENAI_API_URL')
OPENAI_MODEL = os.getenv('OPENAI_MODEL')
#deepseek
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL')
# Qwen
QWEN_API_KEY = os.getenv('QWEN_API_KEY')
QWEN_API_URL = os.getenv('QWEN_API_URL')
QWEN_MODEL = os.getenv('QWEN_MODEL')
# OpenRouter
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_API_URL = os.getenv('OPENROUTER_API_URL')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL')

# Forge API URL
FORGE_API_URL = os.getenv('FORGE_API_URL')
database = os.getenv("PGDB_NAME")
username = os.getenv("PGDB_USER")
password = os.getenv("PGDB_PASSWORD")
host = os.getenv("PGDB_HOST")
port = os.getenv("PGDB_PORT", 5432)

# In-memory rij
article_row = {
    "run_id": None,
    "full_url": None,
    "topic": None,
    "summary": None,
    "text": None,
    "pub_date": None,
    "title": None,
    "supply_channel": None
}

# Functies om rij te vullen
def set_run_id(row, run_id):
    row["run_id"] = run_id

def set_full_url(row, full_url):
    row["full_url"] = full_url

def set_topic(row, topic):
    row["topic"] = topic

def set_summary(row, summary):
    row["summary"] = summary

def set_text(row, text):
    row["text"] = text

def set_pub_date(row, pub_date):
    row["pub_date"] = pub_date

def set_title(row, title):
    row["title"] = title

def set_supply_channel(row, supply_channel):
    row["supply_channel"] = supply_channel

# article_row leegmaken
def clear_article_row(row):
    row["run_id"] = None
    row["full_url"] = None
    row["topic"] = None
    row["summary"] = None
    row["text"] = None
    row["pub_date"] = None
    row["title"] = None
    row["supply_channel"] = None

def maak_DALLE3_PROMPT(client, blog_text, model):
    # Formuleer de opdracht voor de AI
    instruction = (
      "Maak een gedetailleerde Stable Diffusion prompt in het Engels gebaseerd op de volgende tekst. "
      "Begin de prompt ALTIJD met de tekst:Create a highly detailed, digital painting of "
      "Kies 1 van de onderwerpen en zorg dat de prompt een plaatje genereert wat de strekking van artikel weerspiegelt. "
      "/genereer zo min mogelijk tekst op het gegeneerde plaatje ndien noodzakelijk dan zoveel mogelijk Nederlandstalig."
      "Lever uitsluitend de gegenereerde prompt aan, zonder verdere uitleg of extra tekst. Tekst:\n"
      f"{blog_text}"
    )

    # Vraag de AI om de prompt te genereren
    response = client.chat.completions.create(
      model= model,
      messages=[
        {"role": "system", "content": "Je bent een deskundige assistent die gedetailleerde prompts voor DALL-E3 genereert."},
        {"role": "user", "content": instruction}
      ]
    )

    # Retourneer de gegenereerde prompt
    prompt = response.choices[0].message.content
    return prompt

def read_summaries(file_path):
    summaries = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        current_label, url, summary = None, None, None
        for line in lines:
            if line.startswith("Label: "):
                if current_label and url and summary:
                    if current_label not in summaries:
                        summaries[current_label] = []
                    summaries[current_label].append((url, summary))
                current_label = line.split("Label: ")[1].strip()
                url, summary = None, None
            elif line.startswith("URL: "):
                url = line.split("URL: ")[1].strip()
            elif line.startswith("Samenvatting: "):
                summary = line.split("Samenvatting: ")[1].strip()
            elif line.strip() == "":
                continue
            else:
                if summary:
                    summary += " " + line.strip()
                else:
                    summary = line.strip()
        if current_label and url and summary:
            if current_label not in summaries:
                summaries[current_label] = []
            summaries[current_label].append((url, summary))
    return summaries

def generate_blog_content(client, summaries, model):
    print(f">>>>>>>>>>>>>>>>>>>>> model:{model}")
    blog_content = ""
    for topic, articles in summaries.items():
        print(f" articles:{articles}\n")
        #blog_content += generate_blog_content_per_topic(topic, articles, client, model) + "\n"
        blog_content += generate_blog_content_per_topic(topic, articles, client, model) + "\n"
    return blog_content

def generate_blog_content_per_topic(topic, articles, client, model):
    # Haal de huidige datum op
    today = datetime.today().strftime('%d %B %Y')
    
    prompt = f"Maak een blogpost op basis van de volgende samenvattingen voor het onderwerp '{topic}'. Voeg headers en opmaak toe,\n"
    prompt += "maar verzin geen extra inhoud. Voeg onderaan elk artikel een 'Bekijk origineel artikel'-link toe in HTML, zodat de link opent in een nieuwe tab.\n"
    prompt += "Herschrijf de samenvatting naar een informele stijl. Zorg ervoor dat er geen plagiaat veroorzaakt wordt.Als je een datum wil gebruiken,\n"
    prompt += "zorg er dan voor dat alle relatieve datums (zoals 'gisteren', 'eergisteren', 'volgende week', etc.) NIET worden omgezet naar absolute datums.\n"
    prompt += "Herschrijf {topic} in eigen woorden, zodat het bij het artikel past. Het herschreven topic moet wel Nederlandstalig zijn. Gebruik de volgende structuur:\n"
    prompt += f"\n## Onderwerp van artikel\n"

    for url, summary in articles:
        prompt += f"{summary}\n\n<a href=\"{url}\" target=\"_blank\">Bekijk origineel artikel</a>\n\n"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Je bent een behulpzame assistent die relatieve datums altijd omzet naar absolute datums gerelateerd aan de huidige datum."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Er is een fout opgetreden bij het genereren van blog_content: {e}")

def update_run_status(run_id, AI_provider, status):
    now = datetime.now()  # Correcte manier om de huidige tijd op te halen

    try:
        # Maak een databaseverbinding
        with connect(database=database, user=username, password=password, host=host, port=port) as conn:
            with conn.cursor() as cursor:
                # Eerste update statement (voor rb_runs)
                cursor.execute("""
                    UPDATE rb_runs
                    SET status = %s, ai_provider = %s, end_datetime = %s
                    WHERE id = %s
                """, (status, AI_provider, now, run_id))

                # Commit veranderingen
                conn.commit()
                print("Statussen zijn succesvol bijgewerkt.")
    except Exception as e:
        print(f"Er is een fout opgetreden bij het bijwerken van de run-status: {e}")
        sys.exit(1)
import random

def maak_blogPost(summaries):
    # Providers en hun API-gegevens
    client_providers = {
        "DeepSeek": (DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL),
        "Qwen": (QWEN_API_KEY, QWEN_API_URL, QWEN_MODEL),
        "OpenRouter": (OPENROUTER_API_KEY, OPENROUTER_API_URL, OPENROUTER_MODEL),
        "OpenAI": (OPENAI_API_KEY, OPENAI_API_URL, OPENAI_MODEL)
    }
    
    # Random kiezen tussen DeepSeek en Qwen
    primary_providers = ["DeepSeek", "Qwen","OpenRouter"]
    #primary_providers = ["OpenRouter","OpenRouter"]
    random.shuffle(primary_providers)

    blog_content = None  # Initialiseer als None
    AI_provider = None   # Initialiseer als None voor het geval alle providers falen

    for provider in primary_providers:
        api_key, base_url, model = client_providers[provider]
        try:
            AI_provider = provider
            print(f"Using {provider} ({model}) with base_url {base_url}")

            client = OpenAI(api_key=api_key, base_url=base_url)
            blog_content = generate_blog_content(client, summaries, model)
            print(f"blog_content: {blog_content}")

            ai_prompt = maak_DALLE3_PROMPT(client, blog_content, model)
            print(f"{provider} ai_prompt: {ai_prompt}")

            with open(DALLE3_PROMPT, 'w', encoding='utf-8') as file:
                file.write(ai_prompt)

            break  # Stop als een provider succesvol is
        except Exception as e:
            print(f"Error using {provider}: {e}")
            print(f"{provider} failed, trying the next provider...")
    
    # Als beide primary providers falen, probeer OpenAI
    if blog_content is None:
        try:
            AI_provider = "OpenAI"
            api_key, base_url, model = client_providers[AI_provider]
            print(f"Using OpenAI ({model}) with base_url {base_url}")

            client = OpenAI(api_key=api_key, base_url=base_url)
            blog_content = generate_blog_content(client, summaries, model)
            print(f"blog_content: {blog_content}")

            ai_prompt = maak_DALLE3_PROMPT(client, blog_content, model)
            print(f"OpenAI ai_prompt: {ai_prompt}")

            with open(DALLE3_PROMPT, 'w', encoding='utf-8') as file:
                file.write(ai_prompt)
        except Exception as e:
            print(f"Error using OpenAI: {e}")
            print("All providers failed.")

    return blog_content, AI_provider

def OUDmaak_blogPost(summaries):
    # Volgorde voor het genereren van blogPost: Eerst Deepseek, als dat niet luke Qwen en als dat ook niet lukt OpenAI
    #
    client_providers = [
        ("DeepSeek", DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL),
        ("Qwen", QWEN_API_KEY, QWEN_API_URL, QWEN_MODEL),
        ("OpenAI", OPENAI_API_KEY, OPENAI_API_URL, OPENAI_MODEL)
    ]

    blog_content = None  # Initialiseer als None
    AI_provider = None   # Initialiseer als None voor het geval alle providers falen

    for provider, api_key, base_url, model in client_providers:
        try:
            AI_provider = provider
            print(AI_provider)
            print(f"Using {model} with base_url {base_url}")
            
            client = OpenAI(api_key=api_key, base_url=base_url)
            blog_content = generate_blog_content(client, summaries, model)
            print(f"blog_content: {blog_content}")

            ai_prompt = maak_DALLE3_PROMPT(client, blog_content, model)
            print(f"{provider} ai_prompt: {ai_prompt}")

            with open(DALLE3_PROMPT, 'w', encoding='utf-8') as file:
                file.write(ai_prompt)

            break  # Stop de loop als een provider succesvol is
        except Exception as e:
            print(f"Error using {provider}: {e}")
            print(f"{provider} failed, trying the next provider...")

    return blog_content, AI_provider  # Enkel één return met een tuple (blog_content, AI_provider)

def generate_summaries(view_name):
    try:
        with connect(database=database, user=username, password=password, host=host, port=port, options="-c search_path=public") as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = f"SELECT id, label, url, summary FROM public.{view_name};"
                cursor.execute(query)
                rows = cursor.fetchall()

                # Verwerking van de resultaten
                ids = []
                with open(SUMMARIES_FILE, 'w', encoding='utf-8') as file:
                    for row in rows:
                        url = row['url']
                        if '112-nieuws' in url:
                            print(f"URL met '112-nieuws' overgeslagen: {url}")
                            continue

                        ids.append(str(row['id']))  #  Zorg dat ID's als string worden opgeslagen
                        file.write(f"Label: {row['label']}\n")
                        file.write(f"URL: {url}\n")
                        file.write(f"Samenvatting: {row['summary']}\n\n")

                print(f"Samenvattingen geschreven naar {SUMMARIES_FILE}.")
                print(f"IDs die worden bijgewerkt: {ids}")  #  Debugging

                # Status bijwerken als er ID's zijn
                if ids:
                    # Check of het een INTEGER of UUID is
                    cursor.execute(
                        "SELECT data_type FROM information_schema.columns WHERE table_name = 'rb_articles' AND column_name = 'id';"
                    )
                    id_type = cursor.fetchone()['data_type']

                    if id_type == "integer":
                        cursor.execute(
                            "UPDATE rb_articles SET status = 'V' WHERE id = ANY(%s::INTEGER[]);",
                            (list(map(int, ids)),)  #  Zet om naar INTEGER
                        )
                    else:  # UUID of andere string-based ID
                        cursor.execute(
                            "UPDATE rb_articles SET status = 'V' WHERE id = ANY(%s::UUID[]);",
                            (ids,)  #  Lijst blijft strings
                        )

                    conn.commit()
                    print(f"Status bijgewerkt voor {len(ids)} artikelen.")
                else:
                    print("Geen artikelen om bij te werken.")

    except Exception as e:
        print(f" Fout bij het ophalen van artikelen uit 'public.{view_name}': {e}")

def upload_image_to_wordpress(filename):
    auth = base64.b64encode(f"{WORDPRESS_USER}:{WORDPRESS_APP_PASSWORD}".encode()).decode()
    media_url = f"{WP_BASE}/wp-json/wp/v2/media"

    # Zorg ervoor dat alleen de bestandsnaam in de header staat
    file_name_only = os.path.basename(filename)

    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Disposition": f'attachment; filename="{filename}"'
    }

    try:
        with open(filename, 'rb') as file:
            media_response = requests.post(media_url, headers=headers, files={'file': file})

        # Print het volledige response voor debugging
        #print(f"Response status: {media_response.status_code}")
        #print(f"Response body: {media_response.text}")

        # Controleer of de upload gelukt is
        if media_response.status_code != 201:
            raise Exception(f"Error uploading image: {media_response.status_code}, {media_response.text}")

        # Haal de media ID op en geef het terug
        media_id = media_response.json().get("id")
        if not media_id:
            raise Exception("Upload gelukt, maar geen 'id' ontvangen in het antwoord.")

        print(f"Afbeelding succesvol geüpload. Media ID: {media_id}")
        return media_id

    except Exception as e:
        print(f"Fout bij uploaden afbeelding 2: {e}")
        return None  # Hiermee voorkom je dat de functie crasht


