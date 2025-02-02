from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path
from pgdbActions import *  # Importeer alle functies uit pgdbActions
from psycopg2 import connect
from psycopg2.extras import RealDictCursor
import json
import locale
import random
import re
import requests
import sys
import time
from urllib.parse import urljoin

# Laad omgevingsvariabelen uit .env bestand
load_dotenv()

SUMMARIES_FILE = os.getenv('SUMMARIES_FILE', '/app/summaries.txt')
DALLE3_PROMPT = os.getenv('DALLE3_PROMPT', '/app/dall-e_3_prompt.txt')
BLOG_FILE = os.getenv('BLOG_FILE', '/app/blog_post.txt')
# openai
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_URL = os.getenv('OPENAI_API_URL')
OPENAI_MODEL = os.getenv('OPENAI_MODEL')
#deepseek
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL')

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
      "Maak een gedetailleerde DALLE-3 prompt gebaseerd op de volgende tekst. "
      "Combineer zoveel mogelijk unieke onderwerpen, thema's en elementen uit de tekst tot één coherente prompt. "
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
    return response.choices[0].message.content

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
    prompt = f"Maak een blogpost op basis van de volgende samenvattingen voor het onderwerp '{topic}'. Voeg headers en opmaak toe,\n"
    prompt += "maar verzin geen extra inhoud. Voeg onderaan elk artikel een 'Bekijk origineel artikel'-link toe in HTML, zodat de link opent in een nieuwe tab.\n"
    prompt += "Herschrijf de samenvatting naar een informele stijl. Zorg ervoor dat er geen plagiaat veroorzaakt wordt.\n"
    prompt += "Als je een datum wil gebruiken, gebruik dan alleen datums die expliciet zijn genoemd. Herschrijf {topic} in eigen woorden, zodat het bij het article past. \n"
    prompt += "Het herschreven topic moet wel Nederlandstalig zijn. Gebruik de volgende structuur:\n"
    prompt += f"\n## onderwerp van article\n"
    for url, summary in articles:
        #print(f"summary: {summary}\n url:{url}\n")
        prompt += f"{summary}\n\n<a href=\"{url}\" target=\"_blank\">Bekijk origineel artikel</a>\n\n"
    try:
       response = client.chat.completions.create(
           model=model,
           messages=[
               {"role": "system", "content": "Je bent een behulpzame assistent."},
               {"role": "user", "content": prompt}
           ]
       )
       #print(response)  # Debug: Bekijk de volledige response
       return response.choices[0].message.content

    except Exception as e:
        print(f"Er is een fout opgetreden bij het genereren van blog_content: {e}")


def Agenerate_blog_content_per_topic(topic, articles, client, model):
    prompt = f"Maak een blogpost op basis van de volgende samenvattingen voor het onderwerp '{topic}'. Voeg headers en opmaak toe,\n"
    prompt += "maar verzin geen extra inhoud. Voeg onderaan elk artikel een 'Bekijk origineel artikel'-link toe in HTML, zodat de link opent in een nieuwe tab.\n"
    prompt += "Herschrijf de samenvatting naar een informele stijl. Zorg ervoor dat er geen plagiaat veroorzaakt wordt.\n"
    prompt += "Als je een datum wil gebruiken, gebruik dan alleen datums die expliciet zijn genoemd. Herschrijf {topic} in eigen woorden, zodat het bij het article past. \n"
    prompt += "Het herschreven topic moet wel Nederlandstalig zijn. Gebruik de volgende structuur:\n"
    prompt += f"\n## onderwerp van article\n"
    print('for loop') 
    for url, summary in articles:
        #print(f"summary: {summary}\n url:{url}\n")
        print(f" url:{url}\n")
        #prompt += f"{summary}\n\n<a href=\"{url}\" target=\"_blank\">Bekijk origineel artikel</a>\n\n"
    try:
       print('response ') 
       response = client.chat.completions.create(
           model=model,
           messages=[
               {"role": "system", "content": "Je bent een behulpzame assistent."},
               {"role": "user", "content": prompt}
           ]
       )
       #print(response)  # Debug: Bekijk de volledige response

       return response.choices[0].message.content
    except Exception as e:
        print(f"Er is een fout opgetreden bij het genereren van blog_content: {e}")


def update_run_status(run_id):
    now = datetime.now()
    try:
        with connect(database=database, user=username, password=password, host=host, port=port) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE rb_runs
                    SET status = 'V', end_datetime = %s
                    WHERE status = 'S' AND id = %s;
                """, (now, run_id,))
                conn.commit()
                print(f"Status van run_id {run_id} bijgewerkt naar 'V'.")
    except Exception as e:
        print(f"Er is een fout opgetreden bij het bijwerken van de run-status: {e}")
        sys.exit(1)


