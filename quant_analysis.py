import pandas as pd
import numpy as np
import sys
import os
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import textwrap
import re

# Set style for publication-ready figures
plt.style.use('seaborn-v0_8-paper')
sns.set_palette("colorblind")

def generate_markdown_report(combined_data_df, question_text_row, output_file='output.md'):
    """Generate a markdown report with sentences describing results for each question"""
    lines = []

    total = len(combined_data_df)

    # ── Q9 ──────────────────────────────────────────────────────────────────
    if 'Q9' in combined_data_df.columns:
        lines.append('# Q9')
        counts = combined_data_df['Q9'].value_counts(dropna=True)
        parts = []
        for val, count in counts.items():
            pct = count / total * 100
            parts.append(f'{pct:.2f}% of participants use {val.lower()}')
        lines.append(', '.join(parts) + '.')
        lines.append('')

    # ── Q10 ─────────────────────────────────────────────────────────────────
    if 'Q10' in combined_data_df.columns:
        lines.append('# Q10')
        counts = combined_data_df['Q10'].value_counts(dropna=True)
        parts = []
        for val, count in counts.items():
            pct = count / total * 100
            parts.append(f'{pct:.2f}% of participants use {val}')
        lines.append(', '.join(parts) + '.')
        lines.append('')

    # ── Q12 ─────────────────────────────────────────────────────────────────
    q12_cols = [col for col in combined_data_df.columns if col.startswith('Q12_')]
    if q12_cols:
        lines.append('# Q12')
        freq_order = ['Always', 'Often', 'Sometimes', 'Rarely', 'Never']

        # Per-app sentence (existing logic)
        for col in q12_cols:
            app_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            counts = combined_data_df[col].value_counts(dropna=True)
            col_total = counts.sum()
            parts = []
            for val in freq_order:
                if val in counts:
                    pct = counts[val] / col_total * 100
                    parts.append(f'{pct:.2f}% said {val.lower()}')
            lines.append(f'For {app_name}, ' + ', '.join(parts) + '.')

        # NEW: Per-participant app usage count stats
        # Count how many apps each participant uses (anything other than "Never" counts)
        app_usage_counts = combined_data_df[q12_cols].apply(
            lambda row: sum(1 for val in row if pd.notna(val) and str(val).strip() != 'Never' and str(val).strip() != ''),
            axis=1
        )

        mean_apps = app_usage_counts.mean()
        std_apps = app_usage_counts.std()
        max_apps = app_usage_counts.max()
        min_apps = app_usage_counts.min()
        max_tie_count = (app_usage_counts == max_apps).sum()
        min_tie_count = (app_usage_counts == min_apps).sum()

        lines.append(
            f'On average, participants use {mean_apps:.2f} apps (SD = {std_apps:.2f}). '
            f'The participant(s) who use the most apps use {max_apps} '
            f'({max_tie_count} participant{"s" if max_tie_count > 1 else ""} tied for this). '
            f'The participant(s) who use the fewest apps use {min_apps} '
            f'({min_tie_count} participant{"s" if min_tie_count > 1 else ""} tied for this).'
        )
        lines.append('')


    # ── Q13 ─────────────────────────────────────────────────────────────────
    if 'Q13' in combined_data_df.columns:
        lines.append('# Q13')
        counts = combined_data_df['Q13'].value_counts(dropna=True)
        parts = []
        for val, count in counts.items():
            pct = count / total * 100
            parts.append(f'{pct:.2f}% said {val.lower()}')
        lines.append(', '.join(parts) + ' when asked if they use additional apps.')
        lines.append('')

    # ── Q14 ─────────────────────────────────────────────────────────────────
    if 'Q14' in combined_data_df.columns:
        lines.append('# Q14')
        apps_raw = combined_data_df['Q14'].dropna()
        apps_raw = apps_raw[apps_raw.astype(str).str.strip() != '']
        if len(apps_raw) > 0:
            app_counts = apps_raw.str.strip().value_counts()
            app_parts = []
            for app, cnt in app_counts.items():
                if cnt > 1:
                    app_parts.append(f'{app} ({cnt} participants)')
                else:
                    app_parts.append(app)
            lines.append('The additional apps participants listed were: ' + ', '.join(app_parts) + '.')
        else:
            lines.append('No additional apps were provided.')
        lines.append('')

    # ── Q15 ─────────────────────────────────────────────────────────────────
    if 'Q15' in combined_data_df.columns:
        lines.append('# Q15')
        counts = {}
        q15_total = 0
        for _, row in combined_data_df['Q15'].items():
            if pd.notna(row) and str(row).strip():
                q15_total += 1
                for sel in [s.strip() for s in str(row).split(',')]:
                    if sel:
                        counts[sel] = counts.get(sel, 0) + 1
        for permission, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            pct = cnt / q15_total * 100
            lines.append(f'{pct:.2f}% of participants selected {permission} as a data permission they are aware of.')
        lines.append('')

    # ── Q16 ─────────────────────────────────────────────────────────────────
    q16_cols = [col for col in combined_data_df.columns if col.startswith('Q16_')]
    if q16_cols:
        lines.append('# Q16')
        ranks = {}
        for col in q16_cols:
            item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            item_name = clean_text(item_name)
            numeric_col = pd.to_numeric(combined_data_df[col], errors='coerce')
            ranks[item_name] = numeric_col.mean()
        for item, mean_rank in sorted(ranks.items(), key=lambda x: x[1]):
            lines.append(f'{item} had a mean rank of {mean_rank:.2f}.')
        lines.append('')

    # ── Q17 ─────────────────────────────────────────────────────────────────
    q17_cols = [col for col in combined_data_df.columns if col.startswith('Q17_')]
    if q17_cols:
        lines.append('# Q17')
        comfort_order = ['Extremely uncomfortable', 'Somewhat uncomfortable',
                         'Neither comfortable nor uncomfortable',
                         'Somewhat comfortable', 'Extremely comfortable']
        for col in q17_cols:
            item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            item_name = clean_text(item_name)
            counts = combined_data_df[col].value_counts(dropna=True)
            col_total = counts.sum()
            parts = []
            for val in comfort_order:
                if val in counts:
                    pct = counts[val] / col_total * 100
                    parts.append(f'{pct:.2f}% said {val.lower()}')
            lines.append(f'For {item_name}, ' + ', '.join(parts) + '.')
        lines.append('')

    # ── Q18 ─────────────────────────────────────────────────────────────────
    for scenario_num in ['1', '2', '3']:
        q18_cols = [col for col in combined_data_df.columns if col.startswith(f'Q18#{scenario_num}_')]
        if q18_cols:
            lines.append(f'# Q18#{scenario_num}')
            response_order = ['More uncomfortable', 'Equally uncomfortable', 'Less uncomfortable']
            for col in q18_cols:
                item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
                item_name = clean_text(item_name)
                counts = combined_data_df[col].value_counts(dropna=True)
                col_total = counts.sum()
                parts = []
                for val in response_order:
                    if val in counts:
                        pct = counts[val] / col_total * 100
                        parts.append(f'{pct:.2f}% said {val.lower()}')
                lines.append(f'For {item_name}, ' + ', '.join(parts) + '.')
            lines.append('')

    # ── Q19 ─────────────────────────────────────────────────────────────────
    q19_cols = [col for col in combined_data_df.columns if col.startswith('Q19#1')]
    if q19_cols:
        lines.append('# Q19')
        filtered_df = combined_data_df[combined_data_df['ResponseId'] != 'R_37fm1j8qZ5AzBmV']
        q19_total = len(filtered_df)
        comfort_order = ['Extremely uncomfortable', 'Somewhat uncomfortable',
                         'Neither comfortable nor uncomfortable',
                         'Somewhat comfortable', 'Extremely comfortable']
        for col in q19_cols:
            item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            counts = filtered_df[col].value_counts(dropna=True)
            col_total = counts.sum()
            parts = []
            for val in comfort_order:
                if val in counts:
                    pct = counts[val] / col_total * 100
                    parts.append(f'{pct:.2f}% said {val.lower()}')
            lines.append(f'For {item_name}, ' + ', '.join(parts) + '.')
        lines.append('')

    # ── Q20 ─────────────────────────────────────────────────────────────────
    q20_cols = [col for col in combined_data_df.columns if col.startswith('Q20_')]
    if q20_cols:
        lines.append('# Q20')
        response_order = ['More uncomfortable', 'Equally uncomfortable', 'Less uncomfortable']
        for col in q20_cols:
            item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            counts = combined_data_df[col].value_counts(dropna=True)
            col_total = counts.sum()
            parts = []
            for val in response_order:
                if val in counts:
                    pct = counts[val] / col_total * 100
                    parts.append(f'{pct:.2f}% said {val.lower()}')
            lines.append(f'For {item_name}, ' + ', '.join(parts) + '.')
        lines.append('')

    # ── Q21 ─────────────────────────────────────────────────────────────────
    q21_cols = [col for col in combined_data_df.columns if col.startswith('Q21_')]
    if q21_cols:
        lines.append('# Q21')
        response_order = ['Yes', 'Maybe', 'No']
        for col in q21_cols:
            app_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            counts = combined_data_df[col].value_counts(dropna=True)
            col_total = counts.sum()
            parts = []
            for val in response_order:
                if val in counts:
                    pct = counts[val] / col_total * 100
                    parts.append(f'{pct:.2f}% said {val.lower()}')
            lines.append(f'For {app_name}, ' + ', '.join(parts) + '.')
        lines.append('')

    # ── Q24 ─────────────────────────────────────────────────────────────────
    if 'Q24' in combined_data_df.columns:
        lines.append('# Q24')
        counts = {}
        q24_total = 0
        for _, row in combined_data_df['Q24'].items():
            if pd.notna(row) and str(row).strip():
                q24_total += 1
                for sel in [s.strip() for s in str(row).split(',')]:
                    if sel:
                        counts[sel] = counts.get(sel, 0) + 1
        for area, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            pct = cnt / q24_total * 100
            lines.append(f'{pct:.2f}% of participants selected {area} as an area of impact.')
        lines.append('')

    # ── Q27 ─────────────────────────────────────────────────────────────────
    if 'Q27' in combined_data_df.columns:
        lines.append('# Q27')
        counts = combined_data_df['Q27'].value_counts(dropna=True)
        parts = []
        for val, count in counts.items():
            pct = count / total * 100
            parts.append(f'{pct:.2f}% said {val.lower()}')
        lines.append(', '.join(parts) + ' when asked if they receive security/privacy guidelines.')
        lines.append('')

    # ── Q30 ─────────────────────────────────────────────────────────────────
    if 'Q30' in combined_data_df.columns:
        lines.append('# Q30')
        extent_order = ['Entirely', 'Mostly', 'Somewhat', 'A little', 'Not at all', 'Prefer not to say']
        counts = combined_data_df['Q30'].value_counts(dropna=True)
        col_total = counts.sum()
        for val in extent_order:
            if val in counts:
                pct = counts[val] / col_total * 100
                lines.append(f'{pct:.2f}% said {val.lower()} when asked to what extent they follow guidelines.')
        lines.append('')

    # ── Q31 ─────────────────────────────────────────────────────────────────
    if 'Q31' in combined_data_df.columns:
        lines.append('# Q31')
        extent_order = ['Entirely', 'Mostly', 'Somewhat', 'A little', 'Not at all']
        counts = combined_data_df['Q31'].value_counts(dropna=True)
        col_total = counts.sum()
        for val in extent_order:
            if val in counts:
                pct = counts[val] / col_total * 100
                lines.append(f'{pct:.2f}% said {val.lower()} when asked if privacy practices and guidelines reduce risks.')
        lines.append('')

    # ── Q32 ─────────────────────────────────────────────────────────────────
    if 'Q32' in combined_data_df.columns:
        lines.append('# Q32')
        extent_order = ['Entirely', 'Mostly', 'Somewhat', 'A little', 'Not at all']
        counts = combined_data_df['Q32'].value_counts(dropna=True)
        col_total = counts.sum()
        for val in extent_order:
            if val in counts:
                pct = counts[val] / col_total * 100
                lines.append(f'{pct:.2f}% said {val.lower()} when asked if privacy practices alone reduce risks.')
        lines.append('')

    # ── Q33 ─────────────────────────────────────────────────────────────────
    q33_cols = [col for col in combined_data_df.columns if col.startswith('Q33_')]
    if q33_cols:
        lines.append('# Q33')
        effectiveness_order = ['Extremely effective', 'Very effective', 'Moderately effective',
                                'Slightly effective', 'Not effective at all']
        for col in q33_cols:
            item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            counts = combined_data_df[col].value_counts(dropna=True)
            col_total = counts.sum()
            parts = []
            for val in effectiveness_order:
                if val in counts:
                    pct = counts[val] / col_total * 100
                    parts.append(f'{pct:.2f}% said {val.lower()}')
            lines.append(f'For {item_name}, ' + ', '.join(parts) + '.')
        lines.append('')

    # ── Q34 ─────────────────────────────────────────────────────────────────
    q34_cols = [col for col in combined_data_df.columns if col.startswith('Q34_')]
    if q34_cols:
        lines.append('# Q34')
        likelihood_order = ['Extremely likely', 'Somewhat likely', 'Neither likely nor unlikely',
                             'Somewhat unlikely', 'Extremely unlikely']
        for col in q34_cols:
            item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            counts = combined_data_df[col].value_counts(dropna=True)
            col_total = counts.sum()
            parts = []
            for val in likelihood_order:
                if val in counts:
                    pct = counts[val] / col_total * 100
                    parts.append(f'{pct:.2f}% said {val.lower()}')
            lines.append(f'For {item_name}, ' + ', '.join(parts) + '.')
        lines.append('')

    # ── Q35 ─────────────────────────────────────────────────────────────────
    if 'Q35' in combined_data_df.columns:
        lines.append('# Q35')
        counts = {}
        q35_total = 0
        for _, row in combined_data_df['Q35'].items():
            if pd.notna(row) and str(row).strip():
                q35_total += 1
                for sel in [s.strip() for s in str(row).split(',')]:
                    if sel:
                        counts[sel] = counts.get(sel, 0) + 1
        for status, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            pct = cnt / q35_total * 100
            lines.append(f'{pct:.2f}% of participants identified as {status}.')
        lines.append('')

    # ── Q36 ─────────────────────────────────────────────────────────────────
    if 'Q36' in combined_data_df.columns:
        lines.append('# Q36')
        counts = combined_data_df['Q36'].value_counts(dropna=True)
        for val, count in counts.items():
            pct = count / total * 100
            lines.append(f'{pct:.2f}% of participants are in the {val}.')
        lines.append('')

    # ── Q37 ─────────────────────────────────────────────────────────────────
    if 'Q37' in combined_data_df.columns:
        lines.append('# Q37')
        counts = combined_data_df['Q37'].value_counts(dropna=True)
        for val, count in counts.items():
            pct = count / total * 100
            lines.append(f'{pct:.2f}% of participants identified as {val.lower()}.')
        lines.append('')

    # ── Q38 ─────────────────────────────────────────────────────────────────
    if 'Q38' in combined_data_df.columns:
        lines.append('# Q38')
        counts = combined_data_df['Q38'].value_counts(dropna=True)
        for val, count in counts.items():
            pct = count / total * 100
            lines.append(f'{pct:.2f}% of participants identified as {val}.')
        lines.append('')

    # ── Q39 ─────────────────────────────────────────────────────────────────
    if 'Q39' in combined_data_df.columns:
        lines.append('# Q39')
        counts = combined_data_df['Q39'].value_counts(dropna=True)
        for val, count in counts.items():
            pct = count / total * 100
            lines.append(f'{pct:.2f}% of participants are in the {val} age range.')
        lines.append('')

    # Write to file
    with open(output_file, 'w') as f:
        f.write('\n'.join(lines))

    print(f"\n✓ Markdown report written to {output_file}")


def convert_to_numeric(df, column, mapping):
    """Convert text responses to numeric values based on mapping"""
    return df[column].map(mapping)

def validate_csv_structure(df, reference_columns, file_name):
    """Validate that CSV has the same column structure as reference"""
    if list(df.columns) != list(reference_columns):
        missing_cols = set(reference_columns) - set(df.columns)
        extra_cols = set(df.columns) - set(reference_columns)
        
        error_msg = f"\nERROR: Column structure mismatch in file '{file_name}'\n"
        if missing_cols:
            error_msg += f"  Missing columns: {missing_cols}\n"
        if extra_cols:
            error_msg += f"  Extra columns: {extra_cols}\n"
        error_msg += "\nAll CSV files must have the same column structure."
        
        print(error_msg)
        sys.exit(1)

def wrap_text(text, width=40):
    """Wrap long text for better display in charts"""
    return '\n'.join(textwrap.wrap(text, width=width))

def clean_text(text):
    """Remove HTML tags and clean text"""
    # Remove <abbr> tags and their content, keeping just "Device Identifiers"
    if '<abbr' in text and 'Device Identifiers' in text:
        return 'Device Identifiers'
    # Remove any other HTML tags
    clean = re.sub('<.*?>', '', text)
    return clean

def create_bar_chart_with_values(data, title, filename, xlabel='Response', ylabel='Count', color='#4472C4', custom_order=None, fixed_ylim=None):
    """Create a bar chart with counts, percentages, and fractions displayed - all bars blue with extra padding"""
    fig, ax = plt.subplots(figsize=(10, 7))  # Increased height
    
    # Apply custom order if provided
    if custom_order:
        data = data.reindex(custom_order, fill_value=0)
    
    total = data.sum()
    
    # All bars in blue
    bars = ax.bar(range(len(data)), data.values, color=color, edgecolor='black', linewidth=0.5)
    
    # Add value labels on bars
    for i, (bar, count) in enumerate(zip(bars, data.values)):
        height = bar.get_height()
        percentage = (count / total * 100) if total > 0 else 0
        label = f'{int(count)}\n({percentage:.1f}%)\n{int(count)}/{int(total)}'
        ax.text(bar.get_x() + bar.get_width()/2., height,
                label, ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Add extra space at top to prevent overlap or use fixed ylim
    if fixed_ylim:
        ax.set_ylim(0, fixed_ylim)
    else:
        ax.set_ylim(0, max(data.values) * 1.25)
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_xticks(range(len(data)))
    ax.set_xticklabels(data.index, rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

def create_bar_chart_with_text_overlay(data, title, filename, text_list=None, xlabel='Response', ylabel='Count', color='#4472C4'):
    """Create a bar chart with optional text overlay above specific bar - all bars blue"""
    fig, ax = plt.subplots(figsize=(10, 11))  # Increased height even more for apps list
    
    total = data.sum()
    
    # All bars in blue
    bars = ax.bar(range(len(data)), data.values, color=color, edgecolor='black', linewidth=0.5)
    
    # Add value labels on bars
    for i, (bar, count, label) in enumerate(zip(bars, data.values, data.index)):
        height = bar.get_height()
        percentage = (count / total * 100) if total > 0 else 0
        value_label = f'{int(count)}\n({percentage:.1f}%)\n{int(count)}/{int(total)}'
        
        # Add text list above "Yes" bar if provided - positioned at y=35-55 (center at 45)
        if text_list and label == 'Yes' and len(text_list) > 0:
            # Place count ABOVE the bar
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    value_label, ha='center', va='bottom', fontsize=9, fontweight='bold')
            # Place the additional apps list at y=45 (center of 35-55 range)
            apps_text = '\n'.join(text_list)
            ax.text(bar.get_x() + bar.get_width()/2., 45,
                    apps_text, ha='center', va='center', fontsize=8, 
                    style='italic', color='darkblue')
        else:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    value_label, ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Fixed y-limit at 100 for Q13
    ax.set_ylim(0, 100)
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_xticks(range(len(data)))
    ax.set_xticklabels(data.index, rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

def create_multi_select_chart(data, title, filename, xlabel='Response Options', ylabel='Count', custom_order=None):
    """Create a bar chart for multi-select questions - properly handle multi-select data"""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Count how many times each option appears
    counts = {}
    total_responses = 0
    
    for idx, row in data.items():
        if pd.notna(row) and str(row).strip():
            total_responses += 1
            # Split by comma if multiple selections
            selections = [s.strip() for s in str(row).split(',')]
            for selection in selections:
                if selection:
                    counts[selection] = counts.get(selection, 0) + 1
    
    if not counts:
        print(f"  ⚠ No data for {title}")
        return
    
    # Sort by count or use custom order
    if custom_order:
        sorted_counts = pd.Series({k: counts.get(k, 0) for k in custom_order})
    else:
        sorted_counts = pd.Series(counts).sort_values(ascending=False)
    
    # Create bar chart
    bars = ax.bar(range(len(sorted_counts)), sorted_counts.values, color='#4472C4', 
                   edgecolor='black', linewidth=0.5)
    
    # Add value labels
    for i, (bar, count) in enumerate(zip(bars, sorted_counts.values)):
        height = bar.get_height()
        percentage = (count / total_responses * 100) if total_responses > 0 else 0
        label = f'{int(count)}\n({percentage:.1f}%)\n{int(count)}/{total_responses}'
        ax.text(bar.get_x() + bar.get_width()/2., height,
                label, ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Add extra space at top
    if len(sorted_counts) > 0 and max(sorted_counts.values) > 0:
        ax.set_ylim(0, max(sorted_counts.values) * 1.25)
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_xticks(range(len(sorted_counts)))
    ax.set_xticklabels([wrap_text(label, 20) for label in sorted_counts.index], 
                        rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

def create_stacked_bar_chart(data, title, filename, categories, sort_by_green=False):
    """Create a stacked bar chart for Likert-scale data"""
    if sort_by_green:
        data_sorted = data.sort_values(by=data.columns[0], ascending=True)
    else:
        data_sorted = data.sort_values(by=list(data.columns), ascending=[True] * len(data.columns))
    
    fig, ax = plt.subplots(figsize=(12, max(6, len(data_sorted) * 0.4)))
    
    if sort_by_green:
        colors = ['#1a9850', '#91cf60', '#fee090', '#fc8d59', '#d73027']
    else:
        colors = ['#d73027', '#fc8d59', '#fee090', '#91cf60', '#1a9850']
    
    data_sorted.plot(kind='barh', stacked=True, ax=ax,
                     color=colors, edgecolor='black', linewidth=0.3)
    
    # Label every segment with its percentage, placed immediately above the segment
    for bar_idx, (row_label, row) in enumerate(data_sorted.iterrows()):
        cumulative = 0
        for col_name, val in row.items():
            if val > 0:
                seg_center = cumulative + val / 2
                font_size = max(4, min(9, val * 0.18))  # auto-scale: wider = bigger, shrinks for thin segments
                label = f'{val:.1f}%'
                ax.text(seg_center, bar_idx,
                        label,
                        ha='center', va='center',  # CHANGED: centered inside the segment
                        fontsize=font_size, fontweight='bold')
            cumulative += val
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Percentage (%)', fontsize=12)
    ax.legend(categories, bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
    ax.set_xlim(0, 100)
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

def create_stacked_bar_chart_3colors(data, title, filename, categories):
    """Create a stacked bar chart for 3-color Likert-scale data (More/Equally/Less uncomfortable)"""
    data_sorted = data.sort_values(by=list(data.columns), ascending=[True, True, True])
    
    fig, ax = plt.subplots(figsize=(12, max(6, len(data_sorted) * 0.4)))
    data_sorted.plot(kind='barh', stacked=True, ax=ax,
                     color=['#d73027', '#fee090', '#1a9850'],
                     edgecolor='black', linewidth=0.3)
    
    # Label every segment with its percentage, placed immediately above the segment
    for bar_idx, (row_label, row) in enumerate(data_sorted.iterrows()):
        cumulative = 0
        for col_name, val in row.items():
            if val > 0:
                seg_center = cumulative + val / 2
                font_size = max(4, min(9, val * 0.18))  # auto-scale: wider = bigger, shrinks for thin segments
                label = f'{val:.1f}%'
                ax.text(seg_center, bar_idx,
                        label,
                        ha='center', va='center',  # CHANGED: centered inside the segment
                        fontsize=font_size, fontweight='bold')
            cumulative += val
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Percentage (%)', fontsize=12)
    ax.legend(categories, bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
    ax.set_xlim(0, 100)
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

def create_heatmap(data, title, filename, xlabel='', ylabel='', cmap='RdYlGn_r', reverse_sort=False, vmin=1, vmax=5, custom_labels=None):
    """Create a heatmap for matrix data"""
    # Sort by mean value
    if reverse_sort:
        data_sorted = data.sort_values(by='Mean', ascending=False)
    else:
        data_sorted = data.sort_values(by='Mean', ascending=True)
    
    fig, ax = plt.subplots(figsize=(10, max(8, len(data_sorted) * 0.3)))
    center_val = (vmax + vmin) / 2
    
    # Create heatmap
    sns.heatmap(data_sorted, annot=True, fmt='.2f', cmap=cmap, center=center_val, 
                vmin=vmin, vmax=vmax, cbar_kws={'label': 'Mean Score'},
                linewidths=0.5, ax=ax)
    
    # Custom colorbar labels if provided
    if custom_labels:
        cbar = ax.collections[0].colorbar
        cbar.set_ticks([vmin, center_val, vmax])
        cbar.set_ticklabels(custom_labels)
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

def create_horizontal_bar_chart(data, title, filename, xlabel='Mean Rank'):
    """Create horizontal bar chart for rankings - lower rank = more uncomfortable = RED and at TOP"""
    # Sort by value (LOWEST to HIGHEST) so most uncomfortable (rank 1) at top
    data_sorted = data.sort_values(ascending=True)
    
    fig, ax = plt.subplots(figsize=(12, max(6, len(data_sorted) * 0.4)))
    
    # Color mapping: lower rank (1) = RED at TOP, higher rank (22) = GREEN at BOTTOM
    norm_values = (data_sorted - data_sorted.min()) / (data_sorted.max() - data_sorted.min())
    colors = plt.cm.RdYlGn(norm_values)  # Low values (rank 1) = red, high values (rank 22) = green
    
    data_sorted.plot(kind='barh', ax=ax, color=colors, edgecolor='black', linewidth=0.5)
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.legend().set_visible(False)
    
    # INVERT y-axis so TOP bar is RED (most uncomfortable)
    ax.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

def generate_visualizations(combined_data_df, question_text_row, output_dir):
    """Generate all visualizations"""    
    vis_count = 0
    
    # Q9: Device type
    if 'Q9' in combined_data_df.columns:
        data = combined_data_df['Q9'].value_counts()
        create_bar_chart_with_values(data, 'Q9: Device Type', 
                                     f'{output_dir}/q9_device_type.png',
                                     xlabel='Device Type', ylabel='Number of Responses')
        vis_count += 1
    
    # Q10: OS type
    if 'Q10' in combined_data_df.columns:
        data = combined_data_df['Q10'].value_counts().sort_index()
        create_bar_chart_with_values(data, 'Q10: OS Type', 
                                     f'{output_dir}/q10_os_type.png',
                                     xlabel='OS Type', ylabel='Number of Responses')
        vis_count += 1
    
    # Q12: App usage frequency
    q12_cols = [col for col in combined_data_df.columns if col.startswith('Q12_')]
    if q12_cols:
        freq_mapping = {'Always': 5, 'Often': 4, 'Sometimes': 3, 'Rarely': 2, 'Never': 1}
        q12_data = []
        q12_labels = []
        for col in q12_cols:
            numeric_col = convert_to_numeric(combined_data_df, col, freq_mapping)
            mean_val = numeric_col.mean()
            q12_data.append(mean_val)
            app_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            q12_labels.append(wrap_text(app_name, 30))
        
        df_heatmap = pd.DataFrame({'Mean': q12_data}, index=q12_labels)
        create_heatmap(df_heatmap, 'Q12: App Usage Frequency', 
                      f'{output_dir}/q12_app_usage_frequency.png',
                      xlabel='', ylabel='Application', cmap='RdYlGn', reverse_sort=True)
        vis_count += 1
    
    # Q13: Additional apps with free response text - FIXED YLIM 100, apps at y=45 (35-55)
    if 'Q13' in combined_data_df.columns:
        data = combined_data_df['Q13'].value_counts().sort_index()
        
        # Get free response apps from Q14 column
        additional_apps = []
        if 'Q14' in combined_data_df.columns:
            apps = combined_data_df['Q14'].dropna().unique()
            additional_apps = [str(app).strip() for app in apps if str(app).lower() not in ['nan', '', 'none']][:15]
        
        create_bar_chart_with_text_overlay(data, 'Q13: Additional Apps Used', 
                                          f'{output_dir}/q13_additional_apps.png',
                                          text_list=additional_apps,
                                          xlabel='Response', ylabel='Number of Responses')
        vis_count += 1
    
    # Q15: Multi-select data permissions
    if 'Q15' in combined_data_df.columns:
        create_multi_select_chart(combined_data_df['Q15'], 'Q15: Data Permissions Awareness', 
                                 f'{output_dir}/q15_data_permissions.png',
                                 xlabel='Permission Type', ylabel='Number of Selections')
        vis_count += 1
    
    # Q16: Rankings
    q16_cols = [col for col in combined_data_df.columns if col.startswith('Q16_')]
    if q16_cols:
        q16_data = {}
        for col in q16_cols:
            numeric_col = pd.to_numeric(combined_data_df[col], errors='coerce')
            mean_rank = numeric_col.mean()
            item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            item_name = clean_text(item_name)
            wrapped_name = wrap_text(item_name, 35)
            q16_data[wrapped_name] = mean_rank
        
        df_ranks = pd.Series(q16_data)
        
        create_horizontal_bar_chart(df_ranks, 'Q16: Data Sensitivity Rankings', 
                                    f'{output_dir}/q16_data_sensitivity_rankings.png',
                                    xlabel='Mean Rank (Lower=More Uncomfortable)')
        vis_count += 1
    
    # Q17: Comfort levels
    q17_cols = [col for col in combined_data_df.columns if col.startswith('Q17_')]
    if q17_cols:
        q17_data = []
        q17_labels = []
        for col in q17_cols:
            counts = combined_data_df[col].value_counts()
            total = counts.sum()
            percentages = (counts / total * 100).reindex([
                'Extremely uncomfortable', 'Somewhat uncomfortable',
                'Neither comfortable nor uncomfortable',
                'Somewhat comfortable', 'Extremely comfortable'
            ], fill_value=0)
            q17_data.append(percentages.values)
            item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            item_name = clean_text(item_name)
            q17_labels.append(wrap_text(item_name, 30))
        
        df_stacked = pd.DataFrame(q17_data, index=q17_labels,
                                  columns=['Extremely\nuncomfortable', 'Somewhat\nuncomfortable',
                                          'Neither', 'Somewhat\ncomfortable', 'Extremely\ncomfortable'])
        create_stacked_bar_chart(df_stacked, 'Q17: Comfort with Data Collection', 
                                f'{output_dir}/q17_comfort_with_data_collection.png',
                                ['Extremely uncomfortable', 'Somewhat uncomfortable',
                                 'Neither', 'Somewhat comfortable', 'Extremely comfortable'],
                                sort_by_green=False)
        vis_count += 1
    
    # Q18: Scenarios
    for scenario_num in ['1', '2', '3']:
        q18_cols = [col for col in combined_data_df.columns if col.startswith(f'Q18#{scenario_num}_')]
        if q18_cols:
            q18_data = []
            q18_labels = []
            for col in q18_cols:
                counts = combined_data_df[col].value_counts()
                total = counts.sum()
                percentages = (counts / total * 100).reindex([
                    'More uncomfortable', 'Equally uncomfortable', 'Less uncomfortable'
                ], fill_value=0)
                q18_data.append(percentages.values)
                item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
                item_name = clean_text(item_name)
                q18_labels.append(wrap_text(item_name, 30))
            
            scenario_names = {
                '1': 'military_app',
                '2': 'foreign_party',
                '3': 'third_party'
            }
            df_stacked = pd.DataFrame(q18_data, index=q18_labels,
                                      columns=['More\nuncomfortable', 'Equally\nuncomfortable', 'Less\nuncomfortable'])
            create_stacked_bar_chart_3colors(df_stacked, f'Q18 {scenario_names[scenario_num]} Discomfort', 
                                    f'{output_dir}/q18_{scenario_names[scenario_num]}_discomfort.png',
                                    ['More uncomfortable', 'Equally uncomfortable', 'Less uncomfortable'])
            vis_count += 1
    
    # Q19#1: Country comfort - EXCLUDE ResponseId R_37fm1j8qZ5AzBmV
    q19_cols = [col for col in combined_data_df.columns if col.startswith('Q19#1')]
    if q19_cols:
        filtered_df = combined_data_df[combined_data_df['ResponseId'] != 'R_37fm1j8qZ5AzBmV'].copy()
        
        q19_data = []
        q19_labels = []
        for col in q19_cols:
            counts = filtered_df[col].value_counts()
            total = counts.sum()
            percentages = (counts / total * 100).reindex([
                'Extremely uncomfortable', 'Somewhat uncomfortable',
                'Neither comfortable nor uncomfortable',
                'Somewhat comfortable', 'Extremely comfortable'
            ], fill_value=0)
            q19_data.append(percentages.values)
            item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            q19_labels.append(item_name)
        
        df_stacked = pd.DataFrame(q19_data, index=q19_labels,
                                  columns=['Extremely\nuncomfortable', 'Somewhat\nuncomfortable',
                                          'Neither', 'Somewhat\ncomfortable', 'Extremely\ncomfortable'])
        create_stacked_bar_chart(df_stacked, 'Q19: Comfort with Foreign Code by Country', 
                                f'{output_dir}/q19_country_comfort.png',
                                ['Extremely uncomfortable', 'Somewhat uncomfortable',
                                 'Neither', 'Somewhat comfortable', 'Extremely comfortable'],
                                sort_by_green=False)
        vis_count += 1
    
    # Q20: Impact of Military Affiliation on Discomfort
    q20_cols = [col for col in combined_data_df.columns if col.startswith('Q20_')]
    if q20_cols:
        q20_data = []
        q20_labels = []
        for col in q20_cols:
            counts = combined_data_df[col].value_counts()
            total = counts.sum()
            percentages = (counts / total * 100).reindex([
                'More uncomfortable', 'Equally uncomfortable', 'Less uncomfortable'
            ], fill_value=0)
            q20_data.append(percentages.values)
            item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            q20_labels.append(item_name)
        
        df_stacked = pd.DataFrame(q20_data, index=q20_labels,
                                  columns=['More\nuncomfortable', 'Equally\nuncomfortable', 'Less\nuncomfortable'])
        create_stacked_bar_chart_3colors(df_stacked, 'Q20: Impact of Military Affiliation on Discomfort', 
                                f'{output_dir}/q20_military_affiliation_impact.png',
                                ['More uncomfortable', 'Equally uncomfortable', 'Less uncomfortable'])
        vis_count += 1
    
    # Q21: Belief about foreign code
    q21_cols = [col for col in combined_data_df.columns if col.startswith('Q21_')]
    if q21_cols:
        belief_mapping = {'Yes': 3, 'Maybe': 2, 'No': 1}
        q21_data = []
        q21_labels = []
        for col in q21_cols:
            numeric_col = convert_to_numeric(combined_data_df, col, belief_mapping)
            mean_val = numeric_col.mean()
            q21_data.append(mean_val)
            app_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            q21_labels.append(wrap_text(app_name, 30))
        
        df_heatmap = pd.DataFrame({'Mean': q21_data}, index=q21_labels)
        create_heatmap(df_heatmap, 'Q21: Belief Apps Contain Foreign Code', 
                      f'{output_dir}/q21_foreign_code_belief.png',
                      xlabel='', ylabel='Application', cmap='RdYlGn_r', reverse_sort=True,
                      vmin=1, vmax=3,
                      custom_labels=["Doesn't contain\nforeign code (1)", 
                                   "Maybe contains\nforeign code (2)", 
                                   "Contains\nforeign code (3)"])
        vis_count += 1
    
    # Q24: Multi-select areas of impact
    if 'Q24' in combined_data_df.columns:
        create_multi_select_chart(combined_data_df['Q24'], 'Q24: Areas of Impact', 
                                 f'{output_dir}/q24_areas_of_impact.png',
                                 xlabel='Impact Area', ylabel='Number of Selections')
        vis_count += 1
    
    # Q27: Receive guidelines
    if 'Q27' in combined_data_df.columns:
        data = combined_data_df['Q27'].value_counts()
        custom_order = ['Yes', 'No']
        create_bar_chart_with_values(data, 'Q27: Receive Security/Privacy Guidelines', 
                                     f'{output_dir}/q27_receive_guidelines.png',
                                     xlabel='Response', ylabel='Number of Responses',
                                     custom_order=custom_order)
        vis_count += 1
    
    # Q30: Extent follow guidelines
    if 'Q30' in combined_data_df.columns:
        data = combined_data_df['Q30'].value_counts().reindex([
            'Entirely', 'Mostly', 'Somewhat', 'A little', 'Not at all', 'Prefer not to say'
        ], fill_value=0)
        create_bar_chart_with_values(data, 'Q30: Extent Follow Guidelines', 
                                     f'{output_dir}/q30_follow_guidelines.png',
                                     xlabel='Extent', ylabel='Number of Responses')
        vis_count += 1
    
    # Q31: Privacy practices + guidelines effectiveness
    if 'Q31' in combined_data_df.columns:
        data = combined_data_df['Q31'].value_counts().reindex([
            'Entirely', 'Mostly', 'Somewhat', 'A little', 'Not at all'
        ], fill_value=0)
        create_bar_chart_with_values(data, 'Q31: Privacy Practices + Guidelines Reduce Risks', 
                                     f'{output_dir}/q31_practices_guidelines_effectiveness.png',
                                     xlabel='Extent', ylabel='Number of Responses')
        vis_count += 1
    
    # Q32: Privacy practices effectiveness
    if 'Q32' in combined_data_df.columns:
        data = combined_data_df['Q32'].value_counts().reindex([
            'Entirely', 'Mostly', 'Somewhat', 'A little', 'Not at all'
        ], fill_value=0)
        create_bar_chart_with_values(data, 'Q32: Privacy Practices Reduce Risks', 
                                     f'{output_dir}/q32_practices_effectiveness.png',
                                     xlabel='Extent', ylabel='Number of Responses')
        vis_count += 1
    
    # Q33: Mitigation effectiveness
    q33_cols = [col for col in combined_data_df.columns if col.startswith('Q33_')]
    if q33_cols:
        q33_data = []
        q33_labels = []
        for col in q33_cols:
            counts = combined_data_df[col].value_counts()
            total = counts.sum()
            percentages = (counts / total * 100).reindex([
                'Extremely effective', 'Very effective', 'Moderately effective',
                'Slightly effective', 'Not effective at all'
            ], fill_value=0)
            q33_data.append(percentages.values)
            item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            q33_labels.append(wrap_text(item_name, 35))
        
        df_stacked = pd.DataFrame(q33_data, index=q33_labels,
                                  columns=['Extremely\neffective', 'Very\neffective', 'Moderately\neffective',
                                          'Slightly\neffective', 'Not effective\nat all'])
        create_stacked_bar_chart(df_stacked, 'Q33: Mitigation Effectiveness', 
                                f'{output_dir}/q33_mitigation_effectiveness.png',
                                ['Extremely effective', 'Very effective', 'Moderately effective',
                                 'Slightly effective', 'Not effective at all'],
                                sort_by_green=True)
        vis_count += 1
    
    # Q34: Adoption likelihood
    q34_cols = [col for col in combined_data_df.columns if col.startswith('Q34_')]
    if q34_cols:
        q34_data = []
        q34_labels = []
        for col in q34_cols:
            counts = combined_data_df[col].value_counts()
            total = counts.sum()
            percentages = (counts / total * 100).reindex([
                'Extremely likely', 'Somewhat likely', 'Neither likely nor unlikely',
                'Somewhat unlikely', 'Extremely unlikely'
            ], fill_value=0)
            q34_data.append(percentages.values)
            item_name = question_text_row[col].split(' - ')[-1] if ' - ' in question_text_row[col] else col
            q34_labels.append(wrap_text(item_name, 35))
        
        df_stacked = pd.DataFrame(q34_data, index=q34_labels,
                                  columns=['Extremely\nlikely', 'Somewhat\nlikely', 'Neither',
                                          'Somewhat\nunlikely', 'Extremely\nunlikely'])
        create_stacked_bar_chart(df_stacked, 'Q34: Adoption Likelihood', 
                                f'{output_dir}/q34_adoption_likelihood.png',
                                ['Extremely likely', 'Somewhat likely', 'Neither likely nor unlikely',
                                 'Somewhat unlikely', 'Extremely unlikely'],
                                sort_by_green=True)
        vis_count += 1
    
    # Q35: Military status
    if 'Q35' in combined_data_df.columns:
        create_multi_select_chart(combined_data_df['Q35'], 'Q35: Military Status', 
                                 f'{output_dir}/q35_military_status.png',
                                 xlabel='Military Status', ylabel='Number of Selections')
        vis_count += 1
    
    # Q36: Branch
    if 'Q36' in combined_data_df.columns:
        data = combined_data_df['Q36'].value_counts().sort_index()
        create_bar_chart_with_values(data, 'Q36: Branch', 
                                     f'{output_dir}/q36_branch.png',
                                     xlabel='Branch', ylabel='Number of Responses')
        vis_count += 1
    
    # Q37: Gender
    if 'Q37' in combined_data_df.columns:
        data = combined_data_df['Q37'].value_counts().reindex([
            'Male', 'Female', 'Prefer not to say'
        ], fill_value=0)
        create_bar_chart_with_values(data, 'Q37: Gender', 
                                     f'{output_dir}/q37_gender.png',
                                     xlabel='Gender', ylabel='Number of Responses')
        vis_count += 1
    
    # Q38: Ethnicity
    if 'Q38' in combined_data_df.columns:
        data = combined_data_df['Q38'].value_counts().reindex([
            'White', 'Black or African American', 'American Indian or Alaska Native',
            'Asian', 'Native Hawaiian or Pacific Islander', 'Other (Please Specify)', 'Prefer not to say'
        ], fill_value=0)
        create_bar_chart_with_values(data, 'Q38: Race/Ethnicity', 
                                     f'{output_dir}/q38_race_ethnicity.png',
                                     xlabel='Race/Ethnicity', ylabel='Number of Responses')
        vis_count += 1
    
    # Q39: Age
    if 'Q39' in combined_data_df.columns:
        data = combined_data_df['Q39'].value_counts().sort_index()
        create_bar_chart_with_values(data, 'Q39: Age', 
                                     f'{output_dir}/q39_age.png',
                                     xlabel='Age Range', ylabel='Number of Responses')
        vis_count += 1
    
    print(f"\nGenerated {vis_count} visuals in '{output_dir}/' folder")

def main():
    # Check for --visualize flag
    create_visualizations = '--visualize' in sys.argv
    if create_visualizations:
        sys.argv.remove('--visualize')
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_responses.py <input_csv_file1> [input_csv_file2] [input_csv_file3] ... [--visualize]")
        print("\nExample:")
        print("  python analyze_responses.py survey_batch1.csv survey_batch2.csv survey_batch3.csv")
        print("  python analyze_responses.py survey_batch1.csv --visualize")
        sys.exit(1)
    
    input_files = sys.argv[1:]
        
    # Read the first CSV file to get question text and column structure
    try:
        first_df = pd.read_csv(input_files[0])
        print(f"Loaded: {input_files[0]} ({len(first_df)} rows)")
    except Exception as e:
        print(f"\nERROR: Could not read file '{input_files[0]}'")
        print(f"Error details: {e}")
        sys.exit(1)
    
    # Row 0 contains the question text
    question_text_row = first_df.iloc[0]
    
    # Store reference columns for validation
    reference_columns = first_df.columns
    
    # Collect all data DataFrames (starting from row 2 in each file)
    all_data_dfs = []
    
    # Add data from first file
    first_data = first_df.iloc[2:].reset_index(drop=True)
    all_data_dfs.append(first_data)
    
    # Read and validate additional CSV files
    for file_name in input_files[1:]:
        try:
            df = pd.read_csv(file_name)
            print(f"Loaded: {file_name} ({len(df)} rows)")
            
            # Validate column structure
            validate_csv_structure(df, reference_columns, file_name)
            
            # Skip metadata rows (rows 0 and 1), extract data starting from row 2
            data_df = df.iloc[2:].reset_index(drop=True)
            all_data_dfs.append(data_df)
            
        except Exception as e:
            print(f"\nERROR: Could not read file '{file_name}'")
            print(f"Error details: {e}")
            sys.exit(1)
    
    # Combine all data into a single DataFrame
    combined_data_df = pd.concat(all_data_dfs, ignore_index=True)
    
    print(f"\nCombined data: {len(combined_data_df)} total responses from {len(input_files)} file(s)")
    
    # Check for duplicate ResponseIds
    if 'ResponseId' in combined_data_df.columns:
        duplicate_ids = combined_data_df['ResponseId'].duplicated().sum()
        if duplicate_ids > 0:
            print(f"\nWARNING: Found {duplicate_ids} duplicate ResponseId(s) in the combined data.")
            print("This may indicate overlapping data between CSV files.")
    
    # Define answer mappings for each question type
    # HIGHER NUMBERS = MORE UNCOMFORTABLE/NEGATIVE (except where noted)
    
    # Q9: Device type
    q9_mapping = {
        'Personal Device': 1,
        'Government/Military-Issued Device': 2,
        'Mix of Both': 3
    }
    
    # Q10: Phone type
    q10_mapping = {
        'Android': 1,
        'iPhone': 2
    }
    
    # Q12: Frequency
    frequency_mapping = {
        'Always': 5,
        'Often': 4,
        'Sometimes': 3,
        'Rarely': 2,
        'Never': 1
    }
    
    # Q13: Yes/No
    yes_no_mapping = {
        'Yes': 1,
        'No': 2
    }
    
    # Q16: Rankings (1-22, already numeric)
    # Q17: Comfort level
    comfort_5_mapping = {
        'Extremely comfortable': 1,
        'Somewhat comfortable': 2,
        'Neither comfortable nor uncomfortable': 3,
        'Somewhat uncomfortable': 4,
        'Extremely uncomfortable': 5
    }
    
    # Q18 (#1, #2, #3)
    more_less_mapping = {
        'Less uncomfortable': 1,
        'Equally uncomfortable': 2,
        'More uncomfortable': 3
    }
    
    # Q19#1: Comfort level
    # Uses comfort_5_mapping
    
    # Q20: More/Equally/Less uncomfortable (for countries)
    # Uses more_less_mapping
    
    # Q21: Belief about foreign code
    yes_maybe_no_mapping = {
        'Yes': 3,
        'Maybe': 2,
        'No': 1
    }
    
    # Q27: Yes/No
    # Uses yes_no_mapping
    
    # Q30-Q32: Extent scales
    extent_mapping = {
        'Entirely': 5,
        'Mostly': 4,
        'Somewhat': 3,
        'A little': 2,
        'Not at all': 1,
        'Prefer not to say': np.nan
    }
    
    # Q33: Effectiveness
    effectiveness_mapping = {
        'Extremely effective': 5,
        'Very effective': 4,
        'Moderately effective': 3,
        'Slightly effective': 2,
        'Not effective at all': 1
    }
    
    # Q34: Likelihood
    likelihood_mapping = {
        'Extremely likely': 5,
        'Somewhat likely': 4,
        'Neither likely nor unlikely': 3,
        'Somewhat unlikely': 2,
        'Extremely unlikely': 1
    }
    
    results = []
    
    # Q9: Device usage
    if 'Q9' in combined_data_df.columns:
        numeric_col = convert_to_numeric(combined_data_df, 'Q9', q9_mapping)
        results.append({
            'Question': f'Q9: {question_text_row["Q9"]}',
            'Description': 'Device usage (1=Personal Device, 2=Government/Military-Issued, 3=Mix of Both)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q10: Phone type
    if 'Q10' in combined_data_df.columns:
        numeric_col = convert_to_numeric(combined_data_df, 'Q10', q10_mapping)
        results.append({
            'Question': f'Q10: {question_text_row["Q10"]}',
            'Description': 'Phone type (1=Android, 2=iPhone)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q12: App usage frequency
    q12_cols = [col for col in combined_data_df.columns if col.startswith('Q12_')]
    for col in q12_cols:
        numeric_col = convert_to_numeric(combined_data_df, col, frequency_mapping)
        results.append({
            'Question': f'{col}: {question_text_row[col]}',
            'Description': f'{col}: App usage frequency (5=Always, 4=Often, 3=Sometimes, 2=Rarely, 1=Never)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q13: Additional apps
    if 'Q13' in combined_data_df.columns:
        numeric_col = convert_to_numeric(combined_data_df, 'Q13', yes_no_mapping)
        results.append({
            'Question': f'Q13: {question_text_row["Q13"]}',
            'Description': 'Additional apps (1=Yes, 2=No)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q15: Multi-select data permissions (skip - not suitable for mean/std)
    
    # Q16: Rankings
    q16_cols = [col for col in combined_data_df.columns if col.startswith('Q16_')]
    for col in q16_cols:
        numeric_col = pd.to_numeric(combined_data_df[col], errors='coerce')
        results.append({
            'Question': f'{col}: {question_text_row[col]}',
            'Description': f'{col}: Ranking (1=most uncomfortable, 22=least uncomfortable)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q17: Comfort with data collection
    q17_cols = [col for col in combined_data_df.columns if col.startswith('Q17_')]
    for col in q17_cols:
        numeric_col = convert_to_numeric(combined_data_df, col, comfort_5_mapping)
        results.append({
            'Question': f'{col}: {question_text_row[col]}',
            'Description': f'{col}: Discomfort level (1=Extremely comfortable, 2=Somewhat comfortable, 3=Neither, 4=Somewhat uncomfortable, 5=Extremely uncomfortable)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q18: Scenarios
    q18_cols = [col for col in combined_data_df.columns if col.startswith('Q18#') and not col.startswith('Q18#4')]
    for col in q18_cols:
        numeric_col = convert_to_numeric(combined_data_df, col, more_less_mapping)
        results.append({
            'Question': f'{col}: {question_text_row[col]}',
            'Description': f'{col}: Discomfort comparison (1=Less uncomfortable, 2=Equally uncomfortable, 3=More uncomfortable)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q19#1: Country comfort - EXCLUDE ResponseId R_37fm1j8qZ5AzBmV
    q19_cols = [col for col in combined_data_df.columns if col.startswith('Q19#1')]
    for col in q19_cols:
        filtered_df = combined_data_df[combined_data_df['ResponseId'] != 'R_37fm1j8qZ5AzBmV']
        numeric_col = convert_to_numeric(filtered_df, col, comfort_5_mapping)
        results.append({
            'Question': f'{col}: {question_text_row[col]}',
            'Description': f'{col}: Discomfort with foreign code (1=Extremely comfortable, 2=Somewhat comfortable, 3=Neither, 4=Somewhat uncomfortable, 5=Extremely uncomfortable) [Excluding ResponseId R_37fm1j8qZ5AzBmV]',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q20: Country comparison
    q20_cols = [col for col in combined_data_df.columns if col.startswith('Q20_')]
    for col in q20_cols:
        numeric_col = convert_to_numeric(combined_data_df, col, more_less_mapping)
        results.append({
            'Question': f'{col}: {question_text_row[col]}',
            'Description': f'{col}: Military affiliation impact (1=Less uncomfortable, 2=Equally uncomfortable, 3=More uncomfortable)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q21: Belief about foreign code in apps
    q21_cols = [col for col in combined_data_df.columns if col.startswith('Q21_')]
    for col in q21_cols:
        numeric_col = convert_to_numeric(combined_data_df, col, yes_maybe_no_mapping)
        results.append({
            'Question': f'{col}: {question_text_row[col]}',
            'Description': f'{col}: Belief app contains foreign code (3=Yes, 2=Maybe, 1=No)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q24: Multi-select areas of impact (skip - not suitable for mean/std)
    
    # Q27: Receive security guidelines
    if 'Q27' in combined_data_df.columns:
        numeric_col = convert_to_numeric(combined_data_df, 'Q27', yes_no_mapping)
        results.append({
            'Question': f'Q27: {question_text_row["Q27"]}',
            'Description': 'Receive security guidelines (1=Yes, 2=No)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q30: Extent follow guidelines
    if 'Q30' in combined_data_df.columns:
        numeric_col = convert_to_numeric(combined_data_df, 'Q30', extent_mapping)
        results.append({
            'Question': f'Q30: {question_text_row["Q30"]}',
            'Description': 'Extent follow guidelines (5=Entirely, 4=Mostly, 3=Somewhat, 2=A little, 1=Not at all)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q31: Privacy practices effectiveness
    if 'Q31' in combined_data_df.columns:
        numeric_col = convert_to_numeric(combined_data_df, 'Q31', extent_mapping)
        results.append({
            'Question': f'Q31: {question_text_row["Q31"]}',
            'Description': 'Privacy practices + guidelines reduce risks (5=Entirely, 4=Mostly, 3=Somewhat, 2=A little, 1=Not at all)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q32: Privacy practices effectiveness (without guidelines)
    if 'Q32' in combined_data_df.columns:
        numeric_col = convert_to_numeric(combined_data_df, 'Q32', extent_mapping)
        results.append({
            'Question': f'Q32: {question_text_row["Q32"]}',
            'Description': 'Privacy practices reduce risks (5=Entirely, 4=Mostly, 3=Somewhat, 2=A little, 1=Not at all)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q33: Mitigation effectiveness
    q33_cols = [col for col in combined_data_df.columns if col.startswith('Q33_')]
    for col in q33_cols:
        numeric_col = convert_to_numeric(combined_data_df, col, effectiveness_mapping)
        results.append({
            'Question': f'{col}: {question_text_row[col]}',
            'Description': f'{col}: Mitigation effectiveness (5=Extremely effective, 4=Very effective, 3=Moderately effective, 2=Slightly effective, 1=Not effective at all)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Q34: Mitigation likelihood
    q34_cols = [col for col in combined_data_df.columns if col.startswith('Q34_')]
    for col in q34_cols:
        numeric_col = convert_to_numeric(combined_data_df, col, likelihood_mapping)
        results.append({
            'Question': f'{col}: {question_text_row[col]}',
            'Description': f'{col}: Adoption likelihood (5=Extremely likely, 4=Somewhat likely, 3=Neither likely nor unlikely, 2=Somewhat unlikely, 1=Extremely unlikely)',
            'Mean': numeric_col.mean(),
            'Std_Dev': numeric_col.std()
        })
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    generate_markdown_report(combined_data_df, question_text_row, output_file='output.md')
        
    # Generate visualizations if requested
    if create_visualizations:
        # Create output directory for visualizations
        vis_output_dir = 'visuals'
        Path(vis_output_dir).mkdir(exist_ok=True)
        
        generate_visualizations(combined_data_df, question_text_row, vis_output_dir)

if __name__ == '__main__':
    main()
