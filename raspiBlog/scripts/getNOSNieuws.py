from raspiBlogLib import * # Importeer alle functies uit raspiBlogLib
import re
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json
import random
import time
import locale
import sys
from pathlib import Path

def parse_relative_time(time_str):
    """
    Parse relatieve tijd strings van NOS.nl naar datetime objecten.
    """
    now = datetime.now()
    print(f"Huidige systeemtijd: {now}")

    # Verwerk 'Zojuist' als de huidige datum en tijd
    if time_str.strip().lower() == 'zojuist':
        return now

    # Controleer op 'Gisteren'
    if 'gisteren' in time_str.lower():
        yesterday = now - timedelta(days=1)
        return datetime(yesterday.year, yesterday.month, yesterday.day, now.hour, now.minute, now.second)

    # Controleer op relatieve uren
    match_hours = re.search(r'(\d+)\s*uur geleden', time_str.lower())
    if match_hours:
        hours_ago = int(match_hours.group(1))
        return now - timedelta(hours=hours_ago)

    # Controleer op relatieve dagen
    match_days = re.search(r'(\d+)\s*dag geleden', time_str.lower())
    if match_days:
        days_ago = int(match_days.group(1))
        return now - timedelta(days=days_ago)

    # Controleer op absolute datums (bijv. "16 december 2024 15:45")
    try:
        return datetime.strptime(time_str, '%d %B %Y %H:%M')
    except ValueError:
        pass

    # Als het formaat niet wordt herkend, return huidige tijd
    print(f"Onbekend tijdformaat: {time_str}, gebruik huidige tijd")
    return now

def determine_supply_channel_from_url(url):
    """
    Bepaal supply channel op basis van URL als fallback.
    """
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    
    if '/sport' in path or '/collectie/' in path:
        return 'Sport'
    else:
        return 'Nieuws'

def get_supply_channel_name(url):
    """
    Haalt de waarde van 'supplyChannelName' op uit de HTML van de opgegeven URL
    en verwijdert 'NOS' als prefix. Gebruikt URL-based fallback als niet gevonden.
    """
    try:
        # Download de HTML-pagina
        response = requests.get(url)
        response.raise_for_status()

        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Probeer eerst JSON in een <script> tag te vinden
        script_tag = soup.find("script", type="application/ld+json")

        if script_tag:
            try:
                json_data = json.loads(script_tag.string)
                if "supplyChannelName" in json_data:
                    channel_name = json_data["supplyChannelName"]
                    return channel_name.replace("NOS ", "")
            except json.JSONDecodeError:
                pass

        # Gebruik regex als fallback
        match = re.search(r'"supplyChannelName"\s*:\s*"([^"]+)"', html_content)
        if match:
            channel_name = match.group(1)
            return channel_name.replace("NOS ", "")

        # Als niets gevonden, gebruik URL-based bepaling
        return determine_supply_channel_from_url(url)

    except requests.exceptions.RequestException as e:
        print(f"Fout bij ophalen van supply channel voor {url}: {e}")
        return determine_supply_channel_from_url(url)

def is_unwanted_text(text):
    """
    Controleer of een tekst ongewenste content bevat die gefilterd moet worden.
    """
    unwanted_phrases = [
        'cookies op de website van nos',
        'nos gebruikt functionele en analytische cookies',
        'meer uitleg',
        'naar cookieinstellingen',
        'deel dit artikel',
        'link gekopieerd',
        'bekijk meer',
        'live bij nos',
        'dit is er de komende tijd bij nos',
        'collectie',
        'kijk hier live',
        'livestream',
        'scorebord'
    ]
    
    text_lower = text.lower().strip()
    
    # Skip lege teksten of zeer korte teksten
    if len(text_lower) < 10:
        return True
    
    # Controleer op ongewenste zinnen
    for phrase in unwanted_phrases:
        if phrase in text_lower:
            return True
            
    return False

def extract_article_text(soup):
    """
    Extract de hoofdartikel tekst uit de BeautifulSoup object voor NOS.nl.
    """
    all_scraped_text = ""
    
    # Zoek naar elementen met het specifieke class-patroon zoals in het originele script
    class_pattern = re.compile(r"^sc-[a-f0-9]+-[0-9]+ [a-zA-Z]+$")
    id_pattern = re.compile(r"^\d+$")

    # Zoek elementen met het class patroon en numerieke ID
    for element in soup.find_all(class_=class_pattern):
        if 'id' in element.attrs and id_pattern.match(element['id']):
            text = element.get_text(separator=' ', strip=True)
            if text and not is_unwanted_text(text):
                all_scraped_text += text + "\n\n"
    
    # Als geen tekst gevonden met class patroon, probeer gewone paragrafen
    if not all_scraped_text.strip():
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and not is_unwanted_text(text):
                all_scraped_text += text + "\n\n"
    
    return all_scraped_text.strip()

def extract_article_data(base_url):
    """
    Extract artikel URLs van de NOS.nl hoofdpagina.
    """
    response = requests.get(base_url)
    print(f"response.status_code: {response.status_code}")

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []

        # Patroon voor artikel URLs (simpele ID-only structuur)
        patterns = [
            re.compile(r"^/artikel/\d+$")
        ]

        for element in soup.find_all('a', href=True):
            href = element['href']
            
            # Controleer of href matcht met een van de patronen
            for pattern in patterns:
                if pattern.match(href):
                    article_url = f"{base_url.rstrip('/')}{href}"
                    print(f"article_url: {article_url}")
                    
                    # Controleer of de URL al bestaat
                    if url_exists(article_url):
                        print(f"article_url already exists in database: {article_url}")
                        continue

                    # Zoek naar tijd informatie
                    time_tag = element.find_next('time', {'datetime': True})
                    publication_time = time_tag['datetime'] if time_tag else 'N/A'

                    articles.append({
                        'url': article_url,
                        'publication_time': publication_time
                    })
                    break  # Stop na eerste match

        return articles
    else:
        raise Exception(f"Error fetching page: {response.status_code}")

def get_articles(article_url, publication_time, runid):
    """
    Scrape een individueel artikel van NOS.nl.
    """
    url = article_url
    response = requests.get(url)

    if response.status_code == 200:
        print(f" >>>>>>>>>>>>>>>>url: {url}")
        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")

        # Zoek de titel-tag en haal de tekst op
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.text.strip()
            print('Titel van de pagina:', title)
        else:
            print('Titel niet gevonden.')
            return

        # Extract artikel tekst met verbeterde filtering
        all_scraped_text = extract_article_text(soup)
        
        if not all_scraped_text:
            print("Geen artikel tekst gevonden na filtering")
            return
            
        print(f"Artikel tekst lengte: {len(all_scraped_text)} karakters")
        print(f"Eerste 200 karakters: {all_scraped_text[:200]}...")

        # Converteer de string naar een datetime-object
        if publication_time != 'N/A':
            try:
                publication_time = datetime.strptime(publication_time, "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                # Als parsing faalt, gebruik huidige tijd
                publication_time = datetime.now()
        else:
            publication_time = datetime.now()

        # Vergelijk de datum
        if publication_time.date() == datetime.today().date():

            # Bepaal supply channel
            supply_channel = get_supply_channel_name(url)
            print(f"supply_channel: {supply_channel}")

            # Stel aanvullende gegevens in
            article_row = {}
            set_run_id(article_row, runid)
            set_full_url(article_row, url)
            
            topic = ''
            set_topic(article_row, topic)
            set_pub_date(article_row, publication_time) 
            set_text(article_row, all_scraped_text)
            
            summary = ''
            set_summary(article_row, summary)
            set_title(article_row, title)
            set_supply_channel(article_row, supply_channel)

            # Voeg artikel toe aan de database
            article_id = insert_article(article_row)
            clear_article_row(article_row)
            
            if article_id is not None:
                print(f"Inserted article with ID {article_id} for run_id: {runid}")
                
            # Wacht een willekeurig aantal seconden tussen 2 en 5
            wait_time = random.uniform(2, 5)
            print(f"Wachten gedurende {wait_time:.2f} seconden...")
            time.sleep(wait_time)
        else:
            print(f"Artikel is niet van vandaag: {publication_time.date()}")
    else:
        print(f"Error fetching page: {response.status_code}")

def main():
    """
    Hoofdfunctie voor het scrapen van NOS.nl artikelen.
    """
    locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
    
    # Gebruik de add_new_row functie uit pgdbActions.py
    start_datetime = datetime.now()
    runid = add_new_row_rb_runs(start_datetime, 'C', Path(sys.argv[0]).stem)
    print(f"runid {runid}")
    
    try:
        # Haal het laatste nieuws van nos.nl 
        base_url = "https://nos.nl"
        article_data = extract_article_data(base_url)
        print(f"Gevonden {len(article_data)} artikelen")

        # Sorteer de artikelen op basis van publication_time, meest recent eerst
        sorted_articles = sorted(article_data, key=lambda x: x['publication_time'], reverse=True)

        # Print de gesorteerde artikelen
        print("Gevonden artikelen gesorteerd op publicatietijd (meest recent eerst):")
        for article in sorted_articles:
            print(f"URL: {article['url']}, Tijd: {article['publication_time']}")
            try:
                get_articles(article['url'], article['publication_time'], runid)
            except Exception as e:
                print(f"Fout bij verwerken van artikel {article['url']}: {e}")
                continue
                
        update_run_status(runid, 'none', 'V')
        
    except Exception as e:
        print(f"Fout bij scrapen: {e}")
        update_run_status(runid, 'none', 'F')

if __name__ == "__main__":
    main()

