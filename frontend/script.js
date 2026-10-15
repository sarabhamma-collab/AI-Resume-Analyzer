
const form = document.getElementById("analyzer-form");
const button = document.getElementById("analyze-button");
const statusText = document.getElementById("status");
const results = document.getElementById("results");

const fileInput = document.getElementById("resumeFile");
const resumeInput = document.getElementById("resume");
const jobDescriptionInput = document.getElementById("job-description");
const answerElement = document.getElementById("ai-answer");


// Backend URL
const API_URL = "http://127.0.0.1:8000";
const MAX_PDF_SIZE = 5 * 1024 * 1024;


// 1. Display skills safely
function showSkills(elementId, skills) {
    const list = document.getElementById(elementId);

    list.replaceChildren();

    if (!Array.isArray(skills) || skills.length === 0) {
        const item = document.createElement("li");
        item.textContent = "None found";
        list.appendChild(item);
        return;
    }

    skills.forEach((skill) => {
        const item = document.createElement("li");
        item.textContent = String(skill);
        list.appendChild(item);
    });
}


// 2. Display AI recommendations
function showRecommendations(answer) {
    const rawAnswer =
        typeof answer === "string" && answer.trim()
            ? answer
            : "No AI recommendations were returned.";

    // Format Markdown and sanitize generated HTML
    if (
        typeof window.marked !== "undefined" &&
        typeof window.DOMPurify !== "undefined"
    ) {
        answerElement.innerHTML = window.DOMPurify.sanitize(
            window.marked.parse(rawAnswer)
        );
    } else {
        // Safe fallback if the formatting libraries are unavailable
        answerElement.textContent = rawAnswer;
    }
}


// 3. Control the Analyze button
function setLoading(isLoading) {
    button.disabled = isLoading;

    button.textContent = isLoading
        ? "Analyzing..."
        : "Analyze My Resume";
}


// 4. Validate the form
function validateInputs(resume, file, jobDescription) {
    if (!jobDescription) {
        return "Please enter a job description.";
    }

    if (!file && !resume) {
        return "Please upload a PDF or paste your resume.";
    }

    if (file && resume) {
        return "Please upload a PDF or paste your resume, not both.";
    }

    if (file && !file.name.toLowerCase().endsWith(".pdf")) {
        return "Please select a PDF file.";
    }

    if (file && file.size > MAX_PDF_SIZE) {
        return "PDF must be 5 MB or smaller.";
    }

    if (resume.length > 100000) {
        return "Resume text is too long.";
    }

    if (jobDescription.length > 30000) {
        return "Job description is too long.";
    }

    return "";
}


// 5. Read and validate the backend response
async function readResponse(response) {
    let data;

    try {
        data = await response.json();
    } catch {
        throw new Error(
            "The server returned an invalid response. " +
            "Check that the backend is running."
        );
    }

    if (!response.ok) {
        const detail =
            typeof data.detail === "string"
                ? data.detail
                : "Resume analysis failed.";

        throw new Error(detail);
    }

    return data;
}


// 6. Display the analysis results

function displayResults(data) {
    // Save the latest analysis for downloading
    latestReport = data;

    const percentage = Number(data.match_percentage);

    document.getElementById("match-percentage").textContent =
        Number.isFinite(percentage)
            ? `${percentage}%`
            : "N/A";

    showSkills("required-skills", data.required_skills);
    showSkills("matching-skills", data.matching_skills);
    showSkills("missing-skills", data.missing_skills);

    showRecommendations(data.answer);

    results.hidden = false;
}



// 7. Handle form submission
form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const resume = resumeInput.value.trim();
    const file = fileInput.files[0];
    const jobDescription = jobDescriptionInput.value.trim();

    // Validate before calling the API
    const validationMessage = validateInputs(
        resume,
        file,
        jobDescription
    );

    if (validationMessage) {
        statusText.textContent = validationMessage;
        return;
    }

    setLoading(true);

    statusText.textContent =
        "Please wait while AI analyzes your resume.";

    results.hidden = true;

    try {
        let response;

        // Option A: Upload a PDF resume
        if (file) {
            const formData = new FormData();

            formData.append("resume_file", file);
            formData.append("job_description", jobDescription);

            response = await fetch(`${API_URL}/analyze-pdf`, {
                method: "POST",
                body: formData
            });
        }

        // Option B: Submit pasted resume text
        else {
            response = await fetch(`${API_URL}/ask`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    resume: resume,
                    job_description: jobDescription
                })
            });
        }

        const data = await readResponse(response);

        displayResults(data);

        statusText.textContent =
            "Resume analysis completed successfully.";

    } catch (error) {
        console.error("Resume analysis error:", error);

        statusText.textContent =
            `Error: ${error.message} ` +
            "Check that the backend is running and try again.";

    } finally {
        setLoading(false);
    }
});


// 8. Clear old status messages when inputs change
[fileInput, resumeInput, jobDescriptionInput].forEach((element) => {
    element.addEventListener("input", () => {
        statusText.textContent = "";
    });
});

let latestReport = null;


function downloadReportAsPdf() {
    if (!latestReport) {
        alert("Please analyze a resume first.");
        return;
    }

    if (!window.jspdf || !window.jspdf.jsPDF) {
        alert("PDF library did not load. Please refresh the page.");
        return;
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF("p", "mm", "a4");

    const margin = 16;
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const contentWidth = pageWidth - margin * 2;
    let y = 20;

    const colors = {
        navy: [25, 43, 75],
        blue: [52, 100, 180],
        light: [241, 245, 251],
        text: [48, 56, 70],
        muted: [110, 120, 135],
        green: [35, 130, 90],
        red: [190, 65, 65]
    };

    function cleanText(value) {
        return String(value ?? "")
            .replace(/<br\s*\/?>/gi, "\n")
            .replace(/<[^>]*>/g, "")
            .replace(/\*\*(.*?)\*\*/g, "$1")
            .replace(/\*(.*?)\*/g, "$1")
            .replace(/__(.*?)__/g, "$1")
            .replace(/`([^`]*)`/g, "$1")
            .replace(/\r/g, "")
            .trim();
    }

    function drawContinuationHeader() {
        doc.setFillColor(...colors.navy);
        doc.rect(0, 0, pageWidth, 13, "F");

        doc.setTextColor(255, 255, 255);
        doc.setFont("helvetica", "bold");
        doc.setFontSize(9);
        doc.text("AI RESUME ANALYZER", margin, 8.5);

        doc.setTextColor(...colors.text);
        y = 23;
    }

    function ensureSpace(height = 7) {
        if (y + height > pageHeight - 18) {
            doc.addPage();
            drawContinuationHeader();
        }
    }

    function addParagraph(text, options = {}) {
        const {
            size = 10,
            bold = false,
            color = colors.text,
            indent = 0,
            gap = 2
        } = options;

        const value = cleanText(text);
        if (!value) return;

        doc.setFont("helvetica", bold ? "bold" : "normal");
        doc.setFontSize(size);
        doc.setTextColor(...color);

        const lines = doc.splitTextToSize(
            value,
            contentWidth - indent
        );

        lines.forEach(line => {
            ensureSpace(5.5);
            doc.text(line, margin + indent, y);
            y += 5;
        });

        y += gap;
    }

    function addSectionTitle(title) {
        ensureSpace(17);

        y += 3;
        doc.setFillColor(...colors.light);
        doc.roundedRect(
            margin, y - 5, contentWidth, 10, 2, 2, "F"
        );

        doc.setFont("helvetica", "bold");
        doc.setFontSize(12);
        doc.setTextColor(...colors.navy);
        doc.text(title, margin + 4, y + 1.5);

        y += 12;
    }

    function addSkillSection(title, skills, type) {
        addSectionTitle(title);

        if (!Array.isArray(skills) || skills.length === 0) {
            addParagraph("None found", { color: colors.muted });
            return;
        }

        const fillColor =
            type === "match" ? [226, 244, 235] :
            type === "missing" ? [253, 235, 233] :
            [232, 239, 250];

        const textColor =
            type === "match" ? colors.green :
            type === "missing" ? colors.red :
            colors.navy;

        doc.setFont("helvetica", "normal");
        doc.setFontSize(9);

        let x = margin;
        const chipHeight = 8;
        const gap = 2;

        skills.forEach(skill => {
            const label = cleanText(skill);
            if (!label) return;

            const chipWidth = Math.min(
                doc.getTextWidth(label) + 8,
                contentWidth
            );

            if (x + chipWidth > pageWidth - margin) {
                x = margin;
                y += chipHeight + gap;
            }

            ensureSpace(chipHeight + gap);

            doc.setFillColor(...fillColor);
            doc.roundedRect(
                x, y - 5, chipWidth, chipHeight, 2, 2, "F"
            );

            doc.setTextColor(...textColor);
            doc.text(label, x + 4, y);

            x += chipWidth + gap;
        });

        y += chipHeight + 5;
    }

    // Professional cover header
    doc.setFillColor(...colors.navy);
    doc.rect(0, 0, pageWidth, 43, "F");

    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(19);
    doc.text("AI Resume Analysis", margin, 19);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.text("Resume-to-Job Description Match Report", margin, 27);

    doc.setFontSize(9);
    doc.text(
        "Generated: " + new Date().toLocaleDateString("en-IN"),
        margin,
        35
    );

    y = 54;

    // Match score card
    const score = Number(latestReport.match_percentage);
    const validScore = Number.isFinite(score)
        ? Math.max(0, Math.min(100, score))
        : null;

    doc.setFillColor(...colors.light);
    doc.roundedRect(
        margin, y, contentWidth, 30, 3, 3, "F"
    );

    doc.setTextColor(...colors.navy);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.text("RESUME MATCH SCORE", margin + 5, y + 9);

    doc.setFontSize(23);
    doc.setTextColor(
        ...(validScore !== null && validScore >= 70
            ? colors.green
            : colors.blue)
    );

    doc.text(
        validScore !== null ? validScore.toFixed(2) + "%" : "N/A",
        margin + 5,
        y + 22
    );

    // Score progress bar
    const barX = margin + 48;
    const barY = y + 15;
    const barWidth = contentWidth - 58;

    doc.setFillColor(215, 222, 233);
    doc.roundedRect(barX, barY, barWidth, 4, 2, 2, "F");

    if (validScore !== null && validScore > 0) {
        doc.setFillColor(...colors.blue);
        doc.roundedRect(
            barX, barY, barWidth * validScore / 100,
            4, 2, 2, "F"
        );
    }

    y += 38;

    // Skill analysis
    addSkillSection(
        "Required Skills",
        latestReport.required_skills,
        "required"
    );

    addSkillSection(
        "Matching Skills",
        latestReport.matching_skills,
        "match"
    );

    addSkillSection(
        "Skills to Develop",
        latestReport.missing_skills,
        "missing"
    );

    // AI recommendations
    addSectionTitle("AI Recommendations");

    const answer = cleanText(
        latestReport.answer ||
        "No AI recommendations available."
    );

    answer.split("\n").forEach(line => {
        const trimmed = line.trim();
        if (!trimmed) {
            y += 2;
            return;
        }

        const isHeading =
            /^#{1,6}\s/.test(trimmed) ||
            /^\d+[\.\)]\s/.test(trimmed);

        const formatted = trimmed
            .replace(/^#{1,6}\s*/, "")
            .replace(/^[-*•]\s*/, "• ");

        addParagraph(formatted, {
            size: 9.5,
            bold: isHeading,
            gap: 1
        });
    });

    // Footer and page numbers on every page
    const totalPages = doc.internal.getNumberOfPages();

    for (let page = 1; page <= totalPages; page++) {
        doc.setPage(page);

        doc.setDrawColor(220, 225, 233);
        doc.line(
            margin,
            pageHeight - 13,
            pageWidth - margin,
            pageHeight - 13
        );

        doc.setFont("helvetica", "normal");
        doc.setFontSize(8);
        doc.setTextColor(...colors.muted);

        doc.text("AI Resume Analyzer", margin, pageHeight - 7);
        doc.text(
            `Page ${page} of ${totalPages}`,
            pageWidth - margin,
            pageHeight - 7,
            { align: "right" }
        );
    }

    doc.save("AI-Resume-Analysis-Report.pdf");
}


const downloadButton = document.getElementById("download-report");

if (downloadButton) {
    downloadButton.addEventListener("click", downloadReportAsPdf);
}

