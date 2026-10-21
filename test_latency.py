
import time
import requests
from statistics import median

url = "http://127.0.0.1:8000/ask"

payload = {
    "resume": (
        "Python, FastAPI, SQL and Git. "
        "Built an AI Resume Analyzer using FastAPI."
    ),
    "job_description": (
        "Looking for a fresher Python developer "
        "with FastAPI, SQL and Git skills."
    ),
}

times = []
failures = 0

for run in range(1, 11):
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()

        result = response.json()
        elapsed = result["processing_time_seconds"]
        times.append(elapsed)

        print(f"Run {run}: {elapsed:.2f} seconds")

    except (requests.RequestException, KeyError, ValueError) as error:
        failures += 1
        print(f"Run {run} failed: {error}")

    if run < 10:
        time.sleep(30)

print("\nSuccessful runs:", len(times))
print("Failed runs:", failures)

if times:
    print(f"Median: {median(times):.2f} seconds")
    print(f"Average: {sum(times) / len(times):.2f} seconds")
else:
    print("No successful runs. Check backend and Groq API.")
