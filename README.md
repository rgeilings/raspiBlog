# AI-Generated Dutch Blog

Project to create AI-generated blogPosts for a Wordpress site running in Docker containers on a Raspberry Pi. More than 95% of the code used for this project is "written" by AI. 

The docker-compose.yaml creates 4 Docker containers:

1. raspiblog_wordpress_1 to run the Wordpress website
2. raspiblog_db_1 to run the Wordpress database
3. raspiblog_python_1 to run the python scripts for generating blogPosts
4. raspiblog_pg_1 to run the postgreSQL database for storing raspiBlog articles and stats

After building and running the containers, the installation/configuration for the Wordpress site must be done manually via browser. For my personal website [renegeilings.nl](https://renegeilings.nl), I use Thema Janey from [www.themeinprogress.com](https://www.themeinprogress.com/)

Here is how I approach the generation of articles. All steps are automatically performed by AI:

## Step-by-Step Process

### Step 1: Check 3 Dutch news sites
Several times a day, the AI bot starts by 'reading' rtlniews.nl, NOS.nl and omroepbrabant.nl for latest news, sports news and entertainment news. This keeps me informed about what's happening and what people are talking about.

### Step 2: Scrape Articles
For each latest news, sports news and entertainment news, the AI bot reads these Dutch articles. A bit of scraping brings together a lot of interesting pieces. This is stored in the postreSQL database.

### Step 3: Create Summary for 6 random articles
Several times a day, the AI bot choose random 6 articles for latest news, sports news or entertainment news and write a summary for thes 6 articles.

### Step 4: Create AI Image
From this summary, the AI bot creates a DALL-E3 prompt to generate a image which reflects the summary. This way, there's always something nice to accompany the article.

### Step 5: Create Blogpost
With the summary and the image, the AI bot creates a complete blog post. This piece is then ready for publication.

### Step 6: Publish on renegeilings.nl
The blog post is automatically published on my site, [renegeilings.nl](https://renegeilings.nl), in the category "gegenereerd met AI." This ensures there's something new and interesting on my blog every day.

## How to Run the Project

### Prerequisites

- Raspberry Pi
- Docker and docker-compose

### Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/rgeilings/raspiBlog.git
   cd raspiBlog
   ```
2. **adjust the docker-compose.yaml and  scripts/.env files**
   ```bash
   vi docker-compose.yaml
   cd ./scripts
   vi.env
   ```
3. Build and Run Docker Containers
   ```bash
   docker-compose up -d --build
4. Configure Wordpres manually via browser   ```
5. Use the postLaatsteXXXXXXX.sh scripta to generate a blogPost. You can use this scripts in the crontab
   ```bash
   ./postTrendingBlog.sh
    ```
## License
This project is licensed under the MIT License.

## Acknowledgments

- AI content generation powered by OpenAI
- Image generation powered by DALL-E 3
- Hosted on a Raspberry Pi with Docker and Docker-compose

---

Feel free to reach out if you have any questions or feedback. Enjoy exploring the world of AI with me!

---

For more detailed information, visit the specific pages on [renegeilings.nl](https://renegeilings.nl) (in Dutch):  "verzamelen data", "maak blogpost met AI" en "post blogpost"

---

