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

def get_supply_channel_name(url):
    """
    Haalt de waarde van 'supplyChannelName' op uit de HTML van de opgegeven URL
    en verwijdert 'NOS' als prefix.

    :param url: De URL van de webpagina
    :return: De waarde van 'supplyChannelName' zonder 'NOS' of een foutmelding
    """
    try:
        # Download de HTML-pagina
        response = requests.get(url)
        response.raise_for_status()  # Controleer op HTTP-fouten

        html_content = response.text  # HTML-inhoud

        # Probeer eerst JSON in een <script> tag te vinden
        soup = BeautifulSoup(html_content, "html.parser")
        script_tag = soup.find("script", type="application/ld+json")

        if script_tag:
            try:
                json_data = json.loads(script_tag.string)
                if "supplyChannelName" in json_data:
                    channel_name = json_data["supplyChannelName"]
                    return channel_name.replace("NOS ", "")  # Verwijder 'NOS '
            except json.JSONDecodeError:
                pass  # Ga door naar regex-methode als JSON niet correct is

        # Gebruik regex als fallback
        match = re.search(r'"supplyChannelName"\s*:\s*"([^"]+)"', html_content)
        if match:
            channel_name = match.group(1)
            return channel_name.replace("NOS ", "")  # Verwijder 'NOS '

        return "supplyChannelName niet gevonden"

    except requests.exceptions.RequestException as e:
        return f"Fout bij ophalen van de URL: {e}"

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
            #summary = maak_summary(all_scraped_text)
            summary =''

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
            supply_channel = get_supply_channel_name(url)
            set_supply_channel(article_row, supply_channel)
            print(f"supply_channel:{supply_channel}")

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
    runid = add_new_row_rb_runs(start_datetime,'C', Path(sys.argv[0]).stem)

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
    update_run_status(runid, 'none', 'V')

if __name__ == "__main__":
    main()
