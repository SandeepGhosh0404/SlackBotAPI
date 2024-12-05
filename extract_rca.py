from openai import OpenAI
from app.config import Config

client = OpenAI(api_key=Config.OPENAI_API_KEY)

# Initialize the Flask app
def get_gpt_response(prompt):
    """
    This function takes a prompt and returns a response from GPT-4.
    """
    try:
        response = client.chat.completions.create(
             model="gpt-4o-mini",
             messages=[{"role": "user", "content": prompt}],
            max_tokens=150,  # Limit the response length
            temperature=0.7  # Adjust creativity level
        )
        # Extract and return the content
        return response
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Example usage
if __name__ == "__main__":
    user_input = "Explain the concept of gravity in simple terms."
    output = get_gpt_response(user_input)
    print("GPT-4 Response:", output)