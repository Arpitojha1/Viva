import asyncio
import os
import requests
import asyncpg
from dotenv import load_dotenv

load_dotenv("C:\\Users\\Arpit\\Viva\\backend\\.env")

async def main():
    base_url = "http://localhost:8001/api"
    
    # 1. Upload Resume
    print("Uploading resume...")
    pdf_path = "dummy_resume.pdf"
    with open(pdf_path, "rb") as f:
        files = {"file": ("dummy_resume.pdf", f, "application/pdf")}
        r = requests.post(f"{base_url}/resume/upload", files=files)
    
    if r.status_code != 201:
        print("Upload failed:", r.status_code, r.text)
        return
    resume_id = r.json()["resumeId"]
    print("Resume ID:", resume_id)
    
    # 2. Create Session
    print("Creating session...")
    r = requests.post(f"{base_url}/session", json={"resumeId": resume_id, "role": "Backend Engineer"})
    if r.status_code != 201:
        print("Session creation failed:", r.status_code, r.text)
        return
    session_token = r.json()["id"]
    print("Session Token:", session_token)
    
    # 3. Get Question
    print("Fetching question...")
    r = requests.get(f"{base_url}/interview/{session_token}/next-question")
    if r.status_code != 200:
        print("Question fetch failed:", r.status_code, r.text)
        return
    q_data = r.json()
    q_id = q_data["id"]
    print("Question ID:", q_id)
    
    # 4. Submit Answer
    print("Submitting answer...")
    r = requests.post(f"{base_url}/interview/{session_token}/answer", json={
        "session_token": session_token,
        "questionId": q_id,
        "answer": "I use Docker and Kubernetes to deploy microservices. It's great for scaling and maintaining state across clusters."
    })
    if r.status_code != 200:
        print("Answer submission failed:", r.status_code, r.text)
        return
    print("Submit response:", r.json())
    
    # 5. Check Database
    print("\nQuerying DB for newest answer...")
    db_url = os.environ.get("DATABASE_URL").replace("postgresql+asyncpg", "postgresql")
    conn = await asyncpg.connect(db_url)
    row = await conn.fetchrow("SELECT id, numeric_score, quality_score, score_reasoning FROM answers ORDER BY id DESC LIMIT 1;")
    print(f"DB Row: id={row['id']}, numeric_score={row['numeric_score']}, quality_score={row['quality_score']}")
    print(f"Reasoning: {row['score_reasoning']}")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
