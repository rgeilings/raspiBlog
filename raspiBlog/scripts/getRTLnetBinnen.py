from raspiBlogLib import * # Importeer alle functies uit raspiBlogLib

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


def extract_article_data(base_url, patterns):
    response = requests.get(base_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        article_links = []  # Sla de URL's op
        found_urls = set()  # In-memory structuur om gevonden URLs bij te houden

        # Zoek naar alle 'a' tags
        for link in soup.find_all('a', href=True):
            article_url = link['href']
            
            # Combineer base_url en article_url als het een relatieve URL is
            full_url = urljoin(base_url, article_url)
            print(f"full_url: {full_url}")

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
                found_urls.add(full_url)  # Voeg de URL toe aan de set

                print(f"URL: {full_url}")

        return article_links
    else:
        raise Exception(f"Error fetching page: {response.status_code}")

def get_articles(article_url, runid):
    url = article_url
    response = requests.get(url)

    if response.status_code == 200:
        print(f" >>>>>>>>>>>>>>url: {url}")
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

        # Zoek naar het script met de JSON-gegevens
        script_tag = soup.find('script', string=re.compile('window.__APOLLO_STATE__'))
        if script_tag:
            json_text = script_tag.string.split('window.__APOLLO_STATE__ = ')[1].split('};')[0] + '}'
            try:
                data = json.loads(json_text)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return

            # Zoek naar de juiste article key
            article_key = None
            for key in data.keys():
                if key.startswith("Article:"):
                    article_key = key
                    break

            if article_key:
                lead_text = data[article_key]["lead"]
                all_scraped_text = lead_text + ' ' 
                print(f" Lead text:{lead_text}")
            else:
                print("Geen artikel gevonden in de JSON-gegevens.")

        # Zoek alle divs met 'data-testid="text-paragraph"' en een class die begint met 'css-'
        class_pattern = re.compile(r"^css-[a-zA-Z0-9]+$")
        paragraphs = soup.find_all("div", {"data-testid": "text-paragraph", "class": class_pattern})

        # Extract de tekstinhoud van alle gevonden paragrafen
        texts = []

        # Zoek de meta tag met property="article:published_time"
        meta_tag = soup.find('meta', {'property': 'article:published_time'})

        # Haal de waarde van het content attribuut op
        publication_time = meta_tag['content'] if meta_tag else None
        print(f"The published time is: {publication_time}")

        #all_scraped_text = lead_text + ' ' if lead_text else ''
        #all_scraped_text = ''

        for div in paragraphs:
            # Doorzoek elk <div> en verzamel tekstinhoud van <p>-tags
            for p in div.find_all('p'):
                text = p.get_text(strip=True)
                all_scraped_text += text + "\n\n"

        # Converteer de string naar een datetime-object
        if publication_time is not None:
            publication_time = datetime.strptime(publication_time, "%Y-%m-%dT%H:%M:%S.%fZ")

            # Vergelijk de datum
            if publication_time.date() == datetime.today().date():

                # Maak samenvatting voor blogpost
                #summary = maak_summary(all_scraped_text)
                summary = ''

                # Stel aanvullende gegevens in
                article_row = {}
                set_run_id(article_row, runid)
                set_full_url(article_row, url)
                #topic = bepaal_topic(title)
                topic = ''
                set_topic(article_row, topic)
                set_pub_date(article_row, publication_time)
                set_text(article_row, all_scraped_text)
                set_summary(article_row, summary)
                set_title(article_row, title)
                supply_channel = ''
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
        print(f"Error fetching page: {response.status_code}")        

def main():
    locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
    #
    # Gebruik de add_new_row functie uit pgdbActions.py
    start_datetime = datetime.now()
    runid = add_new_row_rb_runs(start_datetime,'C', Path(sys.argv[0]).stem)
    print(f"runid {runid}")
    # Basis URL voor artikellinks
    base_url = "https://rtlnieuws.nl/net-binnen"

    # Regex om te zoeken naar class="css-variabel" gevolgd door href="/nieuws/" zonder "video"
    patterns = ['https://rtlnieuws.nl/nieuws/', 'https://rtlnieuws.nl/boulevard/']

    article_data = extract_article_data(base_url,patterns)
    
    #Verwerk elk artikel en print de tijd
    for article_link in (article_data):
        full_url = article_link
        print(f"Scraping {full_url}...")
        get_articles(full_url, runid) 
    update_run_status(runid)

if __name__ == "__main__":
    main()
