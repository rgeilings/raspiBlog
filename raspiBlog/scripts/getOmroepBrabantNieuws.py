import sys
import time
import locale
import requests
import re
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from raspiBlogLib import *

# Basis-URL van de website
BASE_URL = "https://www.omroepbrabant.nl"
URLS = {
    "Nieuws": BASE_URL + "/netbinnen",
    "Sport": BASE_URL + "/sport"
}

# Headers om te voorkomen dat de scraper wordt geblokkeerd
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_html(url):
    """Haal de HTML van een pagina op met error handling."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Fout bij laden van {url}: Status code {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Verbindingsfout bij {url}: {e}")
        return None

def extract_article_urls(main_page_html):
    """Haal alle artikel-URL's op de hoofdpagina."""
    soup = BeautifulSoup(main_page_html, "html.parser")
    articles = soup.find_all("article")
    
    results = []
    for article in articles:
        link_tag = article.find("a", href=True)
        article_url = BASE_URL + link_tag["href"] if link_tag else None
        if article_url:
            results.append(article_url)

    return results

def extract_metadata(article_url):
    """Scrape publicatiedatum en wijzigingsdatum van een artikelpagina."""
    article_html = fetch_html(article_url)
    if not article_html:
        return None, None  # Geen HTML beschikbaar

    soup = BeautifulSoup(article_html, "html.parser")

    published_time, modified_time = None, None
    meta_tags = soup.find_all("meta")

    for tag in meta_tags:
        if tag.get("property") == "article:published_time":
            published_time = tag.get("content")
        if tag.get("property") == "article:modified_time":
            modified_time = tag.get("content")

    return published_time, modified_time

def get_articles(article_url, publication_time, modified_time, runid, category, delay=2):
    """Scrape de titel en inhoud van een artikelpagina en sla op als publicatiedatum of wijzigingsdatum vandaag is."""
    response = requests.get(article_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Fout bij laden van artikel: {article_url}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    # Artikel titel
    title_tag = soup.find("title")
    title = title_tag.text.replace(" - Omroep Brabant", "") if title_tag else "Geen titel gevonden"

    # Artikel inhoud scrapen
    content_divs = soup.find_all("div", class_=lambda c: c and c.startswith("content_content"))
    all_scraped_text = "\n\n".join([div.get_text(separator="\n", strip=True) for div in content_divs]) if content_divs else "Geen inhoud gevonden"

    # Opruimen van irrelevante content
    all_scraped_text = re.sub(r"Dit vind je ook interessant:.*", "", all_scraped_text, flags=re.DOTALL)
    all_scraped_text = re.sub(r"^[A-Z ]+:\s*$(\n.*)?", "", all_scraped_text, flags=re.MULTILINE)
    all_scraped_text = re.sub(r"\n\s*\n", "\n", all_scraped_text).strip()

    # Alleen opslaan als publicatie- of wijzigingsdatum vandaag is
    today = datetime.today().date()
    pub_date = publication_time.date() if publication_time else None
    mod_date = modified_time.date() if modified_time else None

    if pub_date == today or mod_date == today:
        print(f"\n Artikel: {title}")
        print(f"Publicatiedatum: {publication_time} 🕒 {publication_time.strftime('%H:%M:%S')}" if publication_time else "📅 Geen publicatiedatum gevonden")
        print(f"Gewijzigd op: {modified_time} 🕒 {modified_time.strftime('%H:%M:%S')}" if modified_time else "🔄 Geen wijzigingsdatum gevonden")
        print(f"Tekst:\n{all_scraped_text[:500]}...\n" + "-"*80)

        latest_time = max(publication_time, modified_time) if publication_time and modified_time else publication_time or modified_time 
       
        # Opslaan van artikel
        summary = ''
        set_run_id(article_row, runid)
        set_full_url(article_row, article_url)
        set_topic(article_row, "")
        set_pub_date(article_row, latest_time)
        set_text(article_row, all_scraped_text)
        set_summary(article_row, summary)
        set_title(article_row, title)
        set_supply_channel(article_row, category)

        print(f">>>>>>>>>>>>>>>>>>>>article_row:{article_row}")
        article_id = insert_article(article_row)
        clear_article_row(article_row)

        if article_id is not None:
            print(f"Inserted article with ID {article_id} for run_id: {runid}")

def main(category):
    """Hoofdfunctie om het scraping-proces te starten."""
    if category not in URLS:
        print("Ongeldige parameter! Gebruik 'Nieuws' of 'Sport'.")
        sys.exit(1)

    url = URLS[category]

    locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')

    # Start nieuwe run
    start_datetime = datetime.now()
    runid = add_new_row_rb_runs(start_datetime, 'C', Path(sys.argv[0]).stem)
    print(f"runid {runid}")

    # Stap 1: Haal HTML van de pagina op
    main_page_html = fetch_html(url)

    if main_page_html:
        article_urls = extract_article_urls(main_page_html)

        # Stap 2: Controleer datum en scrape artikelinhoud als datum vandaag is
        for article_url in article_urls:
            if url_exists(article_url):
                print(f"article_url already exists in database: {article_url}")
                continue  # Ga naar de volgende URL als deze al bestaat

            published_time, modified_time = extract_metadata(article_url)

            # Zet tijdstempel om naar datetime object
            try:
                pub_time = datetime.strptime(published_time, "%Y-%m-%dT%H:%M:%S%z") if published_time else None
                mod_time = datetime.strptime(modified_time, "%Y-%m-%dT%H:%M:%S%z") if modified_time else None
            except ValueError as e:
                print(f"Datumconversiefout bij {article_url}: {e}")
                continue

            if (pub_time and pub_time.date() == datetime.today().date()) or (mod_time and mod_time.date() == datetime.today().date()):
                get_articles(article_url, pub_time, mod_time, runid, category)
                time.sleep(2)  # Even wachten om niet te snel te scrapen

    else:
        print("Fout: Hoofdpagina kon niet worden geladen. Controleer je verbinding of headers.")

    update_run_status(runid, 'none', 'V')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Gebruik: python getOmroepBrabant.py [Nieuws|Sport]")
        sys.exit(1)

    category = sys.argv[1]  # Ontvang parameter Nieuws of Sport
    main(category)

