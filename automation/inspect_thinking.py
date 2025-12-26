from google.genai import types
try:
    print("Trying thinking_level='HIGH'")
    tc = types.ThinkingConfig(thinking_level="HIGH")
    print("Success thinking_level")
except Exception as e:
    print(f"Failed thinking_level: {e}")

try:
    print("Trying include_thoughts=True")
    tc = types.ThinkingConfig(include_thoughts=True)
    print("Success include_thoughts")
except Exception as e:
    print(f"Failed include_thoughts: {e}")
