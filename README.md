# AI Resume Analyzer

An AI-powered web application that analyzes resumes against job descriptions, identifies matching skills, highlights skill gaps, and generates personalized recommendations.

## Features

- **PDF Resume Upload:** Upload a resume in PDF format.
- **Resume Text Input:** Paste resume content directly.
- **Skill Matching:** Identify matching and missing skills based on a job description.
- **Match Score:** Calculate a resume-to-job skill match percentage.
- **AI Recommendations:** Get suggestions for skill development and interview preparation.
- **PDF Report Download:** Download the analysis report.
- **Input Validation:** Handle missing inputs and invalid PDF files.

## Tech Stack

- **Backend:** Python, FastAPI
- **AI Integration:** Groq API
- **Frontend:** HTML, CSS, JavaScript
- **PDF Processing:** pypdf
- **Validation:** Pydantic

## Project Structure

```text
AI-Resume-Analyzer/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── main.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/sarabhamma-collab/AI-Resume-Analyzer.git
cd AI-Resume-Analyzer
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure the Groq API key

Create a `.env` file in the project root:

```text
GROQ_API_KEY=your_groq_api_key_here
```

Replace the placeholder with your own API key. Never publish your real API key.

### 5. Run the backend

```bash
uvicorn main:app --reload
```

Backend API: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

### 6. Run the frontend

Open a second terminal:

```powershell
cd frontend
python -m http.server 5500 --bind 127.0.0.1
```

Open http://127.0.0.1:5500 in your browser.

## How to Use

1. Upload a PDF resume or paste resume text.
2. Enter the job description.
3. Click **Analyze My Resume**.
4. Review the match score, matching skills, and skills to develop.
5. Read the AI recommendations.
6. Download the PDF analysis report.

## Security

- Keep API keys in the local `.env` file.
- Do not commit `.env` or other secrets to GitHub.
- Resume information should be handled carefully because it may contain personal data.

## Future Improvements

- More robust skill extraction and synonym matching.
- Resume section analysis.
- Job-specific interview question generation.
- Automated tests and deployment.


## Application Screenshot

![AI Resume Analyzer](screenshots/resume-analyzer.png)


## Author

**Sara Garg**

GitHub: https://github.com/sarabhamma-collab