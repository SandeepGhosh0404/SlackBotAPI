from flask import Blueprint, request, jsonify
from app.models.model import SolutionModel
from app.handlers.confluence_handlers import get_confluence_page, generate_table_row_html, update_confluence_page, get_confluence_page_data
from app.utils.utils import add_row_to_html_table
from app.handlers.slack_handlers import respond_to_mention

compare_bp = Blueprint('compare', __name__)

processed_events = set()
solution_model = SolutionModel()

@compare_bp.route('/compare', methods=['POST'])
def compare_sentences():
    try:
        data = request.get_json()
        new_question = data['new_question']

        solution, similarity_score = solution_model.get_solution(new_question)

        if solution is not None:
            return jsonify({
                "answer": solution["solution"],
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
        else:  # Single solution request
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
        print(page)
        updated_content = add_row_to_html_table(page['body']['storage']['value'], new_row)
        new_version = page['version']['number'] + 1
        update_confluence_page(page_id, page['title'], updated_content, new_version)
        return jsonify({"message": "Row added successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update Confluence page: {str(e)}"}), 500

@compare_bp.route('/slack/events', methods=['POST'])
def events_handler():
    """Handles incoming Slack events."""
    try:
        slack_event = request.get_json()

        # Verify the URL challenge
        if slack_event.get('type') == 'url_verification':
            return jsonify({'challenge': slack_event.get('challenge')})

        # Handle event callback (e.g., app_mention)
        if slack_event.get('type') == 'event_callback':
            event = slack_event.get('event', {})
            if event.get('type') == 'app_mention':
                print(f"Mention received: {event.get('text')}")

                # Get the unique client_msg_id to track processed events
                client_msg_id = event.get('client_msg_id')

                # If the event has already been processed, ignore it
                if client_msg_id in processed_events:
                    print(f"Duplicate event detected. Ignoring.")
                    return '', 200

                # Store the event ID to prevent future duplicates
                processed_events.add(client_msg_id)

                # Process the event
                channel = event.get('channel')
                text = event.get('text')
                thread_ts = event.get('thread_ts')  # Check if the event is part of a thread
                respond_to_mention(channel, text, thread_ts)

        return '', 200

    except Exception as e:
        print(f"Error handling Slack event: {e}")
        return jsonify({'error': str(e)}), 500