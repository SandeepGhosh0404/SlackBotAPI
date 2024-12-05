from flask import Flask, request, jsonify
from transformers import pipeline


classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

candidate_labels = [
    "AWS alert",
    "system alert",
    "user query",
    "incident explanation",
    "actionable advice",
    "incident"
    "new relic query"
]

def categorize_message(message_type: str) -> str:
    type_mapping = {
        "AWS alert": "ALERT",
        "system alert": "ALERT",
        "user query": "QUERY",
        "incident explanation": "INCIDENT",
        "incident": "INCIDENT",
        "new relic alert": "ALERT",
        "actionable advice": "SOLUTION",
    }

    return type_mapping.get(message_type, "UNKNOWN")


def classify_message(message: str) -> dict:
    result = classifier(message, candidate_labels)
    return {
        "label": result['labels'][0],
        "confidence": result['scores'][0]
    }