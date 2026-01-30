import json

def safe_json_parse(text: str) -> dict:
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception:
        return {
            "thinking": "Failed to parse JSON from model output",
            "node_list": []
        }
