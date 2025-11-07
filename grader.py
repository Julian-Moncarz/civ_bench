"""
Module for grading model answers.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import config
import openrouter_client
import answerer


def load_ground_truth(assignment_num: int) -> Optional[str]:
    """Load ground truth answer for an assignment."""
    gt_path = config.GROUND_TRUTH_DIR / f"{assignment_num}.md"
    if not gt_path.exists():
        return None

    with open(gt_path, "r") as f:
        return f.read()


def grade_answer(
    model_id: str,
    assignment_num: int,
    student_answer: str,
    trial_num: int = 0,
    grade_num: int = 0
) -> Dict:
    """
    Grade a student's answer using the grader model.

    Args:
        model_id: The model that provided the answer
        assignment_num: Assignment number
        student_answer: The student's answer text
        trial_num: Trial number
        grade_num: Grade attempt number (for consistency checking)

    Returns:
        Dict containing the grade and metadata
    """
    # Load ground truth
    ground_truth = load_ground_truth(assignment_num)
    if not ground_truth:
        return {
            "success": False,
            "error": f"Ground truth not found for assignment {assignment_num}",
            "model_id": model_id,
            "assignment_num": assignment_num,
        }

    # Find all images for this assignment (same as answerer)
    image_paths = answerer.find_assignment_images(assignment_num)
    if not image_paths:
        return {
            "success": False,
            "error": f"No images found for assignment {assignment_num}",
            "model_id": model_id,
            "assignment_num": assignment_num,
        }

    print(f"  Grading {model_id}'s answer (grade {grade_num + 1}/{config.NUM_GRADES})...")

    # Build grading prompt
    grading_prompt = config.GRADING_PROMPT_TEMPLATE.format(
        ground_truth=ground_truth,
        student_answer=student_answer
    )

    # Call grader model with all images
    result = openrouter_client.call_model(
        model_id=config.GRADER_MODEL,
        prompt=grading_prompt,
        image_paths=image_paths,
        max_tokens=config.GRADER_MAX_TOKENS,
        temperature=config.GRADER_TEMPERATURE,
    )

    # Build response object
    grade_data = {
        "grader_model": config.GRADER_MODEL,
        "graded_model": model_id,
        "assignment_num": assignment_num,
        "trial_num": trial_num,
        "grade_num": grade_num,
        "timestamp": datetime.now().isoformat(),
        "success": result["error"] is None,
    }

    if result["error"]:
        grade_data["error"] = result["error"]
        grade_data["grade_response"] = None
        print(f"  ❌ Grading error: {result['error']}")
    else:
        grade_data["grade_response"] = result["content"]
        grade_data["usage"] = result.get("usage", {})

        # Try to parse the JSON grade
        try:
            # Extract JSON from response (may have markdown code blocks or extra text)
            response_text = result["content"].strip()

            # Try to find JSON in various formats
            json_text = None

            # Check for markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                # Try to find JSON object by looking for { and }
                if "{" in response_text and "}" in response_text:
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    json_text = response_text[json_start:json_end].strip()
                else:
                    json_text = response_text

            parsed_grade = json.loads(json_text)
            grade_data["score"] = parsed_grade.get("score")
            grade_data["questions"] = parsed_grade.get("questions", {})
            grade_data["total_correct"] = parsed_grade.get("total_correct")
            grade_data["total_questions"] = parsed_grade.get("total_questions")

            # Calculate summary statistics
            if grade_data["questions"]:
                correct_count = sum(1 for v in grade_data["questions"].values() if v == "correct")
                partial_count = sum(1 for v in grade_data["questions"].values() if v == "partial")
                incorrect_count = sum(1 for v in grade_data["questions"].values() if v == "incorrect")
                grade_data["summary"] = {
                    "correct": correct_count,
                    "partial": partial_count,
                    "incorrect": incorrect_count
                }

            print(f"  ✓ Score: {grade_data['score']}/100 ({grade_data.get('total_correct', 0)}/{grade_data.get('total_questions', 0)} correct)")
        except (json.JSONDecodeError, ValueError) as e:
            grade_data["parse_error"] = str(e)
            grade_data["score"] = None
            # Store raw response for debugging
            grade_data["raw_response_preview"] = result["content"][:500]
            print(f"  ⚠️  Got response but couldn't parse JSON: {str(e)}")

    # Save grade
    save_grade(grade_data)

    return grade_data


def save_grade(grade_data: Dict):
    """Save grade to disk in two formats for different use cases."""
    grader_model = grade_data["grader_model"]
    model_id = grade_data["graded_model"]
    assignment_num = grade_data["assignment_num"]
    trial_num = grade_data["trial_num"]
    grade_num = grade_data["grade_num"]

    # 1. Save detailed grade to organized directory structure
    # Structure: grades/{grader_model}/{tested_model}/trial_{n}/assignment_{n}_grade_{n}.json
    grader_name = grader_model.replace("/", "_")
    model_name = model_id.replace("/", "_")
    grade_dir = config.GRADES_DIR / grader_name / model_name / f"trial_{trial_num}"
    grade_dir.mkdir(parents=True, exist_ok=True)

    output_file = grade_dir / f"assignment_{assignment_num}_grade_{grade_num}.json"
    with open(output_file, "w") as f:
        json.dump(grade_data, f, indent=2)

    # 2. Append to JSONL for easy bulk analysis
    # Create a flattened version for analysis
    analysis_record = {
        "grader_model": grader_model,
        "tested_model": model_id,
        "assignment": assignment_num,
        "trial": trial_num,
        "grade_num": grade_num,
        "timestamp": grade_data["timestamp"],
        "score": grade_data.get("score"),
        "total_correct": grade_data.get("total_correct"),
        "total_questions": grade_data.get("total_questions"),
        "questions": grade_data.get("questions", {}),
        "summary": grade_data.get("summary", {}),
        "success": grade_data["success"],
    }

    # Append to results file
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_file = config.RESULTS_DIR / "grades.jsonl"

    with open(results_file, "a") as f:
        f.write(json.dumps(analysis_record) + "\n")

    print(f"  Saved to: {output_file}")
    print(f"  Appended to: {results_file}")


def grade_all_responses():
    """
    Grade all existing responses in the responses directory.
    """
    print("=" * 60)
    print("Grading All Responses")
    print("=" * 60)
    print()

    graded_count = 0
    error_count = 0

    # Iterate through all model directories
    for model_dir in config.RESPONSES_DIR.iterdir():
        if not model_dir.is_dir():
            continue

        model_id = model_dir.name.replace("_", "/")
        print(f"\n{'='*60}")
        print(f"Grading: {model_id}")
        print('='*60)

        # Iterate through trial directories
        for trial_dir in model_dir.iterdir():
            if not trial_dir.is_dir() or not trial_dir.name.startswith("trial_"):
                continue

            trial_num = int(trial_dir.name.replace("trial_", ""))

            # Find answer files
            for answer_file in trial_dir.glob("*_answer.json"):
                # Extract assignment number
                assignment_num = int(answer_file.stem.replace("assignment_", "").replace("_answer", ""))

                # Load the answer
                with open(answer_file, "r") as f:
                    answer_data = json.load(f)

                if not answer_data.get("success"):
                    print(f"  Skipping assignment {assignment_num} (answer failed)")
                    continue

                student_answer = answer_data.get("answer")
                if not student_answer:
                    print(f"  Skipping assignment {assignment_num} (no answer)")
                    continue

                # Grade multiple times if configured
                for grade_num in range(config.NUM_GRADES):
                    result = grade_answer(
                        model_id=model_id,
                        assignment_num=assignment_num,
                        student_answer=student_answer,
                        trial_num=trial_num,
                        grade_num=grade_num
                    )

                    if result["success"]:
                        graded_count += 1
                    else:
                        error_count += 1

    print()
    print("=" * 60)
    print("GRADING COMPLETE")
    print("=" * 60)
    print(f"Successfully graded: {graded_count}")
    print(f"Errors: {error_count}")
    print()
