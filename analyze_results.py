#!/usr/bin/env python3
"""
Quick analysis of grading results.
Usage: python analyze_results.py
"""

import json
from pathlib import Path
from collections import defaultdict

import config


def load_grades():
    """Load all grades from the JSONL file."""
    results_file = config.RESULTS_DIR / "grades.jsonl"

    if not results_file.exists():
        print(f"No results file found at {results_file}")
        return []

    grades = []
    with open(results_file, "r") as f:
        for line in f:
            grades.append(json.loads(line))

    return grades


def analyze_grades(grades):
    """Analyze grading results and print summary statistics."""
    if not grades:
        print("No grades to analyze.")
        return

    print("=" * 60)
    print("GRADING RESULTS SUMMARY")
    print("=" * 60)
    print()

    # Group by model
    by_model = defaultdict(list)
    for grade in grades:
        if grade.get("success") and grade.get("score") is not None:
            by_model[grade["tested_model"]].append(grade)

    # Per-model statistics
    print("SCORES BY MODEL:")
    print("-" * 60)
    for model, model_grades in sorted(by_model.items()):
        scores = [g["score"] for g in model_grades]
        avg_score = sum(scores) / len(scores)

        total_correct = sum(g.get("total_correct", 0) for g in model_grades)
        total_questions = sum(g.get("total_questions", 0) for g in model_grades)

        print(f"\n{model}:")
        print(f"  Average Score: {avg_score:.1f}/100")
        print(f"  Total Correct: {total_correct}/{total_questions}")
        print(f"  Graded Assignments: {len(model_grades)}")

    print()
    print("-" * 60)

    # Per-question analysis
    print("\nQUESTION DIFFICULTY ANALYSIS:")
    print("-" * 60)

    question_stats = defaultdict(lambda: {"correct": 0, "partial": 0, "incorrect": 0, "total": 0})

    for grade in grades:
        if grade.get("success") and grade.get("questions"):
            for q_id, result in grade["questions"].items():
                question_stats[q_id][result] += 1
                question_stats[q_id]["total"] += 1

    for q_id in sorted(question_stats.keys()):
        stats = question_stats[q_id]
        total = stats["total"]
        correct_pct = (stats["correct"] / total * 100) if total > 0 else 0
        partial_pct = (stats["partial"] / total * 100) if total > 0 else 0
        incorrect_pct = (stats["incorrect"] / total * 100) if total > 0 else 0

        print(f"\n{q_id}:")
        print(f"  Correct:   {stats['correct']:2d}/{total} ({correct_pct:5.1f}%)")
        print(f"  Partial:   {stats['partial']:2d}/{total} ({partial_pct:5.1f}%)")
        print(f"  Incorrect: {stats['incorrect']:2d}/{total} ({incorrect_pct:5.1f}%)")

    print()
    print("=" * 60)


if __name__ == "__main__":
    grades = load_grades()
    analyze_grades(grades)
