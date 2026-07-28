import os
import json
import urllib.request
import urllib.error

env_path = ".env"
grok_key = ""
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("GROK_API_KEY"):
                grok_key = line.split("=", 1)[1].strip().strip('"').strip("'")

print(f"Loaded GROK_API_KEY: {grok_key[:10]}...{grok_key[-6:]}")

models_to_test = ["grok-beta", "grok-2-1212", "grok-vision-beta", "grok-2"]

for model in models_to_test:
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {grok_key}"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful AI recruitment assistant."},
            {"role": "user", "content": "Reply in 1 sentence: Grok API status check."}
        ],
        "temperature": 0.1
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)

    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            print(f"\nSUCCESS with model '{model}'! Grok Response:")
            print(body["choices"][0]["message"]["content"])
            break
    except urllib.error.HTTPError as e:
        print(f"Model '{model}' failed ({e.code}): {e.read().decode('utf-8')}")
    except Exception as exc:
        print(f"Error for '{model}': {exc}")
