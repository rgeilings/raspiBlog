import nltk
import requests
from bs4 import BeautifulSoup
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from datetime import datetime, timedelta, timezone
import dateparser
from pytrends.request import TrendReq
from dotenv import load_dotenv
import os
import locale
import time
from openai import OpenAI

# Laad omgevingsvariabelen uit .env bestand
load_dotenv()

nltk.download('punkt')

SUMMARIES_FILE = os.getenv('SUMMARIES_FILE', '/app/summaries.txt')
OUTPUT_FILE = os.getenv('OUTPUT_FILE', '/app/all_summaries.txt')
BLOG_FILE = os.getenv('BLOG_FILE', '/app/blog_post.txt')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def get_trending_topics():
    pytrends = TrendReq(hl='nl-NL', tz=360)
    trending_searches_df = pytrends.trending_searches(pn='netherlands')

    # Haal alleen de eerste 5 trending topics op
    trends = trending_searches_df[0].tolist()[:6]
    return trends
try:
    trending_topics = get_trending_topics()
    if trending_topics:
        print("Trending topics:")
        for topic in trending_topics:
            print(f"- {topic}")
    else:
        print("No trending topics found.")
except Exception as e:
    print(f"An error occurred: {e}")

def scrape_articles(keywords, delay=2):
    articles = {}
    base_url = "https://news.google.com"
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=12)

    excluded_domains = ["telegraaf.nl", "nos.nl", "vi.nl", "rtvutrecht.nl"]

    for keyword in keywords:
        keyword_articles = set()
        search_url = f"{base_url}/search?q={keyword}&hl=nl&gl=NL&ceid=NL:nl"
        try:
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                if 'article' in link['href']:
                    full_url = base_url + link['href'][1:] if link['href'].startswith('.') else link['href']
                    try:
                        resolved_response = requests.head(full_url, timeout=10, allow_redirects=True)
                        final_url = resolved_response.headers.get('location', full_url)
                        if any(domain in final_url for domain in excluded_domains):
                            print(f"Skipping URL: {final_url} due to excluded domain")
                            continue
                    except requests.RequestException as e:
                        print(f"Error resolving final URL for {full_url}: {e}")
                        continue
                    time_tag = link.find_next('time')
                    if time_tag and 'datetime' in time_tag.attrs:
                        pub_date = dateparser.parse(time_tag['datetime'])
                        if pub_date:
                            pub_date = pub_date.astimezone(timezone.utc)
                            if pub_date > time_threshold:
                                keyword_articles.add(final_url)
                                if len(keyword_articles) >= 3:
                                    break
                    # Vertraging toevoegen tussen verzoeken
                    time.sleep(delay)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {search_url}: {e}")
        except Exception as e:
            print(f"Error processing results for keyword '{keyword}': {e}")

        articles[keyword] = list(keyword_articles)

        # Vertraging toevoegen tussen verzoeken voor elke zoekopdracht
        time.sleep(delay)

    return articles

def fetch_article_text(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        popup_selectors = [
            'div.modal',
            'div.popup',
            'div[role="dialog"]',
            'div.overlay',
            '#login-popup',
            '.login-popup',
        ]

        for selector in popup_selectors:
            if soup.select_one(selector):
                print(f"Skipping article {url} due to popup")
                return ""

        paragraphs = soup.find_all('p')
        article_text = ' '.join([p.get_text() for p in paragraphs])
        return article_text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching article {url}: {e}")
    except Exception as e:
        print(f"Error processing article {url}: {e}")
    return ""

def summarize_article(text, sentence_count=20):
    parser = PlaintextParser.from_string(text, Tokenizer("dutch"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, sentence_count)
    return " ".join([str(sentence) for sentence in summary])

def write_summary(keywords, output_file):
    articles = scrape_articles(keywords)
    summaries = []
    for keyword, urls in articles.items():
        for url in urls:
            text = fetch_article_text(url)
            if text:
                summary = summarize_article(text, sentence_count=20)
                summaries.append((keyword, url, summary))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for keyword, url, summary in summaries:
            f.write(f"Keyword: {keyword}\nURL: {url}\nSamenvatting: {summary}\n\n")

def read_summaries(file_path):
    summaries = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        keyword, url, summary = None, None, None
        for line in lines:
            if line.startswith("Keyword: "):
                if keyword and url and summary:
                    if keyword not in summaries:
                        summaries[keyword] = []
                    summaries[keyword].append((url, summary))
                keyword = line.split("Keyword: ")[1].strip()
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
        if keyword and url and summary:
            if keyword not in summaries:
                summaries[keyword] = []
            summaries[keyword].append((url, summary))
    return summaries

def generate_blog_content_per_topic(topic, articles, client):
    prompt = f"Maak een blogpost op basis van de volgende samenvattingen voor het onderwerp '{topic}'. Voeg headers en opmaak toe, maar verzin geen extra inhoud en geen urls. Herschrijf de samenvatting naar een informele stijl. Gebruik de volgende structuur:\n"
    prompt += f"\n## {topic}\n"
    for url, summary in articles:
        prompt += f"### {url}\n{summary}\n"
    response = client.chat.completions.create(
        #model="gpt-3.5-turbo",
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Je bent een behulpzame assistent."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def generate_blog_content(summaries):
    client = OpenAI(api_key=OPENAI_API_KEY)
    blog_content = ""
    for topic, articles in summaries.items():
        blog_content += generate_blog_content_per_topic(topic, articles, client) + "\n"
    return blog_content

def main():
    # Bestandsnamen
    files_to_delete = [SUMMARIES_FILE, OUTPUT_FILE, BLOG_FILE ]

    # Verwijder de bestanden
    for file in files_to_delete:
       if os.path.exists(file):
           os.remove(file)
           print(f"{file} is verwijderd.")
       else:
           print(f"{file} bestaat niet.")
    #
    keywords = get_trending_topics()
    write_summary(keywords, SUMMARIES_FILE)
    print(f"Samenvattingen geschreven naar {SUMMARIES_FILE}")
    
    summaries = read_summaries(SUMMARIES_FILE)
    blog_content = generate_blog_content(summaries)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as file:
        for keyword, articles in summaries.items():
            file.write(f"### {keyword}\n")
            for url, summary in articles:
                file.write(f"Keyword: {keyword}\n")
                file.write(f"URL: {url}\n")
                file.write(f"Samenvatting: {summary}\n\n")

    with open(BLOG_FILE, 'w', encoding='utf-8') as file:
        file.write(blog_content)
    
    print(f"Blog content is geschreven naar '{BLOG_FILE}'")

if __name__ == "__main__":
    main()

