from flask import jsonify
from app.config import Config
from app.handlers.confluence_handlers import generate_table_row_html, get_confluence_page_data, update_confluence_page
from app.utils.utils import add_row_to_html_table


def handle_rca_submission(payload):
    state_values = payload["view"]["state"]["values"]
    problem = state_values["problem_block"]["problem_input"]["value"]
    rca = state_values["rca_block"]["rca_input"]["value"]
    long_term_fix = state_values["long_term_fix_block"]["long_term_fix_input"]["value"]
    short_term_fix = state_values["short_term_fix_block"]["short_term_fix_input"]["value"]
    remarks = state_values.get("remarks_block", {}).get("remarks_input", {}).get("value", "")
    spocs = state_values["spoc_block"]["spoc_input"]["selected_users"]

    print(f"Problem: {problem}")
    print(f"RCA: {rca}")
    print(f"Long Term Fix: {long_term_fix}")
    print(f"Short Term Fix: {short_term_fix}")
    print(f"Remarks: {remarks}")
    print(f"SPOCs: {', '.join(spocs)}")
    columns = [problem, rca, long_term_fix, short_term_fix, remarks]

    new_row = generate_table_row_html(columns)


    try:
        page = get_confluence_page_data(Config.CONFLUENCE_PAGE_ID)
        updated_content = add_row_to_html_table(page['body']['storage']['value'], new_row)
        new_version = page['version']['number'] + 1
        update_confluence_page(Config.CONFLUENCE_PAGE_ID, page['title'], updated_content, new_version)
        return jsonify({
            "response_action": "clear"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to update Confluence page: {str(e)}"}), 500
