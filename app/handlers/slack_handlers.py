import re
import requests
import logging
from app.config import Config
from app.api.compare import SolutionModel

def respond_to_mention(channel, text, thread_ts=None):
    """Responds to a mention with a solution or a default message."""
    try:
        token = Config.SLACK_BOT_TOKEN
        if not token:
            logging.error("SLACK_BOT_TOKEN is not set")
            return

        mention_regex = re.compile(r"<@[\w\d]+>")
        clean_text = mention_regex.sub('', text).strip()

        solution_model = SolutionModel()
        solution, similarity_score = solution_model.get_solution(new_question=clean_text)

        if solution is None:
            solution = "No similar question found. Please provide the RCA and solution."


        message_payload = {
            'channel': channel,
            'text': solution['solution'],
            'response_type': 'in_channel',
        }

        if thread_ts:
            message_payload["thread_ts"] = thread_ts

        slack_url = "https://slack.com/api/chat.postMessage"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        response = requests.post(slack_url, json=message_payload, headers=headers)

        if response.status_code != 200:
            logging.error(f"Failed to send message to Slack: {response.text}")
        else:
            logging.info(f"Response sent to Slack: {clean_text}")

    except Exception as e:
        logging.error(f"Error responding to mention: {e}")