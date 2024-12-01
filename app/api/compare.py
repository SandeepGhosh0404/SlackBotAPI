from flask import Blueprint, request, jsonify
from app.models.model import SolutionModel

compare_bp = Blueprint('compare', __name__)

# Initialize SolutionModel
solution_model = SolutionModel()

@compare_bp.route('/compare', methods=['POST'])
def compare_sentences():
    try:
        # Get the data from the request
        data = request.get_json()
        new_question = data['new_question']

        # Get the solution for the new question
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
        # In case of any error, return an error message
        return jsonify({"error": str(e)}), 400


@compare_bp.route('/store_solution', methods=['POST'])
def store_solution():
    try:
        # Get the data from the request
        data = request.get_json()
        question = data['question']
        rca = data['rca']
        solution = data['solution']

        # Store the RCA and solution
        message = solution_model.store_solution(question, rca, solution)

        return jsonify({"message": message})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
