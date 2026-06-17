"""
agents.py — Multi-agent banking support pipeline (AG2 + Groq).
"""

import json, os, re
from dotenv import load_dotenv
load_dotenv()

# Works locally (.env) AND on Streamlit Cloud (st.secrets)
try:
    import streamlit as st
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
except Exception:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

import autogen
from database import create_ticket, get_ticket, update_ticket_status


GROQ_CONFIG = {
    "config_list": [{
        "model": "llama-3.3-70b-versatile",
        "api_key": GROQ_API_KEY,
        "base_url": "https://api.groq.com/openai/v1",
        "api_type": "openai",
    }],
    "temperature": 0.3,
    "cache_seed": None,
}


def _extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in model reply:\n{text}")
    return json.loads(match.group())


def _get_last_assistant_message(chat_history):
    """Extract last assistant message from chat history."""
    for msg in reversed(chat_history):
        if msg.get("role") == "assistant" or msg.get("name") != "Orchestrator":
            content = msg.get("content", "")
            if content and content.strip():
                return content
    return chat_history[-1].get("content", "")


# ── Agent 1: Classifier ────────────────────────────────────────────────────
classifier_agent = autogen.ConversableAgent(
    name="ClassifierAgent",
    system_message="""You are a banking customer-support classifier.
Given a customer message return ONLY a JSON object with two keys:
  "category"  : one of ["feedback_positive", "feedback_negative", "query"]
  "sentiment" : one of ["positive", "negative", "neutral"]
Return ONLY valid JSON. No explanation, no markdown, no code blocks.""",
    llm_config=GROQ_CONFIG,
    human_input_mode="NEVER",
    max_consecutive_auto_reply=1,
)

# ── Agent 2: Responder ─────────────────────────────────────────────────────
responder_agent = autogen.ConversableAgent(
    name="ResponderAgent",
    system_message="""You are a senior banking customer-support specialist.
You receive a JSON with user_name, message, category, sentiment.
Write a warm professional personalised reply (under 120 words).
- Address the customer by first name.
- feedback_positive: thank them and reinforce the relationship.
- feedback_negative: empathise, apologise, offer next steps.
- query: give a clear helpful answer.
- End every reply with: "Your support ticket has been created and our team will follow up within 24 hours."
Return ONLY JSON: {"response": "<reply>"}. No markdown, no extra keys, no code blocks.""",
    llm_config=GROQ_CONFIG,
    human_input_mode="NEVER",
    max_consecutive_auto_reply=1,
)

# ── Orchestrator ───────────────────────────────────────────────────────────
user_proxy = autogen.UserProxyAgent(
    name="Orchestrator",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=0,
    code_execution_config=False,
)


# ── Public API ─────────────────────────────────────────────────────────────
def process_customer_message(user_name: str, message: str) -> dict:
    if not GROQ_API_KEY:
        raise EnvironmentError("GROQ_API_KEY is not set in your .env file or Streamlit secrets.")

    # Step 1 — Classify
    result = user_proxy.initiate_chat(
        classifier_agent,
        message=f"Customer message: {message}",
        max_turns=1,
        silent=True,
    )
    last_msg = _get_last_assistant_message(result.chat_history)
    classification = _extract_json(last_msg)
    category  = classification.get("category", "query")
    sentiment = classification.get("sentiment", "neutral")

    # Step 2 — Respond
    result = user_proxy.initiate_chat(
        responder_agent,
        message=json.dumps({
            "user_name": user_name,
            "message":   message,
            "category":  category,
            "sentiment": sentiment,
        }),
        max_turns=1,
        silent=True,
    )
    last_msg = _get_last_assistant_message(result.chat_history)
    response_text = _extract_json(last_msg).get(
        "response", "Thank you for contacting us.")

    # Step 3 — Save ticket
    ticket_id = create_ticket(user_name, message, category, sentiment, response_text)
    ticket    = get_ticket(ticket_id)

    return {
        "ticket_id":  ticket_id,
        "category":   category,
        "sentiment":  sentiment,
        "response":   response_text,
        "status":     ticket["status"],
        "created_at": ticket["created_at"],
    }


def fetch_ticket_status(ticket_id: str):
    return get_ticket(ticket_id)


def resolve_ticket(ticket_id: str, new_status: str) -> bool:
    return update_ticket_status(ticket_id, new_status)