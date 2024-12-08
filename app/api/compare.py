from flask import Blueprint, request, jsonify
from slack_sdk.errors import SlackApiError
from app.models.classifier import classify_message, categorize_message
from app.handlers.gpt_handlers import get_alert_info, analyze_sentence
from app.models.model import SolutionModel
from app.handlers.confluence_handlers import get_confluence_page, generate_table_row_html, update_confluence_page, get_confluence_page_data
from app.utils.utils import add_row_to_html_table, remove_bot_mention
from PIL import Image
import pytesseract
from slack_sdk import WebClient
from app.config import Config
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from app.utils.utils import format_alert_response,open_modal
from app.handlers.common import handle_rca_submission, handle_issue_submission
from slack_sdk.signature import SignatureVerifier
import json
import re

compare_bp = Blueprint('compare', __name__)

processed_events = set()
solution_model = SolutionModel()
app = App(token=Config.SLACK_BOT_TOKEN, signing_secret=Config.SIGNING_SECRET)
handler = SlackRequestHandler(app)
signature_verifier = SignatureVerifier(Config.SIGNING_SECRET)
client = WebClient(token=Config.SLACK_BOT_TOKEN)

@compare_bp.route('/compare', methods=['POST'])
def compare_sentences():
    try:
        data = request.get_json()
        new_question = data['new_question']

        solution, similarity_score = solution_model.get_solution(new_question)
        if solution is not None:
            return jsonify({
                "answer": solution["rca"],
                "similarity_score": similarity_score
            })
        else:
            return jsonify({
                "message": "No similar question found. Please provide the RCA and solution.",
                "similarity_score": similarity_score
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@compare_bp.route('/store_solution', methods=['POST'])
def store_solution():
    try:
        data = request.get_json()

        if isinstance(data, list):
            success_count = solution_model.store_solutions_bulk(data)
            return jsonify({"message": f"{success_count} solutions stored successfully"})
        else:
            question = data['question']
            rca = data['rca']
            solution = data['solution']
            message = solution_model.store_solution(question, rca, solution)
            return jsonify({"message": message})

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@compare_bp.route('/confluence/table', methods=['GET'])
def confluence_table():
    page_id = request.args.get('pageID')
    if not page_id:
        return jsonify({"error": "Page ID is required"}), 400
    
    try:
        table_data = get_confluence_page(page_id)
        return jsonify(table_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@compare_bp.route('/confluence/add-row',methods=['POST'])
def add_row_to_confluence():
    request_data = request.get_json()
    page_id = request_data.get("page_id")
    columns = request_data.get("columns")
    
    if not page_id or not columns:
        return jsonify({"error": "Page ID and Columns are required"}), 400

    new_row = generate_table_row_html(columns)

    try:
        page = get_confluence_page_data(page_id)
        updated_content = add_row_to_html_table(page['body']['storage']['value'], new_row)
        new_version = page['version']['number'] + 1
        update_confluence_page(page_id, page['title'], updated_content, new_version)
        return jsonify({"message": "Row added successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update Confluence page: {str(e)}"}), 500

@compare_bp.route('/sync-confluence', methods=['GET'])
def sync_confluence():
    page_id = request.args.get('pageID')
    if not page_id:
        return jsonify({"error": "Page ID is required"}), 400
    try:
        result= []
        table_data = get_confluence_page(page_id)
        print(table_data)
        for row in table_data[1:]:
            alert, rca, short_term_fix, long_term_fix,remarks,spoc = row
            result.append({
                "alert": alert,
                "rca": rca,
                "short_term_fix": short_term_fix,
                "long_term_fix": long_term_fix,
                "remarks": remarks,
                "spoc": spoc
            })
        success_count = solution_model.store_solutions_bulk(result)
        return jsonify({"message": f"{success_count} solutions stored successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@compare_bp.route('/alerts_info', methods=['GET'])
def alert_info():
    alert = request.json.get("alert", "")
    if not alert:
        return jsonify({"error": "No alert message provided"}), 400

    result = get_alert_info(alert)
    return jsonify(result)

@compare_bp.route('/analyze', methods=['POST'])
def analyze():
    """
    API endpoint to analyze a given sentence.
    Expects a JSON payload with a "sentence" key.
    """
    try:
        data = request.get_json()
        if not data or "sentence" not in data:
            return jsonify({"error": "Missing 'sentence' in request payload"}), 400

        sentence = data["sentence"]

        # Analyze the sentence
        result = analyze_sentence(sentence)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@compare_bp.route('/classify', methods=['POST'])
def classify():
    data = request.get_json()

    if 'message' not in data:
        return jsonify({"error": "Missing 'message' in request"}), 400

    message = data['message']

    # Classify the message

    classification_result = classify_message(message)
    category = categorize_message(classification_result.get("label"))

    return jsonify(category), 200

@compare_bp.route('/extract-text', methods=['POST'])
def extract_text():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files['image']
    try:
        image = Image.open(image_file)
        text = pytesseract.image_to_string(image)
        return jsonify({"text": text}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@compare_bp.route("/slack/command", methods=['POST'])
def handle_slash_command():
    try:
        response = jsonify({
            "response_type": "ephemeral",
            "text": "Opening the Finance On-Call modal..."
        })
        response.status_code = 200

        client.views_open(
            trigger_id=request.form["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "issue_modal",
                "title": {"type": "plain_text", "text": "Finance On-Call Bot"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "issue_block",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "issue_input",
                            "multiline": True
                        },
                        "label": {"type": "plain_text", "text": "Issue (Required)"},
                        "optional": False
                    }
                ],
                "submit": {"type": "plain_text", "text": "Submit"}
            },
        )

    except Exception as e:
        print(f"Error opening modal: {e}")
        response = jsonify({"response_type": "ephemeral", "text": "Failed to open modal."})
        response.status_code = 500

    return response

@compare_bp.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

@app.event("message")
def handle_message(event, say, client):
    """Listen for messages in the specified channel and respond."""
    channel_id = event.get('channel')
    message_ts = event.get('ts')
    message_text = event.get('text')
    user = event.get('user')
    bot_id = event.get('bot_id')
    thread_ts = event.get('thread_ts')

    print(message_text)

    if thread_ts or message_text[0:8] !="*<https:":
        print("This is a reply in a thread. Skipping processing.")
        return

    if channel_id == Config.ALERT_CHANNEL_ID and user and not bot_id:
        gpt_response = get_alert_info(message_text)
        formatted_message, alert, rca, insight, formatted_resolution_steps = format_alert_response(gpt_response)
        client.chat_postMessage(
            channel=channel_id,
            text=formatted_message,
            thread_ts=message_ts,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": formatted_message  # Adding the formatted RCA message here
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Would you like to provide an RCA for this alert?"
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Provide RCA",
                            "emoji": True
                        },
                        "value": "provide_rca",
                        "action_id": "button-action"
                    }
                }
            ]
        )

@compare_bp.route("/slack/interact", methods=["POST"])
def slack_interact():
    try:
        raw_payload = request.form.get('payload')
        if not raw_payload:
            return jsonify({'error': 'No payload found'}), 400

        payload = json.loads(raw_payload)
        user_id = payload['user']['id']
        action_id = payload.get('actions', [])
        if action_id:
            action_id = action_id[0].get('action_id', None)
        else:
            action_id = None
        print(payload)

        if payload.get("type") == "view_submission" and payload.get("view",{}).get("callback_id")!="issue_modal":
            return handle_rca_submission(payload)

        elif payload.get("view",{}).get("callback_id")=="issue_modal":
            issue = handle_issue_submission(payload)
            solution,similarity= solution_model.get_solution(issue)
            return send_message_to_channel(Config.DOC_GEN_CHANNEL_ID,issue,solution)

        elif action_id == 'button-action':
            print("Clicked")
            trigger_id = payload['trigger_id']
            open_modal(trigger_id)
            return jsonify({
                'response_type': 'ephemeral',
                'text': f"Hey <@{user_id}>, you clicked Button 1!"
            })

        elif action_id == 'button_action_2':
            return jsonify({
                'response_type': 'ephemeral',
                'text': f"Hey <@{user_id}>, you clicked Button 2!"
            })

        else:
            return jsonify({'error': 'Unknown action'}), 400

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@compare_bp.route("/slack/rca", methods=['POST'])
def handle_rca_command():
    if "thread_ts" not in request.form:
        response = jsonify({
            "response_type": "ephemeral",
            "text": "The /rca command can only be used in threads. Please use it within a thread."
        })
        response.status_code = 200
        return response

    try:
        client.views_open(
            trigger_id=request.form["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "modal_submission",
                "title": {"type": "plain_text", "text": "Finance on call bot"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "user_input_block",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "user_input_action",
                        },
                        "label": {"type": "plain_text", "text": "Enter something:"},
                    }
                ],
                "submit": {"type": "plain_text", "text": "Submit"},
            },
        )
    except SlackApiError as e:
        print(f"Error opening modal: {e.response['error']}")

    return jsonify({"response_type": "ephemeral"}), 200

@app.event("app_mention")
def handle_mention(event, say):
    """Handles @mention of the bot."""
    user_id = event.get("user")
    channel_id = event.get("channel")
    thread_ts = event.get("thread_ts")
    message_ts = event.get("ts")
    text = event.get("text")
    cleaned_text = text.replace(f"<@{app.client.auth_test()['user_id']}>", "").strip()
    solution, similarity_score = solution_model.get_solution(cleaned_text)

    if solution is None:
        if thread_ts:
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,  # Reply in the thread
                text="Please provide the RCA and solution.",
                mrkdwn=True
            )
        else:
            thread_ts = message_ts  # Capture the timestamp of the new message
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,  # Reply in the thread
                text="Please provide the RCA and solution.",
                mrkdwn=True
            )

        return jsonify({"response_action": "clear"})


    blocks = [
        {
            "type": "section",
            "block_id": "solution_section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Issue:* {cleaned_text}\n\n"
                        f"*Root Cause Analysis (RCA):*\n{solution['rca']}\n\n"
                        f"*Short-Term Fix:*\n{solution['short_term_fix']}\n\n"
                        f"*Long-Term Fix:*\n{solution['long_term_fix']}\n\n"
                        f"*Remarks:*\n{solution['remarks']}\n\n"
                        f"*SPOC:*\n{solution['spoc']}\n\n"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Add RCA"
                    },
                    "action_id": "button-action",
                    "value": "add_rca"
                }
            ]
        }
    ]

    try:
        if thread_ts:
            response = say(
                text="Replying with solution",
                thread_ts=thread_ts,
                blocks=blocks
            )
        else:
            response = say(
                text="Replying with solution",
                thread_ts=message_ts,
                blocks=blocks
            )

        print(f"Message sent successfully: {response}")

    except Exception as e:
        print(f"Error occurred while sending message: {str(e)}")
        return jsonify({"error": "Failed to send message"}), 500

    return "", 200

def send_message_to_channel(channel_id,issue, solution):

    if solution is None:
        client.chat_postMessage(
            channel=channel_id,
            text="Please provide the RCA and solution.",
            mrkdwn=True
        )
        return jsonify({"response_action": "clear"})

    try:
        client.chat_postMessage(
            channel=channel_id,
            text=f"*Issue:* {issue}\n\n"
                        f"*Root Cause Analysis (RCA):*\n{solution['rca']}\n\n"
                        f"*Short-Term Fix:*\n{solution['short_term_fix']}\n\n"
                        f"*Long-Term Fix:*\n{solution['long_term_fix']}\n\n"
                        f"*Remarks:*\n{solution['remarks']}\n\n"
                        f"*SPOC:*\n{solution['spoc']}\n\n",
            mrkdwn=True
        )
        return jsonify({"response_action": "clear"})
    except SlackApiError as e:
        return jsonify({"error": f"Failed to send message: {e.response['error']}"})