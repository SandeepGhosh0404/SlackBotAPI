import json
from typing import Dict
from openai import OpenAI, BaseModel
import os
from app.config import Config

client = OpenAI(api_key = "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")


class AlertResponse(BaseModel):
    rca: list[str]


def get_alert_info(alert):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": """You are an assistant specializing in monitoring alerts. Generate RCA details strictly in the following JSON schema:
                {
                    "rca": [
                        "string (max 40 characters)",
                    ]
                }
                Each string in 'rca' should be a brief and most possible description of the root cause analysis, and there should be no more than 1 elements. Make the 'rca' brief such that i can be useful ( atleast 20 words)."""
            },
            {"role": "user", "content": alert}
        ]
    )

    # Extract content
    response_content = completion.choices[0].message.content

    try:
        response_data = json.loads(response_content)  # Ensure it parses as valid JSON
    except json.JSONDecodeError:
        response_data = {"error": "Invalid response format", "raw_content": response_content}

    return response_data


def analyze_sentence(sentence: str) -> Dict[str, str]:
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": """You are a troubleshooting assistant specializing in identifying problems, root causes, and solutions. 
                Analyze the input sentence and return the result in the following JSON format:
                {
                    "problem": "A concise description of the problem (if found, max 100 characters).",
                    "rca": "A brief explanation of the root cause analysis (if found, max 100 characters).",
                    "solution": "A short, actionable solution (if found, max 100 characters)."
                }
                If any of the fields are not applicable, leave them empty. Preserve the technical context accurately. 
                Also, if needed, you can add some important technical information."""
            },
            {"role": "user", "content": sentence}
        ]
    )

    response_content = completion.choices[0].message.content

    response_data = {
        "problem": "",
        "rca": "",
        "solution": ""
    }

    try:
        response_data.update(eval(response_content))
    except (SyntaxError, ValueError):
        response_data["error"] = "Response format was not valid JSON."

    return response_data


