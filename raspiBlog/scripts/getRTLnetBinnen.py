from raspiBlogLib import * # Importeer alle functies uit raspiBlogLib
import re
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import random
import time
import locale
import sys
from pathlib import Path

def parse_relative_time(time_str):
    """
    Parse relatieve tijd strings van RTL.nl naar datetime objecten.
    Voorbeelden:
    - "5 minuten geleden"
    - "1 uur geleden"
    - "Zojuist"
    - "Gisteren"
    """
    now = datetime.now()
    print(f"Huidige systeemtijd: {now}")
    
    # Verwerk 'Zojuist' als de huidige datum en tijd
    if 'zojuist' in time_str.lower():
        return now
    
    # Controleer op 'Gisteren'
    if 'gisteren' in time_str.lower():
        yesterday = now - timedelta(days=1)
        return datetime(yesterday.year, yesterday.month, yesterday.day, now.hour, now.minute, now.second)
    
    # Controleer op relatieve minuten
    match_minutes = re.search(r'(\d+)\s*minu[nt]en?\s+geleden', time_str.lower())
    if match_minutes:
        minutes_ago = int(match_minutes.group(1))
        return now - timedelta(minutes=minutes_ago)
    
    # Controleer op relatieve uren
    match_hours = re.search(r'(\d+)\s*uur\s+geleden', time_str.lower())
    if match_hours:
        hours_ago = int(match_hours.group(1))
        return now - timedelta(hours=hours_ago)
    
    # Controleer op relatieve dagen
    match_days = re.search(r'(\d+)\s*dag(?:en)?\s+geleden', time_str.lower())
    if match_days:
        days_ago = int(match_days.group(1))
        return now - timedelta(days=days_ago)
    
    # Als het formaat niet wordt herkend, return de huidige tijd
    print(f"Onbekend tijdformaat: {time_str}, gebruik huidige tijd")
    return now

def determine_supply_channel(url):
    """
    Bepaal de supply_channel op basis van de URL.
    """
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    
    if '/nieuws/' in path:
        # Controleer of het een sport artikel is binnen de nieuws sectie
        if '/sport/' in path:
            return 'Sport'
        else:
            return 'Nieuws'
    elif '/boulevard/' in path or '/entertainment/' in path:
        return 'Entertainment'
    elif '/sport/' in path:
        return 'Sport'
    else:
        # Default naar Nieuws als we het niet kunnen bepalen
        return 'Nieuws'

def is_unwanted_text(text):
    """
    Controleer of een tekst ongewenste content bevat die gefilterd moet worden.
    """
    unwanted_phrases = [
        'ontvang wekelijks updates',
        'download de app',
        'heb jij de app rtl',
        'advertentievrij',
        'rtl-premium',
        'privacy beleid',
        'deel artikel',
        'lees meer over',
        'bekijk ons privacy beleid',
        'exclusieve acties en persoonlijke tips',
        'download \'m hier voor',
        'ja? daar zijn we blij mee',
        'nog niet? download',
        'blijf op de hoogte van de nieuwste rtl',
        'je kunt je op elk moment onderaan de e-mail uitschrijven'
    ]
    
    text_lower = text.lower().strip()
    
    # Skip lege teksten of zeer korte teksten
    if len(text_lower) < 10:
        return True
    
    # Controleer op ongewenste zinnen
    for phrase in unwanted_phrases:
        if phrase in text_lower:
            return True
    
    # Skip teksten die alleen uit links bestaan
    if text_lower.startswith('lees ook') and len(text_lower) < 50:
        return True
        
    return False

def extract_article_data(base_url, patterns):
    """
    Extract artikel URLs van de RTL.nl hoofdpagina.
    """
    response = requests.get(base_url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        article_links = []
        found_urls = set()
        
        # Zoek naar alle 'a' tags met href attributen
        for link in soup.find_all('a', href=True):
            article_url = link['href']
            
            # Combineer base url en article url als het een relatieve URL is
            full_url = urljoin(base_url, article_url)
            
            # Controleer of de gegenereerde URL voldoet aan een van de patronen
            if any(full_url.startswith(pattern) for pattern in patterns):
                
                # Controleer of de URL al bestaat in de database
                if url_exists(full_url):
                    print(f"URL already exists in database: {full_url}")
                    continue
                
                # Controleer of de URL al eerder is gevonden op de pagina
                if full_url in found_urls:
                    print(f"URL already found on page: {full_url}")
                    continue
                
                article_links.append(full_url)
                found_urls.add(full_url)
                
                print(f"URL gevonden: {full_url}")
    
        return article_links
    else:
        raise Exception(f"Error fetching page: {response.status_code}")

def extract_article_text(soup):
    """
    Extract de hoofdartikel tekst uit de BeautifulSoup object.
    """
    all_scraped_text = ""
    
    # Zoek eerst naar de hoofdartikel container
    article_containers = soup.find_all(['article', 'main'])
    
    if article_containers:
        # Als we een artikel container vinden, zoek alleen daarin
        container = article_containers[0]
        paragraphs = container.find_all('p')
    else:
        # Anders zoek in alle paragrafen
        paragraphs = soup.find_all('p')
    
    # Filter en verzamel artikel tekst
    for p in paragraphs:
        text = p.get_text(strip=True)
        
        # Skip ongewenste teksten
        if is_unwanted_text(text):
            continue
            
        # Voeg geldige tekst toe
        if text:
            all_scraped_text += text + "\n\n"
    
    # Trim de tekst en verwijder overtollige witruimte
    all_scraped_text = all_scraped_text.strip()
    
    # Extra filtering voor specifieke patronen die aan het begin kunnen staan
    lines = all_scraped_text.split('\n')
    filtered_lines = []
    
    for line in lines:
        line = line.strip()
        if line and not is_unwanted_text(line):
            filtered_lines.append(line)
    
    return '\n\n'.join(filtered_lines)

def get_articles(article_url, runid):
    """
    Scrape een individueel artikel van RTL.nl.
    """
    url = article_url
    response = requests.get(url)
    
    if response.status_code == 200:
        print(f" >>>>>>>>>>>>>>>>url: {url}")
        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Zoek de titel-tag en haal de tekst op
        title_tag = soup.find('h1')
        if title_tag:
            title = title_tag.text.strip()
            print(f"Titel van de pagina: {title}")
        else:
            print("Titel niet gevonden.")
            return
        
        # Zoek naar de publicatiedatum informatie
        # RTL.nl gebruikt een patroon zoals "Door RTL Nieuws · 5 minuten geleden · Aangepast: 0 minuten geleden"
        publication_time = None
        time_elements = soup.find_all(string=re.compile(r'(minuten|uur|dag|zojuist|gisteren).*geleden', re.IGNORECASE))
        
        for time_text in time_elements:
            # Zoek naar het eerste deel met tijd informatie
            time_match = re.search(r'(\d+\s*(?:minuten?|uur|dag(?:en)?)\s+geleden|zojuist|gisteren)', time_text.lower())
            if time_match:
                time_str = time_match.group(1)
                publication_time = parse_relative_time(time_str)
                print(f"Publicatietijd gevonden: {time_str} -> {publication_time}")
                break
        
        if not publication_time:
            # Als geen relatieve tijd gevonden, gebruik huidige tijd
            publication_time = datetime.now()
            print("Geen publicatietijd gevonden, gebruik huidige tijd")
        
        # Extract artikel tekst met verbeterde filtering
        all_scraped_text = extract_article_text(soup)
        
        if not all_scraped_text.strip():
            print("Geen artikel tekst gevonden na filtering")
            return
        
        print(f"Artikel tekst lengte: {len(all_scraped_text)} karakters")
        print(f"Eerste 200 karakters: {all_scraped_text[:200]}...")
        
        # Controleer of het artikel van vandaag is
        if publication_time.date() == datetime.today().date():
            
            # Bepaal supply_channel op basis van URL
            supply_channel = determine_supply_channel(url)
            print(f"Supply channel bepaald: {supply_channel}")
            
            # Stel aanvullende gegevens in
            article_row = {}
            set_run_id(article_row, runid)
            set_full_url(article_row, url)
            
            # Topic bepaling (kan later uitgebreid worden)
            topic = ''
            set_topic(article_row, topic)
            set_pub_date(article_row, publication_time)
            set_text(article_row, all_scraped_text.strip())
            
            # Summary (kan later uitgebreid worden)
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
    Hoofdfunctie voor het scrapen van RTL.nl artikelen.
    """
    locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
    
    # Gebruik de add_new_row functie uit pgdbActions.py
    start_datetime = datetime.now()
    runid = add_new_row_rb_runs(start_datetime, 'C', Path(sys.argv[0]).stem)
    print(f"runid {runid}")
    
    # Basis URL voor artikellinks
    base_url = "https://www.rtl.nl/"
    
    # Patronen voor RTL.nl nieuws artikelen
    patterns = [
        'https://www.rtl.nl/nieuws/',
        'https://www.rtl.nl/boulevard/'
    ]
    
    try:
        # Extract artikel URLs
        article_data = extract_article_data(base_url, patterns)
        print(f"Gevonden {len(article_data)} artikelen")
        
        # Verwerk elk artikel
        for article_link in article_data:
            try:
                get_articles(article_link, runid)
            except Exception as e:
                print(f"Fout bij verwerken van artikel {article_link}: {e}")
                continue
                
    except Exception as e:
        print(f"Fout bij scrapen: {e}")

if __name__ == "__main__":
    main()

