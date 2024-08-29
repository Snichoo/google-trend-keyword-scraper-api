from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import time
import agentql
from playwright.sync_api import sync_playwright
import logging

# Load environment variables from the .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',  # Make sure the format string is correct
)

# Suppress Flask's default logging to avoid conflicts
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)  # Set this to ERROR or higher to suppress unwanted logs

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Get the AgentQL API key from the environment variables
AGENTQL_API_KEY = os.getenv("AGENTQL_API_KEY")

# Ensure the API key is present
if not AGENTQL_API_KEY:
    logger.error("AgentQL API key is missing. Please set it in the .env file.")
    raise ValueError("AgentQL API key is missing.")

logger.info("AgentQL API key loaded successfully.")

# Define the AgentQL query to extract related queries
RELATED_QUERIES_QUERY = """
{
    related_queries[] {
        query
    }
}
"""

# Function to scrape the website and return related queries
def fetch_related_queries(url):
    logger.info(f"Starting to fetch related queries from {url}")

    with sync_playwright() as playwright:
        logger.info("Launching Chromium browser...")
        browser = playwright.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",  # Helps to avoid detection
            ],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        page = agentql.wrap(browser.new_page())
        page.set_viewport_size({"width": 1280, "height": 800})

        logger.info(f"Navigating to {url}")
        page.goto(url)
        page.wait_for_load_state('domcontentloaded')
        logger.info("Page loaded successfully")

        retries = 0
        max_retries = 5
        while retries < max_retries:
            if "too many requests" in page.content().lower():
                logger.warning("Too many requests detected. Refreshing the page.")
                page.reload()
                retries += 1
                logger.info(f"Retry {retries}/{max_retries}")
            else:
                logger.info("No 'too many requests' error detected")
                break

        if retries == max_retries:
            logger.error("Max retries reached. Exiting...")
            return []

        logger.info("Scrolling down to load all content")
        scroll_height = page.evaluate("document.body.scrollHeight")
        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            logger.info("Scrolled to bottom, waiting for content to load...")
            time.sleep(2)
            new_scroll_height = page.evaluate("document.body.scrollHeight")
            if new_scroll_height == scroll_height:
                logger.info("No new content loaded after scrolling")
                break
            logger.info("New content detected, scrolling again...")
            scroll_height = new_scroll_height

        logger.info("Querying related queries using AgentQL...")
        related_queries_response = page.query_data(RELATED_QUERIES_QUERY)
        related_queries = related_queries_response.get("related_queries", [])

        logger.info(f"Related queries fetched successfully: {related_queries}")
        return related_queries

@app.route('/fetch_related_queries', methods=['POST'])
def fetch_related():
    logger.info("Received request to fetch related queries")
    data = request.json
    url = data.get('url')
    
    if not url:
        logger.error("URL is missing in the request")
        return jsonify({"error": "URL is required"}), 400

    try:
        logger.info(f"Fetching related queries from URL: {url}")
        related_queries = fetch_related_queries(url)
        logger.info("Returning related queries to client")
        return jsonify({"related_queries": related_queries}), 200
    except Exception as e:
        logger.error(f"Error fetching related queries: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

PORT = int(os.getenv("PORT", 5000))

if __name__ == "__main__":
    logger.info(f"Starting Flask server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT)
