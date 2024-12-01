import os
import requests
from dotenv import load_dotenv
from app.config import Config

load_dotenv()

def get_confluence_page_data(page_id):
    # Get environment variables
    base_url = Config.CONFLUENCE_BASE_URL
    username = Config.CONFLUENCE_USERNAME
    api_token = Config.CONFLUENCE_API_TOKEN

    url = f"{base_url}/rest/api/content/{page_id}?expand=body.storage,version"
    response = requests.get(url, auth=(username, api_token))

    if response.status_code != 200:
        raise Exception(f"Error fetching Confluence page: {response.status_code}, {response.text}")
    
    return response.json()

def add_row_to_html_table(html_content, new_row):
    tbody_end = "</tbody>"
    tbody_end_index = html_content.find(tbody_end)
    
    if tbody_end_index == -1:
        return html_content
    
    html_content = html_content[:tbody_end_index] + new_row + html_content[tbody_end_index:]
    return html_content