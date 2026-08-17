"""
End-to-end smoke test for the Viva API.
Tests: health → upload → create session → get question → submit answer
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

# Use the real Burkov PDF (known-good — already ingested successfully)
_BOOKS_DIR = Path(__file__).parent.parent / "data" / "books"
_PDF_PATH = next(_BOOKS_DIR.glob("*Burkov*"), None) or next(_BOOKS_DIR.glob("*.pdf"), None)
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 260>>stream
BT /F1 12 Tf 72 720 Td
(John Smith - AI/ML Engineer) Tj T*
(Skills: Python PyTorch TensorFlow LLMs Transformers NLP) Tj T*
(Experience: 3 years deep learning NLP computer vision) Tj T*
(Projects: BERT fine-tuning, diffusion models, RL policy gradients) Tj T*
(Education: MSc Machine Learning) Tj
ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000576 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
655
%%EOF"""


async def smoke_test():
    import httpx
    BASE = "http://localhost:8000/api"

    async with httpx.AsyncClient(timeout=90) as client:
        # 1. Health
        r = await client.get("http://localhost:8000/health")
        print(f"[1] Health: {r.status_code} -> {r.json()}")

        # 2. Resume upload
        files = {"file": ("test_resume.pdf", MINIMAL_PDF, "application/pdf")}
        r = await client.post(f"{BASE}/resume/upload", files=files)
        print(f"[2] Upload: {r.status_code}")
        if r.status_code not in (200, 201):
            print(f"    ERROR: {r.text[:400]}")
            return
        data = r.json()
        resume_id = data["resumeId"]
        skills = data["extractedSkills"]
        print(f"    resumeId={resume_id}")
        print(f"    skills={skills}")

        # 3. Create session
        r = await client.post(
            f"{BASE}/session",
            json={"resumeId": resume_id, "role": "AI/ML Engineer"},
        )
        print(f"[3] Session: {r.status_code}")
        if r.status_code not in (200, 201):
            print(f"    ERROR: {r.text[:400]}")
            return
        session_data = r.json()
        session_id = session_data["id"]
        print(f"    sessionId={session_id}, status={session_data['status']}")

        # 4. Get first question
        r = await client.get(f"{BASE}/interview/{session_id}/next-question")
        print(f"[4] Next question: {r.status_code}")
        if r.status_code != 200:
            print(f"    ERROR: {r.text[:400]}")
            return
        q = r.json()
        print(f"    id={q['id']}, difficulty={q['difficulty']}")
        print(f"    text={q['text'][:120]}...")
        print(f"    source={q['source']['book']}, p.{q['source']['page']}, sim={q['source']['similarity']:.3f}")

        # 5. Submit answer
        r = await client.post(
            f"{BASE}/interview/{session_id}/answer",
            json={
                "questionId": q["id"],
                "answer": (
                    "Gradient descent optimizes a loss function by computing the gradient "
                    "and stepping in the negative gradient direction. The learning rate "
                    "controls step size. Stochastic gradient descent (SGD) uses mini-batches "
                    "for computational efficiency and acts as regularization."
                ),
            },
        )
        print(f"[5] Submit answer: {r.status_code}")
        if r.status_code == 200:
            ans = r.json()
            print(f"    score={ans['score']}, nextDifficulty={ans['nextDifficulty']}, hasNext={ans['hasNextQuestion']}")
        else:
            print(f"    ERROR: {r.text[:400]}")
            return

        print("\n[OK] Smoke test passed — full stack is functional.")


if __name__ == "__main__":
    asyncio.run(smoke_test())
