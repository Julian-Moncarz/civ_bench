"""
Generate comprehensive findings report with visualizations.
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

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

def create_master_findings_visualization(df):
    """Create a comprehensive multi-panel findings visualization."""

    fig = plt.figure(figsize=(20, 24))
    gs = fig.add_gridspec(6, 2, hspace=0.35, wspace=0.25)

    # ==================== PANEL 1: Model Performance ====================
    ax1 = fig.add_subplot(gs[0, :])
    performance = df.groupby('tested_model').agg({
        'normalized_score': ['mean', 'std', 'count']
    })
    performance.columns = ['mean', 'std', 'n']
    performance = performance.sort_values('mean', ascending=False)

    model_names = [name.split('/')[-1].replace('_', '-') for name in performance.index]
    x_pos = np.arange(len(performance))
    colors = sns.color_palette("husl", len(performance))

    bars = ax1.bar(x_pos, performance['mean'], yerr=performance['std'],
                   capsize=8, alpha=0.85, color=colors, edgecolor='black', linewidth=1.5)
    ax1.set_title('🏆 Model Performance Comparison (with std dev error bars)',
                  fontsize=16, fontweight='bold', pad=15)
    ax1.set_xlabel('Model', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Average Score (0-1)', fontsize=13, fontweight='bold')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(model_names, rotation=0, ha='center', fontsize=11)
    ax1.set_ylim(0, 0.5)
    ax1.grid(axis='y', alpha=0.4)

    for i, (bar, val, std, n) in enumerate(zip(bars, performance['mean'], performance['std'], performance['n'])):
        ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + std + 0.015,
                f'{val:.3f}±{std:.3f}\n(n={int(n)})',
                ha='center', va='bottom', fontsize=10, fontweight='bold')

    # ==================== PANEL 2: Assignment Difficulty Heatmap ====================
    ax2 = fig.add_subplot(gs[1, :])
    pivot = df.groupby(['tested_model', 'assignment'])['normalized_score'].mean().unstack()
    pivot.index = [name.split('/')[-1].replace('_', '-') for name in pivot.index]

    im = ax2.imshow(pivot.values, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
    ax2.set_xticks(np.arange(len(pivot.columns)))
    ax2.set_yticks(np.arange(len(pivot.index)))
    ax2.set_xticklabels([f'A{int(col)}' for col in pivot.columns], fontsize=11)
    ax2.set_yticklabels(pivot.index, fontsize=11)
    ax2.set_title('🎯 Assignment Difficulty Heatmap (Model × Assignment Performance)',
                  fontsize=16, fontweight='bold', pad=15)
    ax2.set_xlabel('Assignment', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Model', fontsize=13, fontweight='bold')

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.iloc[i, j]
            color = 'white' if val < 0.4 else 'black'
            ax2.text(j, i, f'{val:.2f}', ha='center', va='center',
                    color=color, fontsize=10, fontweight='bold')

    cbar = plt.colorbar(im, ax=ax2, fraction=0.046, pad=0.04)
    cbar.set_label('Score (0=Red, 1=Green)', fontsize=11, fontweight='bold')

    # ==================== PANEL 3: Score Distribution ====================
    ax3 = fig.add_subplot(gs[2, 0])
    ax3.hist(df['normalized_score'], bins=20, color='steelblue', edgecolor='black', alpha=0.8, linewidth=1.5)
    ax3.axvline(df['normalized_score'].mean(), color='red', linestyle='--', linewidth=3,
               label=f'Mean: {df["normalized_score"].mean():.3f}')
    ax3.axvline(df['normalized_score'].median(), color='green', linestyle='--', linewidth=3,
               label=f'Median: {df["normalized_score"].median():.3f}')
    ax3.set_xlabel('Score', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Frequency', fontsize=12, fontweight='bold')
    ax3.set_title('📊 Overall Score Distribution\n(Heavily bimodal: mostly zeros)', fontsize=14, fontweight='bold')
    ax3.legend(fontsize=11, loc='upper right')
    ax3.grid(axis='y', alpha=0.4)

    # ==================== PANEL 4: Zero/Partial/Perfect Breakdown ====================
    ax4 = fig.add_subplot(gs[2, 1])
    df['score_cat'] = pd.cut(df['normalized_score'], bins=[-0.1, 0, 0.99, 1.0],
                              labels=['Zero (0%)', 'Partial', 'Perfect (100%)'])
    cat_counts = df['score_cat'].value_counts()
    colors_pie = ['#e74c3c', '#f39c12', '#2ecc71']
    wedges, texts, autotexts = ax4.pie(cat_counts.values, labels=cat_counts.index,
                                        autopct=lambda p: f'{p:.1f}%\n({int(p*len(df)/100)})',
                                        colors=colors_pie, startangle=90,
                                        textprops={'fontsize': 11, 'fontweight': 'bold'},
                                        explode=[0.05, 0, 0])
    ax4.set_title('🎂 Score Category Breakdown\n52% of grades are ZERO!', fontsize=14, fontweight='bold')

    # ==================== PANEL 5: Grading Variance by Assignment ====================
    ax5 = fig.add_subplot(gs[3, 0])
    variance_by_assignment = df.groupby(['assignment', 'tested_model'])['normalized_score'].std().reset_index()
    variance_by_assignment_agg = variance_by_assignment.groupby('assignment')['normalized_score'].mean().sort_values(ascending=False)

    bars = ax5.bar(range(len(variance_by_assignment_agg)), variance_by_assignment_agg.values,
                   color=sns.color_palette("Reds_r", len(variance_by_assignment_agg)),
                   edgecolor='black', linewidth=1.5, alpha=0.85)
    ax5.set_xlabel('Assignment', fontsize=12, fontweight='bold')
    ax5.set_ylabel('Average Std Dev', fontsize=12, fontweight='bold')
    ax5.set_title('⚠️ Grading Variance by Assignment\n(Higher = More Inconsistent)', fontsize=14, fontweight='bold')
    ax5.set_xticks(range(len(variance_by_assignment_agg)))
    ax5.set_xticklabels([f'A{int(a)}' for a in variance_by_assignment_agg.index], fontsize=11)
    ax5.grid(axis='y', alpha=0.4)

    for bar, val in zip(bars, variance_by_assignment_agg.values):
        ax5.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.005,
                f'{val:.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # ==================== PANEL 6: Question-Level Difficulty ====================
    ax6 = fig.add_subplot(gs[3, 1])

    # Expand questions
    q_data = []
    for _, row in df.iterrows():
        for q_letter, q_result in row['questions'].items():
            q_data.append({
                'question': q_letter,
                'correct': 1 if q_result == 'correct' else 0.5 if q_result == 'partial' else 0
            })
    q_df = pd.DataFrame(q_data)
    q_perf = q_df.groupby('question')['correct'].mean().sort_values()

    # Take top 15 hardest and easiest
    top_hard = q_perf.head(8)
    top_easy = q_perf.tail(8)
    combined = pd.concat([top_hard, top_easy])

    colors_q = ['#e74c3c' if v < 0.3 else '#f39c12' if v < 0.7 else '#2ecc71' for v in combined.values]
    bars = ax6.barh(range(len(combined)), combined.values, color=colors_q,
                    edgecolor='black', linewidth=1.2, alpha=0.85)
    ax6.set_yticks(range(len(combined)))
    ax6.set_yticklabels(combined.index, fontsize=10)
    ax6.set_xlabel('Success Rate', fontsize=12, fontweight='bold')
    ax6.set_title('📝 Question Difficulty\n(Hardest 8 + Easiest 8)', fontsize=14, fontweight='bold')
    ax6.set_xlim(0, 1)
    ax6.grid(axis='x', alpha=0.4)

    for i, (bar, val) in enumerate(zip(bars, combined.values)):
        ax6.text(val + 0.03, bar.get_y() + bar.get_height()/2.,
                f'{val:.3f}', ha='left', va='center', fontsize=9, fontweight='bold')

    # ==================== PANEL 7: Critical Finding - Assignment 5 Variance ====================
    ax7 = fig.add_subplot(gs[4, :])

    # Get all assignment 5 grades for gemini-2.5-pro
    a5_grades = df[(df['assignment'] == 5) & (df['tested_model'].str.contains('gemini-2.5-pro'))]

    if len(a5_grades) > 0:
        scores = a5_grades['normalized_score'].values
        x_pos = np.arange(len(scores))

        bars = ax7.bar(x_pos, scores, color='coral', edgecolor='black', linewidth=1.5, alpha=0.85)
        ax7.axhline(scores.mean(), color='red', linestyle='--', linewidth=2,
                   label=f'Mean: {scores.mean():.3f}')
        ax7.axhline(scores.mean() + scores.std(), color='orange', linestyle=':', linewidth=2,
                   label=f'+1 SD: {scores.mean() + scores.std():.3f}')
        ax7.axhline(scores.mean() - scores.std(), color='orange', linestyle=':', linewidth=2,
                   label=f'-1 SD: {scores.mean() - scores.std():.3f}')

        ax7.set_xlabel('Grade Attempt Number', fontsize=13, fontweight='bold')
        ax7.set_ylabel('Score', fontsize=13, fontweight='bold')
        ax7.set_title('🚨 CRITICAL: Assignment 5 (Gemini 2.5 Pro) - SAME Answer, WILDLY Different Scores\n' +
                     f'Range: {scores.min():.3f} to {scores.max():.3f} | Std Dev: {scores.std():.3f} | ' +
                     'Root Cause: GRADER_TEMPERATURE=1 (should be 0!)',
                     fontsize=14, fontweight='bold', color='red')
        ax7.set_xticks(x_pos)
        ax7.set_xticklabels([f'#{i}' for i in range(len(scores))], fontsize=10)
        ax7.set_ylim(0, 1.1)
        ax7.legend(fontsize=11, loc='upper right')
        ax7.grid(axis='y', alpha=0.4)

        for bar, val in zip(bars, scores):
            ax7.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.03,
                    f'{val:.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # ==================== PANEL 8: Key Findings Summary ====================
    ax8 = fig.add_subplot(gs[5, :])
    ax8.axis('off')

    findings_text = """
🔬 KEY RESEARCH FINDINGS

1. GRADER RELIABILITY ISSUE (CRITICAL)
   • Temperature=1 in config causes non-deterministic grading
   • Same answer receives wildly different scores (range: 0.33-1.0 for Assignment 5)
   • Recommendation: Set GRADER_TEMPERATURE=0 for reproducible results

2. ASSIGNMENT DIFFICULTY PATTERNS
   • Assignments 4, 6, 7: Near-zero success rates (avg < 0.01) - too hard or poorly specified
   • Assignment 1: Highest success rate (avg = 0.586) - appropriate difficulty
   • Assignment 5: Most variable grading (std = 0.304) - see temperature issue above

3. MODEL PERFORMANCE RANKING
   • Best: Gemini 2.5 Pro (0.281 ± 0.356)
   • Mid: Grok-4 (0.163 ± 0.257), Claude Opus 4.1 (0.138 ± 0.237)
   • Lowest: Claude Sonnet 4.5 (0.130 ± 0.232)
   • Note: High variance suggests inconsistent question difficulty or grading issues

4. SCORE DISTRIBUTION ANOMALY
   • 52% of all grades are ZERO - assignments may be too difficult
   • Only 7% perfect scores, 40% partial credit
   • Bimodal distribution suggests "all or nothing" grading pattern

5. TRUNCATION ISSUES DETECTED
   • Some model responses are cut off mid-answer (Assignment 5 example found)
   • Causes incomplete grading (3 questions instead of 6)
   • Check max_tokens configuration for answering models

6. QUESTION-LEVEL INSIGHTS
   • Question "1f" impossible (0% success rate) - may be mislabeled or missing ground truth
   • Questions "d", "e" consistently difficult across assignments (13-21% success)
   • Question "3a" perfect (100% success) - possible ground truth matching issue

RECOMMENDATIONS FOR BENCHMARK IMPROVEMENT:
✓ Set GRADER_TEMPERATURE=0 immediately
✓ Review assignments 4, 6, 7 for clarity/difficulty
✓ Increase max_tokens for model responses to prevent truncation
✓ Audit ground truth answers for questions with 0% or 100% success
✓ Consider using ensemble grading (3 graders, majority vote) to reduce variance
✓ Add answer length validation before grading
    """

    ax8.text(0.05, 0.95, findings_text, transform=ax8.transAxes,
            fontsize=11, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.savefig('analysis/graphs/master_findings_report.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: analysis/graphs/master_findings_report.png")
    plt.close()

def main():
    print("\n" + "="*70)
    print("GENERATING COMPREHENSIVE FINDINGS REPORT")
    print("="*70 + "\n")

    df = load_grades()
    create_master_findings_visualization(df)

    print("\n" + "="*70)
    print("✅ MASTER FINDINGS REPORT COMPLETE")
    print("="*70)
    print("\nView the comprehensive visualization:")
    print("  → analysis/graphs/master_findings_report.png")
    print("\nThis single image contains all key findings from the analysis.")
    print()

if __name__ == "__main__":
    main()
