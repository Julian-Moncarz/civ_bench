"""
Deep analysis of CivBench grading patterns.
Investigates question-level performance, assignment difficulty, and anomalies.
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

def load_grades(grades_file='results/grades.jsonl'):
    """Load grades from JSONL file."""
    grades = []
    with open(grades_file, 'r') as f:
        for line in f:
            grades.append(json.loads(line.strip()))
    return pd.DataFrame(grades)

def create_heatmap(df, output_path='analysis/graphs/assignment_difficulty_heatmap.png'):
    """Create heatmap of model performance across assignments."""

    # Calculate mean score for each model/assignment combination
    pivot_data = df.groupby(['tested_model', 'assignment'])['normalized_score'].mean().unstack()

    # Clean up model names
    pivot_data.index = [name.split('/')[-1].replace('_', ' ').replace('-', ' ').title()
                        for name in pivot_data.index]

    # Create figure with custom size
    fig, ax = plt.subplots(figsize=(12, 6))

    # Create heatmap
    sns.heatmap(pivot_data, annot=True, fmt='.3f', cmap='RdYlGn',
                vmin=0, vmax=1, cbar_kws={'label': 'Average Score'},
                linewidths=1, linecolor='gray', ax=ax)

    ax.set_title('Model Performance Heatmap Across Assignments\n(Darker Red = Harder, Darker Green = Easier)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Assignment Number', fontsize=12, fontweight='bold')
    ax.set_ylabel('Model', fontsize=12, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()

    return pivot_data

def analyze_question_level_performance(df, output_path='analysis/graphs/question_level_analysis.png'):
    """Analyze which specific questions (a, b, c, d) are hardest."""

    # Expand questions column into separate rows
    question_data = []
    for _, row in df.iterrows():
        for q_letter, q_result in row['questions'].items():
            question_data.append({
                'assignment': row['assignment'],
                'tested_model': row['tested_model'],
                'question': q_letter,
                'result': q_result,
                'correct': 1 if q_result == 'correct' else 0.5 if q_result == 'partial' else 0
            })

    q_df = pd.DataFrame(question_data)

    # Calculate success rate per question per assignment
    pivot_data = q_df.groupby(['assignment', 'question'])['correct'].mean().unstack()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Heatmap of question difficulty by assignment
    sns.heatmap(pivot_data, annot=True, fmt='.2f', cmap='RdYlGn',
                vmin=0, vmax=1, cbar_kws={'label': 'Success Rate'},
                linewidths=1, linecolor='gray', ax=ax1)
    ax1.set_title('Question Difficulty by Assignment\n(Success Rate Across All Models)',
                  fontsize=12, fontweight='bold')
    ax1.set_xlabel('Question', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Assignment', fontsize=11, fontweight='bold')

    # Overall question difficulty across all assignments
    overall_q_perf = q_df.groupby('question')['correct'].agg(['mean', 'std', 'count'])

    x_pos = np.arange(len(overall_q_perf))
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']  # Red, Blue, Green, Orange

    bars = ax2.bar(x_pos, overall_q_perf['mean'], yerr=overall_q_perf['std'],
                   capsize=5, alpha=0.8, color=colors, edgecolor='black', linewidth=1.2)

    ax2.set_xlabel('Question', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Average Success Rate', fontsize=11, fontweight='bold')
    ax2.set_title('Overall Question Difficulty\n(Averaged Across All Assignments & Models)',
                  fontsize=12, fontweight='bold')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(overall_q_perf.index)
    ax2.set_ylim(0, 1.0)
    ax2.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar, val in zip(bars, overall_q_perf['mean']):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{val:.3f}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()

    return q_df, pivot_data, overall_q_perf

def investigate_grading_variance(df, output_path='analysis/graphs/grading_variance_investigation.png'):
    """Investigate why some assignment/model combos have high variance."""

    # Calculate variance for each assignment/model combo
    variance_data = df.groupby(['assignment', 'tested_model']).agg({
        'normalized_score': ['mean', 'std', 'count', 'min', 'max']
    })
    variance_data.columns = ['mean', 'std', 'count', 'min', 'max']
    variance_data['range'] = variance_data['max'] - variance_data['min']
    variance_data = variance_data.reset_index()

    # Filter to only those with variance > 0
    variable_grades = variance_data[variance_data['std'] > 0].copy()
    variable_grades['combo'] = variable_grades.apply(
        lambda x: f"A{x['assignment']}: {x['tested_model'].split('/')[-1][:15]}", axis=1
    )

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 1. Scatter: Mean vs Std Dev
    ax1 = axes[0, 0]
    scatter = ax1.scatter(variable_grades['mean'], variable_grades['std'],
                         s=variable_grades['count']*20, alpha=0.6, c=variable_grades['assignment'],
                         cmap='viridis', edgecolors='black', linewidth=1)
    ax1.set_xlabel('Mean Score', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Standard Deviation', fontsize=11, fontweight='bold')
    ax1.set_title('Grade Variability: Mean vs Std Dev\n(bubble size = number of grades)',
                  fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax1, label='Assignment')

    # 2. Distribution of variance across assignments
    ax2 = axes[0, 1]
    assignment_variance = variance_data.groupby('assignment')['std'].mean().sort_values(ascending=False)
    bars = ax2.bar(range(len(assignment_variance)), assignment_variance.values,
                   color=sns.color_palette("Reds_r", len(assignment_variance)),
                   edgecolor='black', linewidth=1.2)
    ax2.set_xlabel('Assignment', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Average Std Dev', fontsize=11, fontweight='bold')
    ax2.set_title('Which Assignments Have Most Variable Grading?',
                  fontsize=12, fontweight='bold')
    ax2.set_xticks(range(len(assignment_variance)))
    ax2.set_xticklabels([f'A{int(a)}' for a in assignment_variance.index])
    ax2.grid(axis='y', alpha=0.3)

    for bar, val in zip(bars, assignment_variance.values):
        ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.01,
                f'{val:.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # 3. Range (max - min) analysis
    ax3 = axes[1, 0]
    top_ranges = variable_grades.nlargest(10, 'range')[['combo', 'range', 'mean', 'count']]
    y_pos = np.arange(len(top_ranges))
    bars = ax3.barh(y_pos, top_ranges['range'], color='coral', edgecolor='black', linewidth=1.2)
    ax3.set_yticks(y_pos)
    ax3.set_yticklabels(top_ranges['combo'], fontsize=9)
    ax3.set_xlabel('Score Range (Max - Min)', fontsize=11, fontweight='bold')
    ax3.set_title('Top 10 Most Inconsistent Gradings\n(Largest range between min and max score)',
                  fontsize=12, fontweight='bold')
    ax3.grid(axis='x', alpha=0.3)

    for i, (bar, val) in enumerate(zip(bars, top_ranges['range'])):
        ax3.text(val + 0.02, bar.get_y() + bar.get_height()/2.,
                f'{val:.2f}', ha='left', va='center', fontsize=8, fontweight='bold')

    # 4. Count distribution - how many grades per combo?
    ax4 = axes[1, 1]
    count_dist = variance_data['count'].value_counts().sort_index()
    ax4.bar(count_dist.index, count_dist.values, color='skyblue', edgecolor='black', linewidth=1.2)
    ax4.set_xlabel('Number of Grades', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax4.set_title('Distribution of Sample Sizes\n(How many times was each combo graded?)',
                  fontsize=12, fontweight='bold')
    ax4.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()

    return variance_data, variable_grades

def analyze_perfect_vs_zero_scores(df, output_path='analysis/graphs/score_distribution.png'):
    """Analyze the distribution of scores - are they clustered at 0 and 1?"""

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))

    # 1. Overall score distribution
    ax1 = axes[0, 0]
    ax1.hist(df['normalized_score'], bins=20, color='steelblue', edgecolor='black', alpha=0.7)
    ax1.axvline(df['normalized_score'].mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {df["normalized_score"].mean():.3f}')
    ax1.axvline(df['normalized_score'].median(), color='green', linestyle='--', linewidth=2, label=f'Median: {df["normalized_score"].median():.3f}')
    ax1.set_xlabel('Normalized Score', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax1.set_title('Overall Score Distribution\n(Are grades bimodal?)',
                  fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)

    # 2. Score distribution by model
    ax2 = axes[0, 1]
    for model in df['tested_model'].unique():
        model_data = df[df['tested_model'] == model]['normalized_score']
        label = model.split('/')[-1].replace('_', ' ').title()[:20]
        ax2.hist(model_data, bins=10, alpha=0.5, label=label, edgecolor='black')
    ax2.set_xlabel('Normalized Score', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax2.set_title('Score Distribution by Model',
                  fontsize=12, fontweight='bold')
    ax2.legend(fontsize=8)
    ax2.grid(axis='y', alpha=0.3)

    # 3. Proportion of zeros, perfect scores, and partial
    ax3 = axes[1, 0]
    score_categories = pd.cut(df['normalized_score'], bins=[-0.1, 0, 0.99, 1.0],
                              labels=['Zero (0%)', 'Partial (1-99%)', 'Perfect (100%)'])
    category_counts = score_categories.value_counts()
    colors = ['#e74c3c', '#f39c12', '#2ecc71']
    wedges, texts, autotexts = ax3.pie(category_counts.values, labels=category_counts.index,
                                        autopct='%1.1f%%', colors=colors, startangle=90,
                                        textprops={'fontsize': 10, 'fontweight': 'bold'})
    ax3.set_title('Score Category Distribution\n(How often are scores 0%, partial, or 100%?)',
                  fontsize=12, fontweight='bold')

    # 4. Score categories by model
    ax4 = axes[1, 1]
    df['score_category'] = pd.cut(df['normalized_score'], bins=[-0.1, 0, 0.99, 1.0],
                                   labels=['Zero', 'Partial', 'Perfect'])
    category_by_model = pd.crosstab(df['tested_model'], df['score_category'], normalize='index') * 100
    category_by_model.index = [name.split('/')[-1].replace('_', ' ').title() for name in category_by_model.index]
    category_by_model.plot(kind='bar', stacked=True, ax=ax4, color=colors, edgecolor='black', linewidth=1)
    ax4.set_xlabel('Model', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Percentage', fontsize=11, fontweight='bold')
    ax4.set_title('Score Category Distribution by Model\n(Stacked %)',
                  fontsize=12, fontweight='bold')
    ax4.legend(title='Category', fontsize=9)
    ax4.set_xticklabels(ax4.get_xticklabels(), rotation=45, ha='right')
    ax4.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()

    return category_counts

def main():
    """Run deep analysis."""
    print("="*70)
    print("DEEP DIVE ANALYSIS - CivBench Grading Patterns")
    print("="*70)

    df = load_grades()
    df['normalized_score'] = df['total_correct'] / df['total_questions']

    print(f"\n📊 Loaded {len(df)} grades\n")

    # 1. Heatmap
    print("🔥 Creating assignment difficulty heatmap...")
    heatmap_data = create_heatmap(df)
    print("\n📊 HEATMAP INSIGHTS:")
    print(f"   - Hardest assignment overall: {heatmap_data.mean(axis=0).idxmin()} (avg: {heatmap_data.mean(axis=0).min():.3f})")
    print(f"   - Easiest assignment overall: {heatmap_data.mean(axis=0).idxmax()} (avg: {heatmap_data.mean(axis=0).max():.3f})")
    print(f"   - Most inconsistent assignment (across models): {heatmap_data.std(axis=0).idxmax()} (std: {heatmap_data.std(axis=0).max():.3f})")

    # 2. Question-level analysis
    print("\n📝 Analyzing question-level performance...")
    q_df, q_pivot, q_overall = analyze_question_level_performance(df)
    print("\n📊 QUESTION-LEVEL INSIGHTS:")
    print(f"   - Hardest question overall: {q_overall['mean'].idxmin()} (success rate: {q_overall['mean'].min():.3f})")
    print(f"   - Easiest question overall: {q_overall['mean'].idxmax()} (success rate: {q_overall['mean'].max():.3f})")
    print("\n   Question difficulty ranking:")
    for q, rate in q_overall['mean'].sort_values().items():
        print(f"     {q}: {rate:.3f} ({rate*100:.1f}% success rate)")

    # 3. Variance investigation
    print("\n🔍 Investigating grading variance patterns...")
    variance_data, variable_grades = investigate_grading_variance(df)
    print("\n📊 VARIANCE INSIGHTS:")
    high_var = variance_data.nlargest(3, 'std')
    print("   Top 3 most variable gradings:")
    for _, row in high_var.iterrows():
        print(f"     Assignment {int(row['assignment'])}, {row['tested_model'].split('/')[-1]}: std={row['std']:.3f}, range={row['range']:.3f}")

    # 4. Score distribution
    print("\n📈 Analyzing score distributions...")
    category_counts = analyze_perfect_vs_zero_scores(df)
    print("\n📊 SCORE DISTRIBUTION INSIGHTS:")
    print(f"   - Zero scores: {category_counts.get('Zero (0%)', 0)} ({category_counts.get('Zero (0%)', 0)/len(df)*100:.1f}%)")
    print(f"   - Partial scores: {category_counts.get('Partial (1-99%)', 0)} ({category_counts.get('Partial (1-99%)', 0)/len(df)*100:.1f}%)")
    print(f"   - Perfect scores: {category_counts.get('Perfect (100%)', 0)} ({category_counts.get('Perfect (100%)', 0)/len(df)*100:.1f}%)")

    print("\n" + "="*70)
    print("✅ Deep analysis complete! Check analysis/graphs/ for all visualizations.")
    print("="*70)

if __name__ == "__main__":
    main()
