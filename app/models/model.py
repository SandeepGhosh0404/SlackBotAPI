import json
import numpy as np
from sentence_transformers import SentenceTransformer, util

class SolutionModel:
    def __init__(self, db_file='solutions_db.json'):
        """Initialize the SolutionModel with the model and database file."""
        # Load the sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Database file path
        self.db_file = db_file
        
        # Load solutions database from JSON
        self.solutions_db = self.load_solutions_db()

    def load_solutions_db(self):
        """Load the solutions from the JSON file."""
        try:
            with open(self.db_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # If the file doesn't exist, initialize with an empty dictionary
            return {}

    def save_solutions_db(self):
        """Save the solutions to the JSON file."""
        with open(self.db_file, 'w') as f:
            json.dump(self.solutions_db, f, indent=4)

    def calculate_similarity(self, new_question, stored_questions):
        """Calculate the similarity between the new question and stored questions."""
        # Encode the sentences and the new question
        sentence_embeddings = self.model.encode(stored_questions)
        new_question_embedding = self.model.encode([new_question])

        # Compute cosine similarity
        cosine_scores = util.pytorch_cos_sim(new_question_embedding, sentence_embeddings)

        # Convert cosine_scores to a Python list (which is JSON serializable)
        cosine_scores_list = cosine_scores.cpu().detach().numpy().tolist()

        # Get the index of the most similar sentence
        most_similar_index = np.argmax(cosine_scores_list)

        # Get the similarity score for the most similar sentence
        similarity_score = cosine_scores_list[0][most_similar_index]

        return most_similar_index, similarity_score

    def get_solution(self, new_question):
        """Get the solution for the most similar question."""
        stored_questions = list(self.solutions_db.keys())
        if not stored_questions:
            return None, 0.0

        most_similar_index, similarity_score = self.calculate_similarity(new_question, stored_questions)

        # If similarity is above 60%, return the solution
        if similarity_score > 0.6:
            return self.solutions_db[stored_questions[most_similar_index]], similarity_score
        else:
            return None, similarity_score

    def store_solution(self, question, rca, solution):
        """Store the RCA and solution in the JSON database."""
        self.solutions_db[question] = {"rca": rca, "solution": solution}
        self.save_solutions_db()
        return "Solution stored successfully"

    def store_solutions_bulk(self, solutions):
        """Store multiple RCA and solution pairs in bulk."""
        success_count = 0
        for solution_data in solutions:
            question = solution_data.get('question')
            rca = solution_data.get('rca')
            solution = solution_data.get('solution')

            if question and rca and solution:
                self.store_solution(question, rca, solution)
                success_count += 1

        return success_count