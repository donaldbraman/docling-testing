#!/usr/bin/env python3
"""
Bayesian optimization of HMM parameters using Optuna.

Finds optimal hyperparameters for HMM sequence alignment by intelligently
sampling the parameter space and maximizing macro F1 score.

Usage:
    pip install optuna
    python scripts/evaluation/optimize_hmm_bayesian.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import optuna

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from parse_extraction import ExtractedItem
from prepare_matching_data import load_html_ground_truth
from sequence_alignment.alignment_metrics import calculate_metrics


def extract_line_level_items(pdf_path: Path) -> list:
    """Extract line-level text from PDF as ExtractedItem objects."""
    import fitz

    doc = fitz.open(pdf_path)
    items = []

    for page_idx, page in enumerate(doc):
        page_num = page_idx + 1
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                text = " ".join([span["text"] for span in line["spans"]])
                bbox = line["bbox"]

                if text.strip():
                    items.append(
                        ExtractedItem(
                            text=text.strip(),
                            label="TEXT",
                            page_num=page_num,
                            bbox=bbox,
                            original_docling_label="DocItemLabel.TEXT",
                        )
                    )

    doc.close()
    return items


def hmm_viterbi_with_params(
    items: list[ExtractedItem],
    body_html: list,
    footnote_html: list,
    threshold: float,
    bottom_threshold: float,
    footnote_bias: float,
    state_persistence: float,
    weak_match_penalty: float,
    min_text_length: int,
):
    """
    Modified HMM Viterbi with parameterized values.

    This is a copy of hmm_viterbi_alignment but with parameters exposed.
    """
    import math
    from dataclasses import dataclass

    from prepare_matching_data import normalize_text

    @dataclass
    class HMMMatch:
        extraction_item: any
        matched_html: any
        similarity_score: float
        corrected_label: str | None
        assignment: str
        state_probability: float

    def calculate_similarity(pdf_text: str, html_text: str) -> float:
        try:
            from rapidfuzz import fuzz

            return fuzz.partial_ratio(pdf_text, html_text) / 100.0
        except ImportError:
            from difflib import SequenceMatcher

            return SequenceMatcher(None, pdf_text, html_text).ratio()

    def calculate_emission_probability(item, html_lines, threshold):
        query = normalize_text(item.text)

        if len(query) < min_text_length:
            return (0.01, None)

        best_score = 0.0
        best_html = None

        for html_line in html_lines:
            target = normalize_text(html_line.text)
            score = calculate_similarity(query, target)

            if score > best_score:
                best_score = score
                best_html = html_line

        if best_score >= threshold:
            probability = best_score
            return (probability, best_html)
        else:
            probability = best_score * weak_match_penalty
            return (probability, None)

    def calculate_transition_probability(from_state: str, to_state: str, page_position: float):
        # Use parameterized values
        if page_position > bottom_threshold:
            if to_state == "footnote":
                return footnote_bias
            else:
                return 1.0 - footnote_bias
        else:
            if from_state == to_state:
                return state_persistence
            else:
                return 1.0 - state_persistence

    # Main Viterbi algorithm (same as original)
    n = len(items)
    states = ["body", "footnote"]
    num_states = len(states)

    emissions = []
    for item in items:
        body_prob, body_match = calculate_emission_probability(item, body_html, threshold)
        footnote_prob, footnote_match = calculate_emission_probability(
            item, footnote_html, threshold
        )
        emissions.append(
            {
                "body": (body_prob, body_match),
                "footnote": (footnote_prob, footnote_match),
            }
        )

    viterbi = [[float("-inf")] * num_states for _ in range(n)]
    backpointer = [[None] * num_states for _ in range(n)]

    initial_prob = 1.0 / num_states
    for s, state in enumerate(states):
        emission_prob, _ = emissions[0][state]
        viterbi[0][s] = math.log(initial_prob) + math.log(emission_prob + 1e-10)

    for i in range(1, n):
        if items[i].bbox:
            l, t, r, b = items[i].bbox
            page_position = (t + b) / 2.0
            page_position = min(1.0, max(0.0, page_position / 2200.0))
        else:
            page_position = 0.5

        for s, to_state in enumerate(states):
            emission_prob, _ = emissions[i][to_state]
            best_prev_score = float("-inf")
            best_prev_state = None

            for s_prev, from_state in enumerate(states):
                transition_prob = calculate_transition_probability(
                    from_state, to_state, page_position
                )
                score = viterbi[i - 1][s_prev] + math.log(transition_prob + 1e-10)

                if score > best_prev_score:
                    best_prev_score = score
                    best_prev_state = s_prev

            viterbi[i][s] = best_prev_score + math.log(emission_prob + 1e-10)
            backpointer[i][s] = best_prev_state

    best_final_state = 0
    best_final_score = viterbi[n - 1][0]
    for s in range(1, num_states):
        if viterbi[n - 1][s] > best_final_score:
            best_final_score = viterbi[n - 1][s]
            best_final_state = s

    path = [best_final_state]
    for i in range(n - 1, 0, -1):
        path.append(backpointer[i][path[-1]])
    path.reverse()

    results = []
    for i, item in enumerate(items):
        state_idx = path[i]
        state = states[state_idx]
        emission_prob, matched_html = emissions[i][state]

        if matched_html is not None:
            corrected_label = "body-text" if state == "body" else "footnote-text"
            query = normalize_text(item.text)
            target = normalize_text(matched_html.text)
            similarity = calculate_similarity(query, target)
        else:
            corrected_label = None
            similarity = 0.0

        results.append(
            HMMMatch(
                extraction_item=item,
                matched_html=matched_html,
                similarity_score=similarity,
                corrected_label=corrected_label,
                assignment=state if matched_html else "original",
                state_probability=math.exp(viterbi[i][state_idx]),
            )
        )

    return results


def objective(trial, items, body_html, footnote_html):
    """
    Objective function for Optuna to optimize.

    Returns: Negative macro F1 (Optuna minimizes by default, we want to maximize)
    """
    # Sample parameters from search space
    threshold = trial.suggest_float("threshold", 0.2, 0.5)
    bottom_threshold = trial.suggest_float("bottom_threshold", 0.5, 0.95)
    footnote_bias = trial.suggest_float("footnote_bias", 0.5, 0.95)
    state_persistence = trial.suggest_float("state_persistence", 0.7, 0.99)
    weak_match_penalty = trial.suggest_float("weak_match_penalty", 0.05, 0.3)
    min_text_length = trial.suggest_int("min_text_length", 5, 20)

    # Run HMM with these parameters
    matches = hmm_viterbi_with_params(
        items,
        body_html,
        footnote_html,
        threshold=threshold,
        bottom_threshold=bottom_threshold,
        footnote_bias=footnote_bias,
        state_persistence=state_persistence,
        weak_match_penalty=weak_match_penalty,
        min_text_length=min_text_length,
    )

    # Calculate metrics
    metrics = calculate_metrics(matches, body_html, footnote_html)

    # Report intermediate values for pruning
    trial.report(metrics.macro_f1, step=0)

    # Return macro F1 (Optuna maximizes when direction='maximize')
    return metrics.macro_f1


def main():
    """Run Bayesian optimization for HMM parameters."""
    print("=" * 80)
    print("BAYESIAN OPTIMIZATION OF HMM PARAMETERS")
    print("=" * 80)

    # Load data
    doc_name = "harvard_law_review_unwarranted_warrants"

    print("\n📂 Extracting line-level data from PDF...")
    pdf_path = None
    for pdf_dir in [Path("data/v3_data/raw_pdf"), Path("data/raw_pdf")]:
        candidate = pdf_dir / f"{doc_name}.pdf"
        if candidate.exists():
            pdf_path = candidate
            break

    if not pdf_path:
        print(f"Error: PDF not found for {doc_name}")
        return 1

    items = extract_line_level_items(pdf_path)
    body_html, footnote_html = load_html_ground_truth(doc_name)

    print(f"  Extracted {len(items)} lines from PDF")
    print(f"  Body HTML: {len(body_html)} items")
    print(f"  Footnote HTML: {len(footnote_html)} items")

    # Create Optuna study
    print("\n" + "=" * 80)
    print("RUNNING BAYESIAN OPTIMIZATION")
    print("=" * 80)
    print("\nUsing TPE (Tree-structured Parzen Estimator) sampler")
    print("Optimizing: threshold, bottom_threshold, footnote_bias, state_persistence,")
    print("           weak_match_penalty, min_text_length")
    print("\nTarget: Maximize Macro F1 score")

    study = optuna.create_study(
        direction="maximize",  # Maximize macro F1
        sampler=optuna.samplers.TPESampler(seed=42),
        pruner=optuna.pruners.MedianPruner(),  # Early stopping for bad trials
    )

    # Run optimization
    n_trials = 50  # Usually 20-50 trials is enough
    print(f"\nRunning {n_trials} trials (this may take 5-10 minutes)...")
    print("Progress will be shown as trials complete.\n")

    study.optimize(
        lambda trial: objective(trial, items, body_html, footnote_html),
        n_trials=n_trials,
        show_progress_bar=True,
    )

    # Results
    print("\n" + "=" * 80)
    print("OPTIMIZATION RESULTS")
    print("=" * 80)

    print(f"\n🏆 Best trial: #{study.best_trial.number}")
    print(f"   Macro F1: {study.best_value:.4f}")

    print("\n📊 Best parameters:")
    for param, value in study.best_params.items():
        print(
            f"   {param:20s} = {value:.4f}"
            if isinstance(value, float)
            else f"   {param:20s} = {value}"
        )

    # Compare to default
    print("\n📈 Improvement over default (threshold=0.3, other defaults):")
    default_matches = hmm_viterbi_with_params(
        items,
        body_html,
        footnote_html,
        threshold=0.3,
        bottom_threshold=0.75,
        footnote_bias=0.8,
        state_persistence=0.9,
        weak_match_penalty=0.1,
        min_text_length=10,
    )
    default_metrics = calculate_metrics(default_matches, body_html, footnote_html)

    print(f"   Default Macro F1: {default_metrics.macro_f1:.4f}")
    print(f"   Optimized Macro F1: {study.best_value:.4f}")
    print(
        f"   Improvement: {(study.best_value - default_metrics.macro_f1):.4f} ({(study.best_value / default_metrics.macro_f1 - 1) * 100:.1f}%)"
    )

    # Run with best parameters and show detailed metrics
    print("\n" + "=" * 80)
    print("DETAILED METRICS WITH OPTIMIZED PARAMETERS")
    print("=" * 80)

    best_matches = hmm_viterbi_with_params(
        items,
        body_html,
        footnote_html,
        **study.best_params,
    )
    best_metrics = calculate_metrics(best_matches, body_html, footnote_html)

    print("\n📊 Body Text:")
    print(f"   F1: {best_metrics.body_f1:.4f}")
    print(f"   Precision: {best_metrics.body_precision:.4f}")
    print(f"   Recall: {best_metrics.body_recall:.4f}")
    print(f"   HTML Used: {best_metrics.body_html_used}/{best_metrics.body_html_total}")

    print("\n📊 Footnote Text:")
    print(f"   F1: {best_metrics.footnote_f1:.4f}")
    print(f"   Precision: {best_metrics.footnote_precision:.4f}")
    print(f"   Recall: {best_metrics.footnote_recall:.4f}")
    print(f"   HTML Used: {best_metrics.footnote_html_used}/{best_metrics.footnote_html_total}")

    # Save results
    output_dir = Path("results/sequence_alignment/hmm_optimization")
    output_dir.mkdir(parents=True, exist_ok=True)

    import json

    with open(output_dir / "best_parameters.json", "w") as f:
        json.dump(
            {
                "best_params": study.best_params,
                "best_macro_f1": study.best_value,
                "default_macro_f1": default_metrics.macro_f1,
                "improvement": study.best_value - default_metrics.macro_f1,
                "metrics": best_metrics.to_dict(),
            },
            f,
            indent=2,
        )

    print(f"\n💾 Saved results to {output_dir}/best_parameters.json")

    # Visualization (optional, requires plotly)
    try:
        import importlib.util

        if importlib.util.find_spec("plotly") is None:
            raise ImportError

        print("\n📊 Generating optimization visualizations...")

        # Parameter importance
        fig_importance = optuna.visualization.plot_param_importances(study)
        fig_importance.write_html(output_dir / "param_importances.html")

        # Optimization history
        fig_history = optuna.visualization.plot_optimization_history(study)
        fig_history.write_html(output_dir / "optimization_history.html")

        # Parallel coordinate plot
        fig_parallel = optuna.visualization.plot_parallel_coordinate(study)
        fig_parallel.write_html(output_dir / "parallel_coordinate.html")

        print(f"   Saved visualizations to {output_dir}/")
        print("   Open *.html files in browser to view")

    except ImportError:
        print("\n💡 Install plotly for visualizations: pip install plotly")

    print("\n" + "=" * 80)
    print("BAYESIAN OPTIMIZATION COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
