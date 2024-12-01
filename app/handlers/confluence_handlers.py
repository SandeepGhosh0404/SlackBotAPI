import json
import requests
from bs4 import BeautifulSoup
from app.utils.utils import get_confluence_page_data
from app.config import Config

def get_confluence_page(page_id):
    page_data = get_confluence_page_data(page_id)
    
    if not page_data or 'body' not in page_data or 'storage' not in page_data['body']:
        raise ValueError("No valid content found on the page")
    
    page_content = page_data['body']['storage']['value']
    
    table_data = parse_table_from_confluence_page(page_content)
    
    if not table_data:
        raise ValueError("No table data found on the page")
    
    return table_data

def parse_table_from_confluence_page(page_content):
    soup = BeautifulSoup(page_content, 'html.parser')
    table_data = []

    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            row_data = []
            for cell in row.find_all(['td', 'th']):
                row_data.append(cell.get_text(strip=True))
            if row_data:
                table_data.append(row_data)
    
    return table_data

def update_confluence_page(page_id, title, new_content, version):
    base_url = Config.CONFLUENCE_BASE_URL
    username = Config.CONFLUENCE_USERNAME
    api_token = Config.CONFLUENCE_API_TOKEN
    url = f"{base_url}/rest/api/content/{page_id}"

    payload = {
        "version": {"number": version},
        "title": title,
        "type": "page",
        "body": {
            "storage": {
                "value": new_content,
                "representation": "storage"
            }
        }
    }

    headers = {"Content-Type": "application/json"}
    response = requests.put(url, json=payload, auth=(username, api_token), headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Failed to update page: {response.text}")

def generate_table_row_html(columns):
    row = "<tr>"
    for column in columns:
        row += f"<td>{column}</td>"
    row += "</tr>"
    return row