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

url = "https://api.x.ai/v1/models"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {grok_key}"})

try:
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        print("Available Grok Models:")
        for m in body.get("data", []):
            print(" -", m.get("id"))
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
except Exception as exc:
    print("Error:", exc)
