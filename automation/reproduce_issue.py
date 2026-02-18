from google.genai import types
try:
    config = types.ThinkingConfig(thinking_level="HIGH")
    print("Success:", config)
except Exception as e:
    print("Error:", e)
