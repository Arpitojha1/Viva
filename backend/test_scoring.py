import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv("C:\\Users\\Arpit\\Viva\\backend\\.env")

from app.services.answer_scorer import score_answer
from app.services.resume_parser import parse_resume

async def main():
    print("Testing parse_resume with openai/gpt-oss-120b...")
    try:
        # Create a dummy PDF bytes (not a real PDF, but we'll bypass the extraction for testing by passing raw_text)
        data, text, chash = await parse_resume(
            file_bytes=b"",
            filename="dummy.pdf",
            raw_text="Arpit's Resume. Skills: Python, Machine Learning, React, FastAPI, AWS, Docker, Kubernetes, PostgreSQL. 5 years of experience in NLP."
        )
        print("Resume Parsed successfully!")
        print("Skills:", data.skills)
        print("Technologies:", data.technologies)
        print("Experience Level:", data.experience_level)
    except Exception as e:
        print("Error in parse_resume:", e)

    print("\n-------------------------------\n")
    print("Testing score_answer with openai/gpt-oss-20b...")
    try:
        result = await score_answer(
            question_text="Explain regularization.",
            answer_text="Regularization is a technique used to prevent overfitting. L1 adds the absolute value of weights to the loss, which encourages sparsity. L2 adds the squared value of weights, which keeps weights small.",
            source_chunks=["Regularization (L1, L2, Dropout) is essential for generalizing models."]
        )
        print("Answer Scored successfully!")
        print("Result numeric_score:", result.numeric_score)
        print("Result quality_score:", result.score)
        print("Result reasoning:", result.reasoning)
    except Exception as e:
        print("Error in score_answer:", e)

if __name__ == "__main__":
    asyncio.run(main())
