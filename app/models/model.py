import json
import numpy as np
from sentence_transformers import SentenceTransformer, util

class SolutionModel:
    def __init__(self, db_file='solutions_db.json'):
        """Initialize the SolutionModel with the model and database file."""
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        self.db_file = db_file

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

        cosine_scores = util.pytorch_cos_sim(new_question_embedding, sentence_embeddings)

        cosine_scores_list = cosine_scores.cpu().detach().numpy().tolist()

        most_similar_index = np.argmax(cosine_scores_list)

        similarity_score = cosine_scores_list[0][most_similar_index]

        return most_similar_index, similarity_score

    def get_solution(self, new_question):
        """Get the solution for the most similar question."""
        stored_questions = list(self.solutions_db.keys())
        if not stored_questions:
            return None, 0.0

        most_similar_index, similarity_score = self.calculate_similarity(new_question, stored_questions)

        print(most_similar_index)

        if similarity_score > 0.6:
            return self.solutions_db[stored_questions[most_similar_index]], similarity_score
        else:
            return None, similarity_score

    def store_solution(self, alert, rca, short_term_fix, long_term_fix="NA", remarks="NA", spoc="NA"):
        """Store the RCA and solution in the JSON database."""
        self.solutions_db[alert] = {"rca": rca, "short_term_fix": short_term_fix, "long_term_fix": long_term_fix,"remarks": remarks, "spoc": spoc}
        self.save_solutions_db()
        return "Solution stored successfully"

    def store_solutions_bulk(self, solutions):
        """Store multiple RCA and solution pairs in bulk."""
        success_count = 0
        for solution_data in solutions:
            alert = solution_data.get('alert')
            rca = solution_data.get('rca')
            short_term_fix = solution_data.get('short_term_fix')
            long_term_fix = solution_data.get('long_term_fix')
            remarks = solution_data.get('remarks')
            spoc = solution_data.get('spoc')

            if alert and rca and short_term_fix:
                self.store_solution(alert, rca, short_term_fix,long_term_fix,remarks,spoc)
                success_count += 1

        return success_count