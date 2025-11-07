"""
Compare how different models answered the same questions.
Creates visualizations showing model response patterns and differences.
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from collections import defaultdict

sns.set_style("whitegrid")

def load_grades():
    """Load all grades."""
    grades = []
    with open('results/grades.jsonl', 'r') as f:
        for line in f:
            grades.append(json.loads(line.strip()))
    df = pd.DataFrame(grades)
    df['normalized_score'] = df['total_correct'] / df['total_questions']
    return df

def analyze_model_answer_patterns(df):
    """Analyze how models answer differently across assignments."""

    # Create a comparison matrix showing which models succeed on which questions
    model_question_success = []

    for _, row in df.iterrows():
        model_name = row['tested_model'].split('/')[-1]
        assignment = row['assignment']

        for q_id, result in row['questions'].items():
            score = 1 if result == 'correct' else 0.5 if result == 'partial' else 0
            model_question_success.append({
                'model': model_name,
                'assignment': assignment,
                'question': f"A{assignment}_{q_id}",
                'score': score,
                'result': result
            })

    return pd.DataFrame(model_question_success)

def plot_model_comparison(df, output_path='analysis/graphs/model_answer_comparison.png'):
    """Create comprehensive model comparison visualization."""

    fig = plt.figure(figsize=(18, 14))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    # Clean model names
    df['model_clean'] = df['tested_model'].str.split('/').str[-1].str.replace('_', '-')

    # 1. Success rate by model and assignment
    ax1 = fig.add_subplot(gs[0, :])
    pivot = df.groupby(['model_clean', 'assignment'])['normalized_score'].mean().unstack(fill_value=0)

    x = np.arange(len(pivot.columns))
    width = 0.2
    colors = sns.color_palette("husl", len(pivot))

    for i, (model, scores) in enumerate(pivot.iterrows()):
        offset = (i - len(pivot)/2 + 0.5) * width
        bars = ax1.bar(x + offset, scores.values, width, label=model, color=colors[i],
                      edgecolor='black', linewidth=1, alpha=0.85)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            if height > 0.05:
                ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                        f'{height:.2f}', ha='center', va='bottom', fontsize=7, rotation=0)

    ax1.set_xlabel('Assignment', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Average Score', fontsize=12, fontweight='bold')
    ax1.set_title('Model Performance Comparison Across Assignments', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels([f'A{int(col)}' for col in pivot.columns])
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(axis='y', alpha=0.3)
    ax1.set_ylim(0, 1.1)

    # 2. Question-level heatmap - which models succeed on which questions?
    ax2 = fig.add_subplot(gs[1, :])

    mq_df = analyze_model_answer_patterns(df)
    # Focus on questions that have some variance (not all 0 or all 1)
    question_variance = mq_df.groupby('question')['score'].std()
    interesting_questions = question_variance[question_variance > 0.1].index[:30]  # Top 30 most variable

    pivot_mq = mq_df[mq_df['question'].isin(interesting_questions)].pivot_table(
        index='model', columns='question', values='score', aggfunc='mean'
    )

    if len(pivot_mq) > 0:
        sns.heatmap(pivot_mq, annot=False, cmap='RdYlGn', vmin=0, vmax=1,
                   cbar_kws={'label': 'Score'}, linewidths=0.5, linecolor='gray', ax=ax2)
        ax2.set_title('Model Performance Heatmap: Top 30 Most Variable Questions\n(Shows where models differ most)',
                     fontsize=13, fontweight='bold')
        ax2.set_xlabel('Question ID', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Model', fontsize=11, fontweight='bold')
        ax2.set_xticklabels(ax2.get_xticklabels(), rotation=90, fontsize=7)
        ax2.set_yticklabels(ax2.get_yticklabels(), rotation=0, fontsize=10)

    # 3. Correct vs Partial vs Incorrect breakdown by model
    ax3 = fig.add_subplot(gs[2, 0])

    result_counts = []
    for model in df['model_clean'].unique():
        model_grades = df[df['model_clean'] == model]
        for _, grade in model_grades.iterrows():
            for result in grade['questions'].values():
                result_counts.append({'model': model, 'result': result})

    result_df = pd.DataFrame(result_counts)
    result_pivot = pd.crosstab(result_df['model'], result_df['result'], normalize='index') * 100

    result_pivot.plot(kind='bar', stacked=True, ax=ax3,
                     color={'correct': '#2ecc71', 'partial': '#f39c12', 'incorrect': '#e74c3c'},
                     edgecolor='black', linewidth=1)
    ax3.set_title('Answer Quality Breakdown by Model\n(Percentage of questions)', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Model', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Percentage', fontsize=11, fontweight='bold')
    ax3.set_xticklabels(ax3.get_xticklabels(), rotation=45, ha='right')
    ax3.legend(title='Result', fontsize=9, loc='upper right')
    ax3.grid(axis='y', alpha=0.3)

    # 4. Model consistency - std dev of scores
    ax4 = fig.add_subplot(gs[2, 1])

    consistency = df.groupby('model_clean')['normalized_score'].agg(['mean', 'std']).sort_values('std')

    colors_bar = ['#2ecc71' if std < 0.3 else '#f39c12' if std < 0.35 else '#e74c3c'
                  for std in consistency['std'].values]

    bars = ax4.barh(range(len(consistency)), consistency['std'], color=colors_bar,
                    edgecolor='black', linewidth=1.5, alpha=0.85)
    ax4.set_yticks(range(len(consistency)))
    ax4.set_yticklabels(consistency.index, fontsize=10)
    ax4.set_xlabel('Standard Deviation of Scores', fontsize=11, fontweight='bold')
    ax4.set_title('Model Consistency\n(Lower = More Consistent Performance)', fontsize=12, fontweight='bold')
    ax4.grid(axis='x', alpha=0.3)

    for i, (bar, val) in enumerate(zip(bars, consistency['std'].values)):
        ax4.text(val + 0.01, bar.get_y() + bar.get_height()/2.,
                f'{val:.3f}', ha='left', va='center', fontsize=10, fontweight='bold')

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()

def print_model_comparison_stats(df):
    """Print detailed comparison statistics."""
    print("\n" + "="*70)
    print("MODEL COMPARISON STATISTICS")
    print("="*70)

    for model in df['tested_model'].unique():
        model_data = df[df['tested_model'] == model]
        model_name = model.split('/')[-1]

        print(f"\n{model_name}:")
        print(f"  Total grades: {len(model_data)}")
        print(f"  Average score: {model_data['normalized_score'].mean():.3f}")
        print(f"  Std dev: {model_data['normalized_score'].std():.3f}")
        print(f"  Best assignment: {model_data.groupby('assignment')['normalized_score'].mean().idxmax()}")
        print(f"  Worst assignment: {model_data.groupby('assignment')['normalized_score'].mean().idxmin()}")

        # Count result types
        total_questions = 0
        correct = 0
        partial = 0
        incorrect = 0

        for _, row in model_data.iterrows():
            for result in row['questions'].values():
                total_questions += 1
                if result == 'correct':
                    correct += 1
                elif result == 'partial':
                    partial += 1
                else:
                    incorrect += 1

        print(f"  Question results:")
        print(f"    Correct: {correct}/{total_questions} ({correct/total_questions*100:.1f}%)")
        print(f"    Partial: {partial}/{total_questions} ({partial/total_questions*100:.1f}%)")
        print(f"    Incorrect: {incorrect}/{total_questions} ({incorrect/total_questions*100:.1f}%)")

    # Head-to-head comparisons
    print("\n" + "="*70)
    print("HEAD-TO-HEAD ASSIGNMENT WINS")
    print("="*70)

    for assignment in sorted(df['assignment'].unique()):
        assignment_data = df[df['assignment'] == assignment]
        winner = assignment_data.groupby('tested_model')['normalized_score'].mean().idxmax()
        winner_score = assignment_data.groupby('tested_model')['normalized_score'].mean().max()

        print(f"\nAssignment {assignment}:")
        print(f"  Winner: {winner.split('/')[-1]} (score: {winner_score:.3f})")

        # Show all scores for this assignment
        for model in sorted(df['tested_model'].unique()):
            model_score = assignment_data[assignment_data['tested_model'] == model]['normalized_score'].mean()
            model_name = model.split('/')[-1]
            # Handle NaN case
            if pd.isna(model_score):
                bar = ""
                score_str = "N/A"
            else:
                bar = "█" * int(model_score * 30)
                score_str = f"{model_score:.3f}"
            print(f"  {model_name:25s} {score_str:>6s} {bar}")

def main():
    print("\n" + "="*70)
    print("MODEL COMPARISON ANALYSIS")
    print("="*70)

    df = load_grades()

    print(f"\nLoaded {len(df)} grades across {df['tested_model'].nunique()} models")

    plot_model_comparison(df)
    print_model_comparison_stats(df)

    print("\n" + "="*70)
    print("✅ Model comparison complete!")
    print("="*70)

if __name__ == "__main__":
    main()
