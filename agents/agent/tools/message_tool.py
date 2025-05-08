import json


def send_message(event: str, message: dict) -> str:
    """
    Send a message to the client.
    """
    return f'event: {event}\ndata: {json.dumps(message, ensure_ascii=False)}\n\n'

def send_markdown(text: str) -> str:
    return send_message("message", {"type": "markdown", "text": text})
