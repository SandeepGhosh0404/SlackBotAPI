import os
import requests
from dotenv import load_dotenv
from app.config import Config
from flask import  jsonify

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

def format_alert_response(response_data):
    rca = response_data.get("rca", "No RCA provided")
    insight = response_data.get("insight", "No insight available")
    resolution_steps = response_data.get("resolution_steps", [])

    # Format the resolution steps as a list
    formatted_resolution_steps = "\n".join([f"*Step {i + 1}:* {step}" for i, step in enumerate(resolution_steps)])

    # Create a formatted string for Slack
    formatted_message = (
        f"📢 *Alert Detected!*\n\n"
        f"*Root Cause Analysis (RCA):*\n"
        f"{rca}\n\n"
        f"*Insight:* \n"
        f"{insight}\n\n"
        f"*Resolution Steps:*\n"
        f"{formatted_resolution_steps}"
    )

    return formatted_message

def open_modal(trigger_id):
    """
    Call Slack's views.open API to display a modal.
    """
    url = 'https://slack.com/api/views.open'
    headers = {
        'Authorization': f'Bearer {Config.SLACK_BOT_TOKEN}',
        'Content-Type': 'application/json'
    }

    # Payload for the modal
    modal_view = {
        "trigger_id": trigger_id,
        "view": {
            "type": "modal",
            "callback_id": "modal-identifier",
            "title": {
                "type": "plain_text",
                "text": "Issue Tracking Form"
            },
            "submit": {
                "type": "plain_text",
                "text": "Submit"
            },
            "blocks": [
                # 🟢 Problem (Pre-filled, Mandatory)
                {
                    "type": "input",
                    "block_id": "problem_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "problem_input",
                        "initial_value": "Pre-filled problem description here"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Problem"
                    }
                },

                # 🟢 RCA (Pre-filled, Mandatory)
                {
                    "type": "input",
                    "block_id": "rca_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "rca_input",
                        "initial_value": "Pre-filled RCA here"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Root Cause Analysis (RCA)"
                    }
                },

                # 🟢 Long Term Fix (Mandatory)
                {
                    "type": "input",
                    "block_id": "long_term_fix_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "long_term_fix_input"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Long Term Fix"
                    }
                },

                # 🟢 Short Term Fix (Mandatory)
                {
                    "type": "input",
                    "block_id": "short_term_fix_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "short_term_fix_input"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Short Term Fix"
                    }
                },

                # 🟡 Remarks (Optional)
                {
                    "type": "input",
                    "block_id": "remarks_block",
                    "optional": True,  # This makes the field optional
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "remarks_input"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Remarks"
                    }
                },

                # 🟢 SPOC (Mandatory)
                {
                    "type": "input",
                    "block_id": "spoc_block",
                    "element": {
                        "type": "multi_users_select",  # Multi-user selection
                        "action_id": "spoc_input"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Select SPOCs"
                    }
                }
            ]
        }
    }

    response = requests.post(url, headers=headers, json=modal_view)
    print(f"Modal Open Response: {response.json()}")
