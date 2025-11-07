"""
Configuration for civil engineering benchmark.
Modify these settings to customize the benchmark.
"""

import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"  # You'll add screenshot images here
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"
RESPONSES_DIR = PROJECT_ROOT / "responses"
GRADES_DIR = PROJECT_ROOT / "grades"
RESULTS_DIR = PROJECT_ROOT / "results"

# OpenRouter API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    # Fall back to reading from .env file directly
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith("OPENROUTER_API_KEY"):
                    OPENROUTER_API_KEY = line.split("=", 1)[1].strip()
                    break

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# API request settings
DEFAULT_MAX_TOKENS = 50000
DEFAULT_TEMPERATURE = 1.0
DEFAULT_TIMEOUT = 120  # seconds

# Models to test
TEST_MODELS = [
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-opus-4.1",
    "openai/gpt-5",
    "google/gemini-2.5-pro",
    "x-ai/grok-4",
    "qwen/qwen3-vl-235b-a22b-instruct",  # Large Chinese vision model
]

# Grader model
GRADER_MODEL = "google/gemini-2.5-flash"
GRADER_MAX_TOKENS = 2048  # Reduced for simpler per-question grading
GRADER_TEMPERATURE = 0.5  # More deterministic grading

# Benchmark settings
NUM_TRIALS = 1  # Number of answer attempts per model
NUM_GRADES = 5  # Number of times each answer is graded
MAX_WORKERS = 10  # Number of parallel API requests (adjust based on API rate limits)

# Which assignments to test (based on image files in data/images/)
ASSIGNMENTS_TO_TEST = [1, 2, 4, 5, 6, 7]

# Prompt for answering
ANSWERING_PROMPT = """You are a civil engineering student with perfect grades completing an assignment.

Please answer ALL questions shown in the image carefully and thoroughly. Show your work, reasoning, and calculations.

Provide clear, precise answers with appropriate units. Format your response with clear question labels (e.g., "Question 1a:", "Question 2:") so answers can be easily identified."""

# Prompt for grading
GRADING_PROMPT_TEMPLATE = """You are grading a civil engineering student's answer.

QUESTION: See the attached image(s)

GROUND TRUTH ANSWER:
{ground_truth}

STUDENT'S ANSWER:
{student_answer}

Your task: Compare the student's answer to the ground truth and evaluate each question/sub-question.
If they get a HSS very similar to the correct one, give them correct.

For each question, mark as:
- "correct": Answer matches ground truth (accepts minor notation differences)
- "partial": Right approach/method but has calculation errors or minor mistakes
- "incorrect": Wrong answer or no relevant attempt

IMPORTANT: Respond with ONLY valid JSON. No other text before or after.

Required format:
{{
    "questions": {{
        "question_id": "correct|partial|incorrect",
        ...
    }},
    "total_correct": <number>,
    "total_questions": <number>,
    "score": <0-100 based on (correct + 0.5*partial)/total>
}}

Example:
{{
    "questions": {{
        "1a": "correct",
        "1b": "incorrect",
        "2": "partial"
    }},
    "total_correct": 1,
    "total_questions": 3,
    "score": 50
}}

"""
