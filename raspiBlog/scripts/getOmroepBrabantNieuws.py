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

    # Controleer op 'Vandaag'
    if 'Vandaag' in time_str:
        return datetime(now.year, now.month, now.day, now.hour, now.minute, now.second)

    # Controleer op relatieve uren
    match_hours = re.search(r'(\d+)\s*uur geleden', time_str)
    if match_hours:
        hours_ago = int(match_hours.group(1))
        return now - timedelta(hours=hours_ago)

    # Controleer op relatieve minuten
    match_minutes = re.search(r'(\d+)\s*minuten geleden', time_str)
    if match_minutes:
        minutes_ago = int(match_minutes.group(1))
        return now - timedelta(minutes=minutes_ago)

    # Controleer op relatieve dagen
    match_days = re.search(r'(\d+)\s*dag geleden', time_str)
    if match_days:
        days_ago = int(match_days.group(1))
        return now - timedelta(days=days_ago)

    # Controleer op dagen van de week (bijv. "vrijdag")
    dagen = {
        "maandag": 0, "dinsdag": 1, "woensdag": 2, "donderdag": 3,
        "vrijdag": 4, "zaterdag": 5, "zondag": 6
    }
    if time_str.lower() in dagen:
        # Bereken hoeveel dagen geleden het is
        vandaag = now.weekday()  # 0 = maandag, 6 = zondag
        target_dag = dagen[time_str.lower()]
        dagen_verschil = (vandaag - target_dag) % 7
        if dagen_verschil == 0:  # Vandaag
            dagen_verschil = 7  # Voor vorige week dezelfde dag
        return now - timedelta(days=dagen_verschil)

    # Controleer op absolute datums (bijv. "16 december 2024 15:45")
    try:
        return datetime.strptime(time_str, '%d %B %Y %H:%M')
    except ValueError:
        pass  # Ga verder naar de foutmelding als het formaat niet klopt

    # Als het formaat niet wordt herkend, geef een foutmelding
    raise ValueError(f"Het formaat van de tijd is niet juist: {time_str}")

def extract_article_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        content = response.text
        soup = BeautifulSoup(content, 'html.parser')
        articles = []
        for link in soup.find_all('a', class_='article-teaser_link__pvELC'):
            href = link.get('href')
            if href and href.startswith('/nieuws/') and '112-nieuws' not in href:
                article_url = f"https://www.omroepbrabant.nl{href}"

                if url_exists(article_url):
                    print(f"article_url already exists in database: {article_url}")
                    continue  # Ga naar de volgende URL als deze al bestaat
                time_tag = link.find_next('div', class_='article-teaser_time__SPLIi')
                publication_time = time_tag.text.strip() if time_tag else 'Onbekend'
                publication_time_parsed = parse_relative_time(publication_time)
                articles.append({
                    'url': article_url,
                    'publication_time': publication_time_parsed
                })
        return articles
    else:
        raise Exception(f"Error fetching page: {response.status_code}")
 
def get_articles(article_url, publication_time, runid, delay=10):
    articles = {}
    processed_urls = []
    url = article_url
    # Haal de HTML van de pagina op
    response = requests.get(url)
    if response.status_code == 200:  # Controleer of de HTTP-verzoek succesvol was
        html_content = response.text

        # Initialiseer BeautifulSoup met de opgehaalde HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # Zoek de titel-tag en haal de tekst op
        title_tag = soup.find('title')
        if title_tag:
            #title = title_tag.text
            title = title_tag.text.replace(" - Omroep Brabant", "") 
            print('Titel van de pagina:', title)
        else:
            print('Titel niet gevonden.')

        # Zoek naar alle div-elementen waarvan de class-naam begint met 'content_content*'
        content_divs = soup.find_all("div", class_=lambda c: c and c.startswith("content_content"))

        if content_divs:
            # Itereer door elk gevonden div-element en druk de tekst af
            # Initieer een lege string om alle tekst te verzamelen
            all_scraped_text = ""

            # Loop door de content_divs
            for div in content_divs:
                scraped_text = div.get_text(separator="\n", strip=True)
                all_scraped_text += scraped_text + "\n" + "\n"  # Voeg tekst toe en scheid met een nieuwe regel
                print(scraped_text)
        else:
            print("Geen elementen gevonden met een class die begint met 'content_content'.")
    else:
        print(f"Er ging iets mis bij het ophalen van de pagina (statuscode: {response.status_code})")
    #
    # Gebruik een regex om alles vanaf 'Dit vind je ook interessant:' te verwijderen
    all_scraped_text = re.sub(r"Dit vind je ook interessant:.*", "", all_scraped_text, flags=re.DOTALL)
    # Verwijder regels met alleen hoofdletters tot aan de dubbele punt en de regel erna
    all_scraped_text = re.sub(r"^[A-Z ]+:\s*$(\n.*)?", "", all_scraped_text, flags=re.MULTILINE)

    # Optioneel: Verwijder overtollige lege regels
    all_scraped_text = re.sub(r"\n\s*\n", "\n", all_scraped_text).strip()

    if publication_time.date() == datetime.today().date():
        # Maak samenvatting voor blogpost
        summary = maak_summary(all_scraped_text)
        set_run_id(article_row, runid)
        set_full_url(article_row, article_url)
        topic = bepaal_topic(title)
        #if 'Titel niet gevonden.' not in title:
        #   topic = bepaal_topic(title)
        #else:
        #   topic = bepaal_topic(all_scraped_text)
        set_topic(article_row, topic)
        set_pub_date(article_row, publication_time)
        set_text(article_row, all_scraped_text)
        set_summary(article_row, summary)
        set_title(article_row, title)
        article_id = insert_article(article_row)
        clear_article_row(article_row)
        if article_id is not None:
            print(f"Inserted article with ID {article_id} for run_id: {runid}")

def main():
    locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
    #
    # Gebruik de add_new_row functie uit pgdbActions.py
    start_datetime = datetime.now()
    runid = add_new_row(start_datetime,'C')
    print(f"runid {runid}")
    # Haal artikelen op van omroepbrabant.nl
    url = 'http://omroepbrabant.nl/netbinnen'
    article_data = extract_article_data(url)

    # Sorteer de artikelen op basis van publication_time, meest recent eerst
    sorted_articles = sorted(article_data, key=lambda x: x['publication_time'], reverse=True)

    # Print de gesorteerde artikelen
    print("Gevonden artikelen gesorteerd op publicatietijd (meest recent eerst):")
    for article in sorted_articles:
        print(f"URL: {article['url']}, Tijd: {article['publication_time']}")
        get_articles(article['url'], article['publication_time'], runid)
    update_run_status(runid)

if __name__ == "__main__":
    main()
