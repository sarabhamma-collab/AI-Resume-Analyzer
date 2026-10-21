import os
import re
import time
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator
from pypdf import PdfReader

# --------------------------------------------------
# 1. Environment and application setup
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)
MAX_PDF_SIZE = 5 * 1024 * 1024  # 5 MB

app = FastAPI(
    title="AI Resume Analyzer",
    description="Analyze resumes against job descriptions, identify skill gaps, and generate AI recommendations.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# --------------------------------------------------
# 2. Request model for pasted resume text
# --------------------------------------------------
class ResumeRequest(BaseModel):
    resume: str = Field(min_length=1, max_length=100_000)
    job_description: str = Field(min_length=1, max_length=30_000)

    @field_validator("resume", "job_description")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field cannot be empty.")
        return value.strip()


# --------------------------------------------------
# 3. Supported skills and Smart Skill Matching aliases
# --------------------------------------------------
ALL_SKILLS = [
    "python", "fastapi", "django", "flask", "sql", "mysql",
    "postgresql", "sqlite", "javascript", "typescript", "html", "css",
    "react", "node.js", "git", "github", "docker", "aws", "azure",
    "machine learning", "deep learning", "pandas", "numpy", "scikit-learn",
    "tensorflow", "pytorch", "rest api", "api development", "sqlalchemy",
    "pydantic", "java", "c++", "data structures", "algorithms", "linux",
    "mongodb", "redis", "llm", "generative ai", "prompt engineering",
]

# Different terms that mean the same canonical skill.
SKILL_ALIASES = {
    "javascript": ["js", "javascript", "ecmascript"],
    "typescript": ["ts", "typescript"],
    "postgresql": ["postgres", "postgresql", "postgresql database"],
    "mysql": ["mysql", "my sql"],
    "fastapi": ["fastapi", "fast api"],
    "node.js": ["node.js", "nodejs", "node js"],
    "rest api": ["rest api", "restful api", "rest apis"],
    "generative ai": ["generative ai", "genai", "gen ai"],
    "machine learning": ["machine learning", "ml"],
    "scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
    "llm": ["llm", "llms", "large language model", "large language models"],
    "github": ["github", "git hub"],
    "c++": ["c++", "cpp"],
    "sqlalchemy": ["sqlalchemy", "sql alchemy"],
    "pydantic": ["pydantic", "pydantic models"],
}

LEARNING_PHRASES = [
    "currently learning", "learning goals", "currently studying",
    "beginner in", "want to learn", "planning to learn",
    "no experience with", "no professional experience with",
    "not experienced in", "not familiar with", "interested in learning",
    "hoping to learn", "learning about", "studying to learn",
]

NEGATIVE_PHRASES = [
    "no experience with", "no professional experience with",
    "not experienced in", "not familiar with", "do not know",
    "don't know", "have not used", "haven't used", "lack experience in",
]


def skill_pattern(skill: str) -> str:
    """Match a complete skill term rather than a partial word."""
    return r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"


def skill_is_present(text: str, skill: str) -> bool:
    """Recognize a canonical skill and its known aliases."""
    aliases = SKILL_ALIASES.get(skill.lower(), [skill.lower()])
    names = set(aliases)
    names.add(skill.lower())

    return any(
        re.search(skill_pattern(name), text.lower())
        for name in names
    )


def extract_skills(job_description: str, skills: list[str]) -> list[str]:
    """Return canonical skills detected in the job description."""
    return [
        skill
        for skill in skills
        if skill_is_present(job_description, skill)
    ]


def find_skills(
    resume_text: str,
    skills: list[str],
) -> tuple[list[str], list[str]]:
    """Separate detected skills from skills not evidenced in the resume."""
    matching_skills = []
    missing_skills = []

    sentences = [
        sentence.strip()
        for sentence in re.split(r"[.!?;\n]+", resume_text.lower())
        if sentence.strip()
    ]

    for skill in skills:
        found_as_experience = False

        for sentence in sentences:
            if not skill_is_present(sentence, skill):
                continue

            # Avoid counting skills mentioned only as learning goals
            # or in statements that deny experience.
            if any(
                phrase in sentence
                for phrase in LEARNING_PHRASES + NEGATIVE_PHRASES
            ):
                continue

            found_as_experience = True
            break

        if found_as_experience:
            matching_skills.append(skill)
        else:
            missing_skills.append(skill)

    return matching_skills, missing_skills


def calculate_match(
    matching_skills: list[str],
    required_skills: list[str],
) -> float:
    """Calculate the score from unique required skills."""
    required = list(dict.fromkeys(required_skills))
    matching = set(matching_skills)

    if not required:
        return 0.0

    return (
        sum(skill in matching for skill in required)
        / len(required)
    ) * 100


# --------------------------------------------------
# 4. Analyze resume using Groq AI
# --------------------------------------------------
def analyze_resume(resume_text: str, job_description: str) -> dict:
    if not resume_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Resume text cannot be empty.",
        )

    if not job_description.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description cannot be empty.",
        )

    if len(resume_text) > 100_000:
        raise HTTPException(
            status_code=400,
            detail="Resume text is too long.",
        )

    if len(job_description) > 30_000:
        raise HTTPException(
            status_code=400,
            detail="Job description is too long.",
        )

    required_skills = extract_skills(job_description, ALL_SKILLS)

    matching_skills, missing_skills = find_skills(
        resume_text,
        required_skills,
    )

    match_percentage = calculate_match(
        matching_skills,
        required_skills,
    )

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is missing. Check your backend .env file.",
        )

    prompt = f"""You are a careful and honest resume reviewer helping a fresher apply for entry-level software developer jobs.

IMPORTANT RULES:
1. Use only information in the resume and job description.
2. Never invent projects, technologies, work experience, achievements, certifications, deployments, or contributions.
3. Distinguish listed skills from skills supported by project evidence and skills the candidate wants to learn.
4. If evidence is missing, say 'Not mentioned in the resume.' Do not assume the candidate has or lacks that ability.
5. Suggestions that require more work must be labelled 'Suggested future improvement.'
6. Keep recommendations practical and beginner-friendly. Do not guarantee job selection.

RESUME:
--- START RESUME ---
{resume_text}
--- END RESUME ---

JOB DESCRIPTION:
--- START JOB DESCRIPTION ---
{job_description}
--- END JOB DESCRIPTION ---

DETECTED REQUIRED SKILLS: {', '.join(required_skills) or 'None detected'}
MATCHING SKILLS: {', '.join(matching_skills) or 'None detected'}
SKILLS NOT DETECTED: {', '.join(missing_skills) or 'None'}
CALCULATED KEYWORD MATCH SCORE: {match_percentage:.2f}%

Write these sections:
1. CANDIDATE STRENGTHS: Explain evidence from the resume and separate listed skills from project experience.
2. SKILLS TO DEVELOP: Discuss relevant skills not demonstrated, noting that not mentioned does not necessarily mean the candidate lacks the skill. Prioritize them.
3. RESUME IMPROVEMENTS: Give three specific improvements without fictional claims.
4. INTERVIEW PREPARATION: Give three relevant questions and beginner-friendly sample answers based only on the resume. Note when personal evidence is missing.
5. LEARNING ROADMAP: Give three to five prioritized actions with a practical exercise or mini-project for each.
6. MATCH SCORE EXPLANATION: Explain that the score measures detected keywords, not overall ability or hiring probability. Do not change the calculated score.
"""

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=45.0,
            max_retries=1,
        )

        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful AI career and resume assistant. "
                        "Give practical, truthful advice."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.3,
        )

        answer = (
            response.choices[0].message.content
            or "The AI returned an empty response."
        )
    except Exception as exc:
        # Log the provider error for debugging; never log the API key.
        print(f"Groq API error type: {type(exc).__name__}")

        raise HTTPException(
            status_code=502,
            detail=(
                "Groq AI request failed. Check the backend terminal "
                "for diagnostic information."
            ),
        )


    return {
        "required_skills": required_skills,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "match_percentage": round(match_percentage, 2),
        "answer": answer,
    }


# --------------------------------------------------
# 5. API endpoints
# --------------------------------------------------
@app.get("/")
def home():
    return {
        "message": "AI Resume Analyzer API is running",
        "docs": "/docs",
    }


@app.post("/ask")
def ask_question(data: ResumeRequest):
    """Analyze resume text and measure processing time."""

    start_time = time.perf_counter()

    result = analyze_resume(
        data.resume,
        data.job_description,
    )

    processing_time = time.perf_counter() - start_time

    result["processing_time_seconds"] = round(processing_time, 2)

    print(
        f"Resume analysis processing time: "
        f"{processing_time:.2f} seconds"
    )

    return result




@app.post("/analyze-pdf")
async def analyze_pdf(
    resume_file: UploadFile = File(...),
    job_description: str = Form(..., min_length=1, max_length=30_000),
):
    """Extract text from an uploaded PDF and analyze it."""
    try:
        if not resume_file.filename:
            raise HTTPException(
                status_code=400,
                detail="Please select a PDF file.",
            )

        if not resume_file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Please upload a PDF file.",
            )

        if not job_description.strip():
            raise HTTPException(
                status_code=400,
                detail="Job description cannot be empty.",
            )

        content = await resume_file.read(MAX_PDF_SIZE + 1)

        if len(content) > MAX_PDF_SIZE:
            raise HTTPException(
                status_code=400,
                detail="PDF size must be 5 MB or less.",
            )

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded PDF is empty.",
            )

        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is not a valid PDF.",
            )

        try:
            pdf = PdfReader(BytesIO(content), strict=False)

            if pdf.is_encrypted:
                raise HTTPException(
                    status_code=400,
                    detail="Password-protected PDFs are not supported.",
                )

            if len(pdf.pages) > 100:
                raise HTTPException(
                    status_code=400,
                    detail="PDF must contain no more than 100 pages.",
                )

            resume_text = "\n".join(
                page.extract_text() or ""
                for page in pdf.pages
            ).strip()

        except HTTPException:
            raise

        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Could not read this PDF. Please try another valid PDF file.",
            )

        if not resume_text:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No readable text was found. This may be a scanned PDF; "
                    "OCR support would be needed."
                ),
            )

        return analyze_resume(
            resume_text,
            job_description.strip(),
        )

    finally:
        await resume_file.close()