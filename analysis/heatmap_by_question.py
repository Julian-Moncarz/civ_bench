"""
Generate a heatmap showing model performance by assignment.
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

def load_grades(grades_file='results/grades.jsonl'):
    """Load grades from JSONL file."""
    grades = []
    with open(grades_file, 'r') as f:
        for line in f:
            grades.append(json.loads(line.strip()))
    return pd.DataFrame(grades)

def prepare_assignment_performance_data(df):
    """
    Extract per-assignment performance for each model.
    Returns a dataframe with models as rows and assignments as columns.
    """
    # Calculate average score per model per assignment
    assignment_scores = []
    for _, row in df.iterrows():
        model = row['tested_model']
        assignment = row['assignment']

        # Calculate score for this assignment (average across all questions)
        questions = row['questions']
        total = 0
        count = 0
        for result in questions.values():
            if result == "correct":
                total += 1.0
            elif result == "partial":
                total += 0.5
            # incorrect adds 0
            count += 1

        score = total / count if count > 0 else 0

        assignment_scores.append({
            'model': model,
            'assignment': f"A{assignment}",
            'score': score
        })

    assignment_df = pd.DataFrame(assignment_scores)

    # Calculate average score per model per assignment (across multiple grading trials)
    pivot_data = assignment_df.groupby(['model', 'assignment'])['score'].mean().reset_index()

    # Create pivot table for heatmap
    heatmap_data = pivot_data.pivot(index='model', columns='assignment', values='score')

    # Sort columns by assignment number
    def sort_key(col):
        return int(col[1:])  # Remove 'A' prefix and convert to int

    sorted_cols = sorted(heatmap_data.columns, key=sort_key)
    heatmap_data = heatmap_data[sorted_cols]

    return heatmap_data

def clean_model_name(model):
    """Clean up model name for display."""
    name = model.split('/')[-1] if '/' in model else model
    # Keep underscores and hyphens readable
    name = name.replace('_', ' ').replace('-', ' ')
    return name

def plot_assignment_heatmap(output_path='analysis/graphs/model_performance_by_assignment.png'):
    """Create heatmap of model performance by assignment."""

    print("Loading grades data...")
    df = load_grades()

    print("Preparing assignment performance data...")
    heatmap_data = prepare_assignment_performance_data(df)

    # Clean up model names for better display
    heatmap_data.index = [clean_model_name(model) for model in heatmap_data.index]

    # Sort models by overall performance (average score across all assignments)
    model_avg = heatmap_data.mean(axis=1).sort_values(ascending=False)
    heatmap_data = heatmap_data.loc[model_avg.index]

    # Calculate figure size based on data dimensions
    n_assignments = len(heatmap_data.columns)
    n_models = len(heatmap_data.index)
    fig_width = max(10, n_assignments * 1.2)
    fig_height = max(6, n_models * 0.6)

    # Create the heatmap
    plt.figure(figsize=(fig_width, fig_height))
    ax = plt.gca()

    # Use a diverging colormap centered at 0.5 (partial credit)
    sns.heatmap(heatmap_data,
                annot=True,  # Show values in cells
                fmt='.2f',   # Format as 2 decimal places
                cmap='RdYlGn',  # Red-Yellow-Green colormap
                vmin=0, vmax=1,  # Score range
                cbar_kws={'label': 'Average Score'},
                linewidths=0.5,
                linecolor='gray',
                ax=ax)

    ax.set_xlabel('Assignment', fontsize=12, fontweight='bold')
    ax.set_ylabel('Model', fontsize=12, fontweight='bold')
    ax.set_title('Model Performance by Assignment\n(averaged across grading trials)',
                 fontsize=14, fontweight='bold', pad=20)

    # Rotate x-axis labels for better readability
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    plt.setp(ax.get_yticklabels(), rotation=0)

    # Create output directory if it doesn't exist
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved heatmap: {output_path}")
    plt.close()

    # Print summary statistics
    print("\n" + "="*70)
    print("ASSIGNMENT DIFFICULTY SUMMARY")
    print("="*70)

    # Calculate average score per assignment (difficulty)
    assignment_avg = heatmap_data.mean(axis=0).sort_values()
    print("\nAssignment difficulty (from easiest to hardest):")
    print(assignment_avg.sort_values(ascending=False).to_string())

    print("\n" + "="*70)
    print("MODEL PERFORMANCE SUMMARY")
    print("="*70)
    print(model_avg.to_string())

    print("\n✅ Heatmap generation complete!")

    return heatmap_data

if __name__ == "__main__":
    plot_assignment_heatmap()
