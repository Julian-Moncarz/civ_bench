#!/usr/bin/env python3
"""
Example: Advanced analysis using pandas.
Install pandas first: pip install pandas

This shows how easy it is to analyze results with the JSONL format.
"""

import pandas as pd
from pathlib import Path

# Load the grades
grades_file = Path(__file__).parent / "results" / "grades.jsonl"

if not grades_file.exists():
    print(f"No results file found at {grades_file}")
    print("Run grading first!")
    exit(1)

# Load into pandas DataFrame - super easy with JSONL!
df = pd.read_json(grades_file, lines=True)

print("=" * 60)
print("PANDAS ANALYSIS EXAMPLE")
print("=" * 60)
print()

# Filter to successful grades only
df_success = df[df["success"] == True]

print("1. Average score by model:")
print(df_success.groupby("tested_model")["score"].mean().round(1))
print()

print("2. Score statistics by assignment:")
print(df_success.groupby("assignment")["score"].describe().round(1))
print()

print("3. Total correct questions by model:")
print(df_success.groupby("tested_model")["total_correct"].sum())
print()

print("4. Success rate (non-null scores):")
print(df.groupby("tested_model")["success"].mean().round(3))
print()

# If you want to analyze per-question data, you can explode the questions dict
# Uncomment to see:
# print("5. Per-question results:")
# df_questions = df_success.explode("questions")
# print(df_questions["questions"].value_counts())

print("=" * 60)
print("\nTip: You can easily export to CSV for Excel:")
print("  df.to_csv('results.csv', index=False)")
print()
print("Or create visualizations with matplotlib/seaborn!")
print("=" * 60)
