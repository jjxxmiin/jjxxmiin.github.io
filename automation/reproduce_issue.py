from google.genai import types

try:
    print("Attempting to create ThinkingConfig with thinking_level='HIGH'")
    tc = types.ThinkingConfig(thinking_level="HIGH")
    print(f"Created: {tc}")
except Exception as e:
    print(f"Error creating ThinkingConfig: {e}")

try:
    print("Attempting to create GenerateContentConfig with thinking_config")
    gc = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_level="HIGH",
        ),
        response_mime_type="application/json",
    )
    print(f"Created Config: {gc}")
except Exception as e:
    print(f"Error creating GenerateContentConfig: {e}")
