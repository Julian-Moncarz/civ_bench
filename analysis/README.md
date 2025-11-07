# CivBench Grading Analysis

This directory contains comprehensive analysis of the CivBench grading data.

## 📊 Generated Visualizations

### Core Visualizations

1. **`graphs/model_performance.png`** - Bar chart showing average scores by model with error bars
2. **`graphs/grader_consistency.png`** - Box plots showing score distributions for each assignment/model combo
3. **`graphs/assignment_difficulty_heatmap.png`** - Heatmap of model performance across assignments
4. **`graphs/question_level_analysis.png`** - Question-by-question difficulty analysis
5. **`graphs/grading_variance_investigation.png`** - Deep dive into grading inconsistencies
6. **`graphs/score_distribution.png`** - Overall score distribution patterns
7. **`graphs/master_findings_report.png`** - **⭐ START HERE** - Comprehensive single-page findings report

### Recommended Viewing Order
1. Start with `master_findings_report.png` for complete overview
2. Dive into specific areas based on interest

## 🔬 Analysis Scripts

### `analyze_grades.py`
Basic analysis with model performance and grader consistency metrics.

**Run:** `python3 analysis/analyze_grades.py`

**Outputs:**
- Model performance bar chart
- Grader consistency box plots
- Summary statistics to console

### `deep_analysis.py`
Advanced analysis with heatmaps, question-level breakdowns, and variance investigations.

**Run:** `python3 analysis/deep_analysis.py`

**Outputs:**
- Assignment difficulty heatmap
- Question-level analysis
- Grading variance investigation
- Score distribution analysis

### `findings_report.py`
Generates comprehensive single-page findings report with all key insights.

**Run:** `python3 analysis/findings_report.py`

**Output:**
- Master findings report (recommended for sharing)

## 🔍 Key Findings Summary

### 1. CRITICAL: Grader Reliability Issue
- **Root Cause:** `GRADER_TEMPERATURE=1` in config.py causes non-deterministic grading
- **Impact:** Same answer receives wildly different scores (Assignment 5 range: 0.33-1.0)
- **Fix:** Set `GRADER_TEMPERATURE=0` for reproducible results

### 2. Model Performance Rankings
1. **Gemini 2.5 Pro:** 0.281 ± 0.356 (best)
2. **Grok-4:** 0.163 ± 0.257
3. **Claude Opus 4.1:** 0.138 ± 0.237
4. **Claude Sonnet 4.5:** 0.130 ± 0.232

### 3. Assignment Difficulty Patterns
- **Hardest:** Assignments 4, 6, 7 (avg ≈ 0.000) - near-universal failure
- **Easiest:** Assignment 1 (avg = 0.586)
- **Most Variable:** Assignment 5 (std = 0.304) - due to grader temperature issue

### 4. Score Distribution Anomaly
- **52%** of all grades are ZERO
- Only **7%** are perfect scores
- **40%** partial credit
- Bimodal distribution suggests assignments may be too difficult or grading is too strict

### 5. Assignment 4 Investigation
- **All models score 0%** on Assignment 4 (Quebec Bridge truss analysis)
- This is **legitimate failure**, not a grading bug
- Models produce answers that differ from ground truth by 50%+ (e.g., Ry: 79200 kN expected vs 36100 kN provided)
- Indicates current vision-language models struggle with complex structural analysis

### 6. Answer Truncation Issues
- Some model responses are cut off mid-answer (Assignment 5 example)
- Causes incomplete grading (3 questions graded instead of 6)
- Check `max_tokens` configuration

### 7. Question-Level Insights
- **Question "1f":** Impossible (0% success) - may be mislabeled
- **Questions "d", "e":** Consistently difficult (13-21% success)
- **Question "3a":** Perfect (100% success) - possible ground truth issue

## 📈 Data Structure

### Input Data
- **`results/grades.jsonl`** - All grading results (162 grades)
- **`grades/`** - Detailed grade files organized by grader/model/trial/assignment

### Grading Structure
- **Grader:** google/gemini-2.5-flash (single grader)
- **Models Tested:** 4 (Claude Opus 4.1, Claude Sonnet 4.5, Gemini 2.5 Pro, Grok-4)
- **Assignments:** 1, 2, 4, 5, 6, 7 (no assignment 3)
- **Grades per assignment:** 10 (for consistency checking)

## 🎯 Recommendations

### Immediate Actions
1. ✅ **Set `GRADER_TEMPERATURE=0`** in config.py
2. ✅ Review assignments 4, 6, 7 for clarity and difficulty
3. ✅ Increase `max_tokens` for model responses to prevent truncation
4. ✅ Audit ground truth for questions with 0% or 100% success

### Future Improvements
- Consider ensemble grading (3 graders, majority vote)
- Add answer length validation before grading
- Implement more granular partial credit rubrics
- Add intermediate step checking for partial credit
- Test additional models to expand benchmark coverage

## 📚 Assignments Overview

| Assignment | Topic | Difficulty | Avg Score |
|------------|-------|------------|-----------|
| 1 | Statics & Mechanics | Medium | 0.586 |
| 2 | Material Properties | Medium-Hard | 0.200 |
| 4 | Truss Analysis (Quebec Bridge) | Very Hard | 0.000 |
| 5 | Structural Design (HSS Selection) | Hard | 0.722* |
| 6 | Beam Dynamics | Very Hard | 0.000 |
| 7 | Beam Bending Analysis | Very Hard | 0.000 |

*Assignment 5 score highly variable due to grader temperature issue

## 🔧 Dependencies

```bash
pip install pandas matplotlib seaborn numpy
```

## 📝 Notes

- All visualizations are high-resolution (300 DPI) PNG files
- Scripts are designed to be run from project root
- Console output includes detailed statistics and insights
- Analysis is automated and can be re-run as new grades are added

---

**Last Updated:** 2025-11-06
**Data Analyzed:** 162 grades across 4 models and 6 assignments
