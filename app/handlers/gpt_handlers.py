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
                "content": """You are an assistant specializing in generating detailed and actionable Root Cause Analysis (RCA) for system alerts.
                When provided with an alert description, your response should include the alert ( Heading of alert or a kind of summary ) most likely root cause, any useful insights, and a list of clear, actionable steps to resolve or investigate the issue.
                Your response should be in the following JSON format:
                {
                    "alert":["string (max 40 characters)"],
                    "rca": ["string (max 40 characters)"],
                    "insight": "string (max 100 characters)",
                    "resolution_steps": [
                        "step 1",
                        "step 2",
                        "step 3"
                    ]
                }
                The 'alert' field should be a short and brief description of the alert
                The 'rca' field should be a short description of the root cause (at least 20 words, no more than 40 characters).
                The 'insight' field should provide valuable context, including possible causes, network conditions, or recent changes.
                The 'resolution_steps' should provide at least 3 actionable steps that can help resolve the issue or mitigate it, such as investigating processes, checking system logs, optimizing configurations, or scaling resources. Each step should be concise but informative."""
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


def get_alert_info_with_context(alert, historical_data=None):
    if historical_data:
        prompt = f"""
        The following is information from a previous discussion regarding alert analysis:

        *Previous RCA(s)*: {historical_data.get('rca', 'N/A')}
        *Short-Term Fixes*: {historical_data.get('short_term_fixes', 'N/A')}
        *Long-Term Fixes*: {historical_data.get('long_term_fixes', 'N/A')}
        *SPOC*: {historical_data.get('spoc', 'N/A')}
        *Priority*: {historical_data.get('priority', 'N/A')}

        Current alert:
        *Alert*: {alert}

        Based on the above, generate the RCA, insight, and resolution steps that incorporate both the previous information and your own analysis.
        """
    else:
        prompt = f"""
        A new alert has been detected:
        *Alert*: {alert}

        Please analyze the alert and provide:
        1. Root Cause Analysis (RCA)
        2. Insight
        3. Resolution steps

        Provide suggestions based on your analysis of the alert.
        """

    # Make the GPT API call
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": "You are an assistant specializing in monitoring alerts and providing RCA, insights, and resolution steps."},
            {"role": "user", "content": prompt}
        ]
    )

    # Extract and return the response
    response_content = completion.choices[0].message.content

    try:
        response_data = json.loads(response_content)  # Ensure it parses as valid JSON
    except json.JSONDecodeError:
        response_data = {"error": "Invalid response format", "raw_content": response_content}

    return response_data

