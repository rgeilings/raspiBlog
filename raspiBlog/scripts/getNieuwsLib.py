from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from pgdbActions import *  # Importeer alle functies uit pgdbActions
import json
import random
import re
import requests

# Laad omgevingsvariabelen uit .env bestand
load_dotenv()

SUMMARIES_FILE = os.getenv('SUMMARIES_FILE', '/app/summaries.txt')
DALLE3_PROMPT = os.getenv('DALLE3_PROMPT', '/app/dall-e_3_prompt.txt')
BLOG_FILE = os.getenv('BLOG_FILE', '/app/blog_post.txt')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# maak_blog_summary
MBSURL = os.getenv('MBSURL')
MBSMODEL = os.getenv('MBSMODEL')
# maak_DALLE3_PROMPT
MMDPMODEL = os.getenv('MMDPMODEL')
# generate_blog_content_per_topic
GBPCPTMODEL = os.getenv('GBPCPTMODEL')

# maak_summary
MSURL =  os.getenv('MSURL')
MSMODEL =os.getenv('MSMODEL')
# bepaal_topic
BTURL =  os.getenv('BTURL')
BTMODEL = os.getenv('BTMODEL')


# In-memory rij
article_row = {
    "run_id": None,
    "full_url": None,
    "topic": None,
    "summary": None,
    "text": None,
    "pub_date": None,
    "title": None
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

# article_row leegmaken
def clear_article_row(row):
    row["run_id"] = None
    row["full_url"] = None
    row["topic"] = None
    row["summary"] = None
    row["text"] = None
    row["pub_date"] = None
    row["title"] = None

def maak_summary(article_text):
    huidige_datum = datetime.now().strftime('%d %B %Y')
    url = MSURL
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model": MSMODEL,
        "prompt": (
            f"Kan je onderstaande tekst afkomstig van een nieuwssite in eigen woorden herschrijven. Geen wollige tekst en to the point. "
            f"De tekst moet waarheidsgetrouw zijn, nieuwswaarde hebben en alleen feiten uit de tekst bevatten. "
            f"Als je een datum wil gebruiken, gebruik dan alleen datums die expliciet zijn genoemd."
            f"Als vandaag wordt genoemd mag {huidige_datum} gebruikt worden maar hoeft niet."
            f"Hou rekening met de locatie van het artikel om datum eventueel om te rekenen naar locale datum"
            f"Hierbij geen titels en geen aankondiging dat het een blogpost betreft: {article_text}"
        ),
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        response_text = response.text
        data = json.loads(response_text)
        actual_response = data.get("response", "Geen antwoord gevonden in de response.")
        # Verwijder regels met "Titel" of "titel"
        actual_response = re.sub(r".*(T|t)itel.*\n?", "", actual_response)
        #print(f">>>>>>>>>>>> actual_response: {actual_response}")
        return actual_response.strip()
    except requests.exceptions.RequestException as e:
        print(f"Fout bij het maken van een summary: {e}")
        return "Fout bij het maken van een summary."
    
def bepaal_topic(title):
    url = BTURL
    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "model": BTMODEL,
        "prompt": (
            f"herschrijf de volgende titel naar een titel met dezelfde betekenis."
            f"Hou je aan de feiten en doe geen aannames! Zorg ervoor dat de titel Nederlands correct is. "
            f"Geef alleen de titel terug en geen aankondiging dat het een titel betreft. "
            f"Er mag geen datum en ook geen jaartal in de titel staan. "
            f"Geen verdere uitleg. Titel:{title}"
        ),
        "stream": False
    }
    try:
        # API-aanroep
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        response_text = response.text
        data = json.loads(response_text)
        # Topic ophalen en opschonen
        topic = data.get("response", "Geen antwoord gevonden in de response.")
        resultaat = data.get("response", "Geen antwoord gevonden in de response.")
        # Verwijder eventuele newline-tekens
        resultaat = resultaat.replace("\n", " ").strip()
        if resultaat.startswith('"'):
            resultaat = resultaat[1:]  # Verwijder eerste karakter als het een "
        if resultaat.endswith('"') or resultaat.endswith('.'):
            resultaat = resultaat.rstrip('".').rstrip('.')
        print(f"Herschreven titel is: {resultaat}")
        return resultaat
    except requests.exceptions.RequestException as e:
        print(f"Fout bij het bepalen van het topic: {e}")
        return title

def maak_blog_summary(blog_content):
    url = MBSURL
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model": MBSMODEL,
        "prompt": (
            f"Kan je een DALLE-3 prompt maken uit onderstaande tekst. Combineer zoveel mogelijk verschillende onderwerpen uit de tekst in 1 prompt."
            f"Geef uitsluitend de DALLE-3 prompt terug zonder enige introductie, toelichting, of extra tekst. Tekst: {blog_content}"
        ),
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        response_text = response.text
        data = json.loads(response_text)
        actual_response = data.get("response", "Geen antwoord gevonden in de response.")
        # Verwijder regels met "Titel" of "titel"
        actual_response = re.sub(r".*(T|t)itel.*\n?", "", actual_response)
        print(f">>>>>>>>>>>> samenvatting blog_post: {actual_response}")
        return actual_response.strip()
    except requests.exceptions.RequestException as e:
        print(f"Fout bij het maken van een summary: {e}")
        return "Fout bij het maken van een summary."

def maak_DALLE3_PROMPT(client, blog_text):
    # Formuleer de opdracht voor de AI
    instruction = (
      "Maak een gedetailleerde DALLE-3 prompt gebaseerd op de volgende tekst. "
      "Combineer zoveel mogelijk unieke onderwerpen, thema's en elementen uit de tekst tot één coherente prompt. "
      "Lever uitsluitend de gegenereerde prompt aan, zonder verdere uitleg of extra tekst. Tekst:\n"
      f"{blog_text}"
    )

    # Vraag de AI om de prompt te genereren
    response = client.chat.completions.create(
      model= MMDPMODEL,
      messages=[
        {"role": "system", "content": "Je bent een deskundige assistent die gedetailleerde prompts genereert."},
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

def generate_blog_content_per_topic(topic, articles, client):
    prompt = f"Maak een blogpost op basis van de volgende samenvattingen voor het onderwerp '{topic}'. Voeg headers en opmaak toe,\n"
    prompt += "maar verzin geen extra inhoud. Voeg onderaan elk artikel een 'Bekijk origineel artikel'-link toe in HTML, zodat de link opent in een nieuwe tab.\n"
    prompt += "Herschrijf de samenvatting naar een informele stijl. Zorg ervoor dat er geen plagiaat veroorzaakt wordt.\n"
    prompt += "Als je een datum wil gebruiken, gebruik dan alleen datums die expliciet zijn genoemd. Herschrijf eventueel {topic} als dit niet bij het article past. \n"
    prompt += "Het herschreven topic moet wel Nederlandstalig zijn. Gebruik de volgende structuur:\n"
    prompt += f"\n## onderwerp van article\n"
    for url, summary in articles:
        prompt += f"{summary}\n\n<a href=\"{url}\" target=\"_blank\">Bekijk origineel artikel</a>\n\n"
    response = client.chat.completions.create(
        model=GBPCPTMODEL,
        messages=[
            {"role": "system", "content": "Je bent een behulpzame assistent."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def generate_blog_content(client, summaries):
    blog_content = ""
    for topic, articles in summaries.items():
        blog_content += generate_blog_content_per_topic(topic, articles, client) + "\n"
    return blog_content

def generate_blog_content_per_topic_oud(topic, articles, client):
    prompt = f"Maak een blogpost op basis van de volgende samenvattingen voor het onderwerp '{topic}'. Voeg headers en opmaak toe,\n"
    prompt += "maar verzin geen extra inhoud en geen urls. Herschrijf de samenvatting naar een informele stijl. Zorg ervoor dat er geen plagiaat veroorzaakt wordt.\n"
    prompt += "Als je een datum wil gebruiken, gebruik dan alleen datums die expliciet zijn genoemd. Herschrijf eventueel {topic} als dit niet bij het article past. \n"
    prompt += "Gebruik de volgende structuur:\n"
    prompt += f"\n## onderwerp van article \n"
    for url, summary in articles:
        prompt += f"{summary}\n"
    response = client.chat.completions.create(
        model= GBPCPTMODEL,
        messages=[
            {"role": "system", "content": "Je bent een behulpzame assistent."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def generate_blog_content_oud(client, summaries):
    blog_content = ""
    for topic, articles in summaries.items():
        blog_content += generate_blog_content_per_topic(topic, articles, client) + "\n"
    return blog_content

