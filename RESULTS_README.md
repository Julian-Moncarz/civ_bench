# Results and Grading Storage

## Directory Structure

```
responses/                    # Model answers to assignments
  {model_name}/
    trial_{n}/
      assignment_{n}_answer.json

grades/                      # Detailed grading results (organized)
  {grader_model}/
    {tested_model}/
      trial_{n}/
        assignment_{n}_grade_{n}.json

results/                     # Easy-to-analyze aggregated data
  grades.jsonl              # One line per grade (load with pandas!)
```

## Quick Analysis

### Using the built-in analyzer:
```bash
python analyze_results.py
```

### Using pandas (recommended for research):
```python
import pandas as pd

# Load all grades - one line!
df = pd.read_json('results/grades.jsonl', lines=True)

# Analyze
print(df.groupby('tested_model')['score'].mean())
print(df.groupby('assignment')['score'].describe())
```

See `example_analysis.py` for more examples.

## JSONL Format

Each line in `results/grades.jsonl` is a JSON object:
```json
{
  "grader_model": "google/gemini-2.5-flash",
  "tested_model": "anthropic/claude-sonnet-4.5",
  "assignment": 1,
  "trial": 0,
  "grade_num": 0,
  "timestamp": "2025-11-06T20:45:00.000000",
  "score": 85,
  "total_correct": 8,
  "total_questions": 10,
  "questions": {
    "1a": "correct",
    "1b": "partial",
    "2": "correct"
  },
  "summary": {
    "correct": 8,
    "partial": 1,
    "incorrect": 1
  },
  "success": true
}
```

## Benefits

✅ **Easy bulk analysis** - Load entire dataset with one line of pandas
✅ **No duplicate data** - Each grade stored once with minimal redundancy
✅ **Organized** - Detailed grades in logical directory structure
✅ **Reproducible** - Temperature=0 ensures consistent results
✅ **Per-question insights** - See which questions are hardest across models

## Tips

- Use `jq` for quick command-line queries:
  ```bash
  # Average score for a specific model
  jq -s 'map(select(.tested_model == "anthropic/claude-sonnet-4.5")) | map(.score) | add/length' results/grades.jsonl

  # List all questions marked as incorrect
  jq -r 'select(.questions != null) | .questions | to_entries[] | select(.value == "incorrect") | .key' results/grades.jsonl | sort -u
  ```

- Export to CSV for Excel:
  ```python
  df.to_csv('results.csv', index=False)
  ```

- Clear results to start fresh:
  ```bash
  rm results/grades.jsonl
  ```
