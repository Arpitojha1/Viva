import asyncio
import requests

def main():
    session_token = "ec187d1e-68a3-4fb4-8060-83cde7ded0c4"
    url = f"http://localhost:8001/api/session/{session_token}/summary"
    print(f"Fetching summary from {url}...")
    r = requests.get(url)
    
    if r.status_code != 200:
        print("Failed:", r.status_code, r.text)
        return
        
    data = r.json()
    print(data.keys())
    series = data.get("performanceSeries")
    if series:
        print(f"Success! performanceSeries has {len(series)} items:")
        for item in series:
            print(f"  Q{item['orderIndex']}: {item['difficulty']} - Score: {item['numericScore']} - Reasoning: {item['scoreReasoning']}")
    else:
        print("Error: performanceSeries missing or empty in response.")

if __name__ == "__main__":
    main()
