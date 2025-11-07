"""
Analysis script for CivBench grading data.
Loads grades and generates visualizations for model performance and grader consistency.
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from collections import defaultdict

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 11

def load_grades(grades_file='results/grades.jsonl'):
    """Load grades from JSONL file."""
    grades = []
    with open(grades_file, 'r') as f:
        for line in f:
            grades.append(json.loads(line.strip()))
    return pd.DataFrame(grades)

def calculate_normalized_scores(df):
    """Calculate normalized scores (0-1 range) for each grade."""
    df['normalized_score'] = df['total_correct'] / df['total_questions']
    return df

def analyze_model_performance(df):
    """Calculate average performance metrics per model."""
    performance = df.groupby('tested_model').agg({
        'normalized_score': ['mean', 'std', 'count', 'sem']
    }).round(4)
    performance.columns = ['mean_score', 'std_dev', 'n_grades', 'std_error']
    performance = performance.sort_values('mean_score', ascending=False)
    return performance

def plot_model_performance(df, output_path='analysis/graphs/model_performance.png'):
    """Create bar chart of model performance with error bars."""
    performance = analyze_model_performance(df)

    # Clean up model names for display
    display_names = []
    for model in performance.index:
        # Extract just the model name without provider prefix
        name = model.split('/')[-1] if '/' in model else model
        # Make it more readable
        name = name.replace('_', ' ').replace('-', ' ').title()
        display_names.append(name)

    fig, ax = plt.subplots(figsize=(10, 6))

    x_pos = np.arange(len(performance))
    colors = sns.color_palette("husl", len(performance))

    bars = ax.bar(x_pos, performance['mean_score'],
                   yerr=performance['std_dev'],
                   capsize=5, alpha=0.8, color=colors,
                   edgecolor='black', linewidth=1.2)

    ax.set_xlabel('Model', fontsize=13, fontweight='bold')
    ax.set_ylabel('Average Score (0-1)', fontsize=13, fontweight='bold')
    ax.set_title('Model performance on our civ homework',
                 fontsize=15, fontweight='bold', pad=20)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(display_names, rotation=45, ha='right')
    ax.set_ylim(0, 1.0)

    # Add value labels on bars
    for i, (bar, val, std) in enumerate(zip(bars, performance['mean_score'], performance['std_dev'])):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + std + 0.02,
                f'{val:.3f}\n±{std:.3f}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Add sample size info
    for i, (bar, n) in enumerate(zip(bars, performance['n_grades'])):
        ax.text(bar.get_x() + bar.get_width()/2., 0.02,
                f'n={int(n)}',
                ha='center', va='bottom', fontsize=8, alpha=0.7)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()

    return performance

def analyze_grader_consistency(df):
    """Analyze how consistent grades are for the same assignment/model combo."""
    # Group by assignment and tested model to see variance
    consistency = df.groupby(['assignment', 'tested_model']).agg({
        'normalized_score': ['mean', 'std', 'count', 'min', 'max']
    }).round(4)
    consistency.columns = ['mean', 'std_dev', 'n_grades', 'min', 'max']
    consistency['range'] = consistency['max'] - consistency['min']
    return consistency.sort_values('std_dev', ascending=False)

def plot_grader_consistency(df, output_path='analysis/graphs/grader_consistency.png'):
    """Create box plots showing score distributions for each assignment/model combo."""

    # Create a more readable identifier
    df['combo'] = df.apply(lambda x: f"A{x['assignment']}: {x['tested_model'].split('/')[-1].replace('_', ' ').replace('-', ' ').title()[:20]}", axis=1)

    # Calculate number of unique combos to determine figure size
    n_combos = df['combo'].nunique()
    fig_height = max(8, n_combos * 0.4)

    fig, ax = plt.subplots(figsize=(12, fig_height))

    # Sort by assignment then model for better organization
    df_sorted = df.sort_values(['assignment', 'tested_model'])
    combo_order = df_sorted['combo'].unique()

    sns.boxplot(data=df, y='combo', x='normalized_score',
                order=combo_order, palette="Set2", ax=ax)

    # Add scatter points to show individual grades
    sns.stripplot(data=df, y='combo', x='normalized_score',
                  order=combo_order, color='black', alpha=0.3, size=3, ax=ax)

    ax.set_xlabel('Score (0-1)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Assignment : Model', fontsize=13, fontweight='bold')
    ax.set_title('Grader Consistency: Score Distribution by Assignment & Model\n(box = IQR, whiskers = range, dots = individual grades)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlim(-0.05, 1.05)

    # Add grid for easier reading
    ax.grid(axis='x', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()

def print_summary_stats(df):
    """Print summary statistics to console."""
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)

    print(f"\nTotal Grades: {len(df)}")
    print(f"Grader Model: {df['grader_model'].unique()[0]}")
    print(f"Models Tested: {df['tested_model'].nunique()}")
    print(f"Assignments: {sorted(df['assignment'].unique())}")
    print(f"Grades per assignment/model: {df['grade_num'].max() + 1}")

    print("\n" + "-"*70)
    print("MODEL PERFORMANCE SUMMARY")
    print("-"*70)
    performance = analyze_model_performance(df)
    print(performance.to_string())

    print("\n" + "-"*70)
    print("GRADER CONSISTENCY (Top 10 Most Variable)")
    print("-"*70)
    consistency = analyze_grader_consistency(df)
    print(consistency.head(10).to_string())

    print("\n" + "-"*70)
    print("GRADER CONSISTENCY (Top 10 Most Consistent)")
    print("-"*70)
    print(consistency.tail(10).to_string())

    print("\n" + "="*70)

def main():
    """Main analysis pipeline."""
    print("Loading grades data...")
    df = load_grades()
    df = calculate_normalized_scores(df)

    print(f"Loaded {len(df)} grades")

    # Generate visualizations
    print("\nGenerating visualizations...")
    plot_model_performance(df)
    plot_grader_consistency(df)

    # Print summary statistics
    print_summary_stats(df)

    print("\n✅ Analysis complete! Check the analysis/graphs/ folder for visualizations.")

if __name__ == "__main__":
    main()
