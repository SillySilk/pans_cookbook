import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin
import time

# --- Configuration ---

# Define your user-agent. Some websites block requests without a known user-agent.
USER_AGENT = "HerbalAlchemyRecipeBot/1.0"

# The target URL you want to scrape.
TARGET_URL = "https://blog.mountainroseherbs.com/herbal-chapstick-recipe" # Example URL

# --- Main Scraping Logic ---

def get_robots_url(base_url):
    """Constructs the full URL for the robots.txt file."""
    return urljoin(base_url, "robots.txt")

def can_fetch(url_to_check):
    """Checks if the website's robots.txt allows fetching the given URL."""
    base_url = requests.utils.urlparse(url_to_check)._replace(path="", params="", query="", fragment="").geturl()
    robots_url = get_robots_url(base_url)
    
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
        # Add a small delay to be respectful to the server
        time.sleep(1) 
        allowed = rp.can_fetch(USER_AGENT, url_to_check)
        if not allowed:
            print(f"Scraping disallowed by {robots_url} for URL: {url_to_check}")
        return allowed
    except Exception as e:
        print(f"Could not fetch or parse robots.txt at {robots_url}. Error: {e}")
        # Fail safely - if we can't read robots.txt, we assume we can't scrape.
        return False

def scrape_recipe(url):
    """
    Scrapes a single recipe page if allowed by robots.txt.
    This function is a TEMPLATE and needs to be customized for each website.
    """
    print(f"Attempting to scrape: {url}")
    
    # 1. Check robots.txt first
    if not can_fetch(url):
        return None

    # 2. Fetch the HTML content
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raises an exception for bad status codes (4xx or 5xx)
    except requests.RequestException as e:
        print(f"Failed to retrieve the webpage. Error: {e}")
        return None

    # 3. Parse the HTML
    soup = BeautifulSoup(response.content, 'html.parser')

    # 4. Extract the data
    #    !!!! THIS IS THE PART YOU MUST CUSTOMIZE !!!!
    #    You need to use your browser's "Inspect" tool to find the correct
    #    tags, classes, and IDs for the data you want from the target website.
    #    The selectors below are HYPOTHETICAL examples.
    try:
        name = soup.find('h1', class_='post-title').get_text(strip=True)
        description = soup.find('meta', attrs={'name': 'description'})['content']
        
        # For instructions, you might need to find a specific div and get all list items
        instructions_div = soup.find('div', class_='recipe-instructions')
        instructions_list = instructions_div.find_all(['p', 'li'])
        instructions = "\\n".join([f"{i+1}. {item.get_text(strip=True)}" for i, item in enumerate(instructions_list)])

        # Benefits might be in a similar section
        benefits_div = soup.find('div', id='recipe-benefits')
        benefits = benefits_div.get_text(strip=True) if benefits_div else "Not specified."

        # You would also extract ingredients and then manually map them to your herb IDs
        # For now, we'll leave these fields to be filled in manually.
        recipe_data = {
            "id": 901, # You'll need a system for generating new IDs
            "name": name,
            "description": description,
            "instructions": instructions,
            "benefits": benefits,
            "category": "Balm", # Manually categorize for now
            "required_herb_ids": "" # Manually add these later (e.g., "1;6")
        }
        return recipe_data
    except AttributeError as e:
        print(f"Could not find an expected element on the page. The site's structure may have changed. Error: {e}")
        return None

if __name__ == "__main__":
    scraped_data = scrape_recipe(TARGET_URL)
    if scraped_data:
        print("\n--- Successfully Scraped Data ---")
        print(scraped_data)
        # To save, you would append this dict to a list and then create a DataFrame
        # df = pd.DataFrame([scraped_data])
        # df.to_csv('new_recipes.csv', mode='a', header=False, index=False)
        print("\nNOTE: Data not saved. Uncomment the lines in the script to save to 'new_recipes.csv'.")

