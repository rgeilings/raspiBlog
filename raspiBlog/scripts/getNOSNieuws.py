from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import requests
import re
import locale
from pgdbActions import *  # Importeer alle functies uit pgdbActions
from getNieuwsLib import * # Importeer alle functies uit getNieuwsLib
import json
import random
import time

def parse_relative_time(time_str):
    now = datetime.now()
    print(f"Huidige systeemtijd: {now}")  # Log de huidige datum en tijd

    # Verwerk 'Zojuist' als de huidige datum en tijd
    if time_str.strip().lower() == 'zojuist':
        return now

    # Controleer op 'Gisteren'
    if 'Gisteren' in time_str:
        yesterday = now - timedelta(days=1)
        return datetime(yesterday.year, yesterday.month, yesterday.day, now.hour, now.minute, now.second)

    # Controleer op relatieve uren
    match_hours = re.search(r'(\d+)\s*uur geleden', time_str)
    if match_hours:
        hours_ago = int(match_hours.group(1))
        return now - timedelta(hours=hours_ago)

    # Controleer op relatieve dagen
    match_days = re.search(r'(\d+)\s*dag geleden', time_str)
    if match_days:
        days_ago = int(match_days.group(1))
        return now - timedelta(days=days_ago)

    # Controleer op absolute datums (bijv. "16 december 2024 15:45")
    try:
        return datetime.strptime(time_str, '%d %B %Y %H:%M')
    except ValueError:
        pass  # Ga verder naar de foutmelding als het formaat niet klopt

    # Als het formaat niet wordt herkend, geef een foutmelding
    raise ValueError(f"Het formaat van de tijd is niet juist: {time_str}")

def extract_article_data(base_url):
    response = requests.get(base_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []

        pattern = re.compile(r"^/artikel/\d+-laatste-nieuws$")

        for element in soup.find_all('a', href=True):
            href = element['href']
            if pattern.match(href):
                article_url = f"{base_url.rstrip('/')}{href}"

                # Controleer of de URL al bestaat (eventueel met een functie zoals url_exists)
                if url_exists(article_url):
                    print(f"article_url already exists in database: {article_url}")
                    continue

                time_tag = element.find_next('time', {'datetime': True})
                publication_time = time_tag['datetime'] if time_tag else 'N/A'

                articles.append({
                    'url': article_url,
                    'publication_time': publication_time
                })

        return articles
    else:
        raise Exception(f"Error fetching page: {response.status_code}")

def get_articles(article_url, publication_time, runid, delay=10):
    url = article_url
    response = requests.get(url)

    if response.status_code == 200:
        html_content = response.text
        # Initialiseer BeautifulSoup met de opgehaalde HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # Zoek de titel-tag en haal de tekst op
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.text
            print('Titel van de pagina:', title)
        else:
            print('Titel niet gevonden.')

        # Zoek naar elementen met een specifieke class-patroon
        class_pattern = re.compile(r"^sc-[a-f0-9]+-[0-9]+ [a-zA-Z]+$")
        id_pattern = re.compile(r"^\d+$")

        all_scraped_text = ""

        for element in soup.find_all(class_=class_pattern):
            if 'id' in element.attrs and id_pattern.match(element['id']):
                text = element.get_text(separator=' ', strip=True)
                all_scraped_text += text + "\n\n"
        # Converteer de string naar een datetime-object
        publication_time = datetime.strptime(publication_time, "%Y-%m-%dT%H:%M:%S%z")

        # Vergelijk de datum
        if publication_time.date() == datetime.today().date():

            # Maak samenvatting voor blogpost
            summary = maak_summary(all_scraped_text)

            # Stel aanvullende gegevens in
            article_row = {}
            set_run_id(article_row, runid)
            set_full_url(article_row, url)
            topic = bepaal_topic(title)
            #if 'Titel niet gevonden.' not in title:
            #    topic = bepaal_topic(title)
            #else:
            #    topic = bepaal_topic(all_scraped_text)
            set_topic(article_row, topic)
            set_pub_date(article_row, publication_time) 
            set_text(article_row, all_scraped_text)
            set_summary(article_row, summary)
            set_title(article_row, title)

            # Voeg artikel toe aan de database
            article_id = insert_article(article_row)
            clear_article_row(article_row)
            if article_id is not None:
                print(f"Inserted article with ID {article_id} for run_id: {runid}")

    else:
        print(f"Error fetching page: {response.status_code}")

def main():
    locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
    #
    # Gebruik de add_new_row functie uit pgdbActions.py
    start_datetime = datetime.now()
    runid = add_new_row(start_datetime,'C')
    print(f"runid {runid}")
    # Haal het laatste nieuws van nos.nl 
    base_url = "https://nos.nl"
    article_data = extract_article_data(base_url)

    # Sorteer de artikelen op basis van publication_time, meest recent eerst
    sorted_articles = sorted(article_data, key=lambda x: x['publication_time'], reverse=True)

    # Print de gesorteerde artikelen
    print("Gevonden artikelen gesorteerd op publicatietijd (meest recent eerst):")
    for article in sorted_articles:
        print(f"URL: {article['url']}, Tijd: {article['publication_time']}")
        get_articles(article['url'], article['publication_time'], runid)

if __name__ == "__main__":
    main()
