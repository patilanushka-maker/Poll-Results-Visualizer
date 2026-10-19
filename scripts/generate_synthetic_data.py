"""Deterministic Synthetic Survey Data Generator.

Generates realistic, reproducible survey datasets across multiple domains:
1. Customer Satisfaction (CSAT & NPS)
2. Employee Engagement
3. Product Preferences

All generated data follows the general-purpose long-format response schema.
"""

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import random
from typing import Any, Optional, Union
import pandas as pd


# Survey specifications for the three distinct domains
SURVEY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "customer_satisfaction": {
        "survey_type": "customer_satisfaction",
        "segments": ["Enterprise", "Mid-Market", "SMB", "Consumer"],
        "segment_weights": [0.25, 0.35, 0.30, 0.10],
        "id_prefix": "CUST",
        "questions": [
            {
                "question_id": "CSAT_OVERALL",
                "question_text": "Overall, how satisfied are you with our customer support service?",
                "question_type": "rating",
                "rating_weights": [0.03, 0.07, 0.20, 0.45, 0.25],  # 1 to 5
            },
            {
                "question_id": "CSAT_NPS",
                "question_text": "How likely are you to recommend our company to a colleague or peer?",
                "question_type": "nps",
                # 0 to 10 weights (detractors: 0-6, passives: 7-8, promoters: 9-10)
                "nps_weights": [0.01, 0.02, 0.03, 0.04, 0.05, 0.07, 0.08, 0.18, 0.22, 0.18, 0.12],
            },
            {
                "question_id": "CSAT_CHANNEL",
                "question_text": "Which primary support channel did you interact with?",
                "question_type": "single_choice",
                "options": ["Live Chat", "Email", "Phone", "Help Center / Docs"],
                "option_weights": [0.45, 0.30, 0.15, 0.10],
            },
            {
                "question_id": "CSAT_PAIN_POINTS",
                "question_text": "Which areas need the most improvement in your experience?",
                "question_type": "multi_select",
                "options": [
                    "First-response wait time",
                    "Technical issue resolution",
                    "Agent product knowledge",
                    "Documentation clarity",
                    "Self-service workflow",
                ],
            },
            {
                "question_id": "CSAT_FEEDBACK",
                "question_text": "Please share any additional comments regarding your support experience.",
                "question_type": "text",
                "sample_texts": [
                    "The representative was very courteous and resolved my issue within 10 minutes.",
                    "Quick turnaround, though I wish the documentation was a bit more up to date.",
                    "The agent went above and beyond to help fix our \"API sync\" errors; very pleased!",
                    "Waited longer than expected on chat, but the final solution worked well.",
                    "Great experience overall, no complaints whatsoever.",
                    "The automated chatbot was unhelpful, but the human agent who followed up was fantastic.",
                    "Clear instructions provided, and the followup email contained all the right links.",
                ],
            },
        ],
    },
    "employee_engagement": {
        "survey_type": "employee_engagement",
        "segments": ["Engineering", "Marketing", "Sales", "Product", "Operations", "People / HR"],
        "segment_weights": [0.30, 0.15, 0.20, 0.15, 0.12, 0.08],
        "id_prefix": "EMP",
        "questions": [
            {
                "question_id": "EE_ROLE_SATISFACTION",
                "question_text": "How satisfied are you with your current role, growth, and responsibilities?",
                "question_type": "rating",
                "rating_weights": [0.02, 0.08, 0.18, 0.42, 0.30],
            },
            {
                "question_id": "EE_ENPS",
                "question_text": "How likely are you to recommend this organization as a great place to work?",
                "question_type": "nps",
                "nps_weights": [0.01, 0.02, 0.03, 0.04, 0.05, 0.08, 0.10, 0.20, 0.22, 0.15, 0.10],
            },
            {
                "question_id": "EE_WORK_ARRANGEMENT",
                "question_text": "What is your primary working model?",
                "question_type": "single_choice",
                "options": ["Fully Remote", "Hybrid (2-3 days office)", "Office-based"],
                "option_weights": [0.45, 0.40, 0.15],
            },
            {
                "question_id": "EE_VALUED_BENEFITS",
                "question_text": "Which company benefits and perks do you value the most?",
                "question_type": "multi_select",
                "options": [
                    "Health and wellness insurance",
                    "Annual learning & development stipend",
                    "Flexible schedule / Core hours",
                    "Generous parental leave",
                    "Mental health support programs",
                ],
            },
            {
                "question_id": "EE_OPEN_FEEDBACK",
                "question_text": "What is one actionable change that would most improve team productivity?",
                "question_type": "text",
                "sample_texts": [
                    "Reduce recurring status meetings; reserve more uninterrupted focus blocks.",
                    "More transparency during quarterly goal planning and roadmapping.",
                    "The learning stipend has been wonderful; let's keep expanding technical workshops.",
                    "Cross-department communication has improved, but tooling integration needs work.",
                    "Our team culture is supportive, and leadership genuinely listens to feedback.",
                    "Streamline internal approval workflows to move faster on customer feature requests.",
                ],
            },
        ],
    },
    "product_preferences": {
        "survey_type": "product_preferences",
        "segments": ["Power Users (Daily)", "Regular Users (Weekly)", "Occasional (Monthly)", "Free Trialists"],
        "segment_weights": [0.28, 0.42, 0.20, 0.10],
        "id_prefix": "PROD",
        "questions": [
            {
                "question_id": "PROD_USABILITY",
                "question_text": "How intuitive and easy to use do you find the application interface?",
                "question_type": "rating",
                "rating_weights": [0.04, 0.09, 0.22, 0.40, 0.25],
            },
            {
                "question_id": "PROD_RECOMMEND",
                "question_text": "How likely are you to recommend our software product to an industry peer?",
                "question_type": "nps",
                "nps_weights": [0.02, 0.02, 0.03, 0.05, 0.06, 0.07, 0.12, 0.20, 0.23, 0.12, 0.08],
            },
            {
                "question_id": "PROD_SUBSCRIPTION_TIER",
                "question_text": "Which subscription plan are you currently utilizing?",
                "question_type": "single_choice",
                "options": ["Community (Free)", "Professional", "Team", "Enterprise Custom"],
                "option_weights": [0.25, 0.40, 0.22, 0.13],
            },
            {
                "question_id": "PROD_ACTIVE_MODULES",
                "question_text": "Which functional modules do you use regularly?",
                "question_type": "multi_select",
                "options": [
                    "Interactive Analytics Dashboard",
                    "Automated Data Cleaning",
                    "Custom CSV Export",
                    "Executive PDF Reporting",
                    "Webhook Alerts",
                ],
            },
            {
                "question_id": "PROD_WISHLIST",
                "question_text": "What new integration or capability would you like to see next?",
                "question_type": "text",
                "sample_texts": [
                    "Would love direct integration with Google Sheets and automated daily syncing.",
                    "The charting options are crisp, but more color palette customization would be great.",
                    "The \"export to slide deck\" feature would save our marketing team hours every Monday.",
                    "Fast loading times and clean layout; best tool we've adopted this year.",
                    "Need deeper role-based permissions for guest and contractor accounts.",
                ],
            },
        ],
    },
}


def generate_dataset(
    survey_key: str,
    n_respondents: int = 150,
    seed: int = 42,
    base_timestamp: Optional[datetime] = None,
) -> pd.DataFrame:
    """Generate a single deterministic synthetic survey dataset.

    Parameters
    ----------
    survey_key : str
        Key identifying the survey domain: 'customer_satisfaction',
        'employee_engagement', or 'product_preferences'.
    n_respondents : int, optional
        Number of distinct respondents to generate, by default 150.
    seed : int, optional
        Random seed ensuring complete reproducibility, by default 42.
    base_timestamp : datetime, optional
        Starting datetime reference for timestamp generation.

    Returns
    -------
    pd.DataFrame
        Long-format survey DataFrame adhering to the project schema.
    """
    if survey_key not in SURVEY_DEFINITIONS:
        raise ValueError(
            f"Unknown survey_key: '{survey_key}'. "
            f"Available keys: {list(SURVEY_DEFINITIONS.keys())}"
        )

    spec = SURVEY_DEFINITIONS[survey_key]
    rng = random.Random(seed)

    if base_timestamp is None:
        base_timestamp = datetime(2026, 1, 15, 9, 0, 0)

    rows: list[dict[str, Any]] = []
    global_response_counter = 1

    for r_idx in range(1, n_respondents + 1):
        respondent_id = f"{spec['id_prefix']}-{r_idx:04d}"
        segment = rng.choices(spec["segments"], weights=spec["segment_weights"])[0]

        # Each respondent completed the survey at a specific random time within a 60-day window
        offset_minutes = rng.randint(0, 60 * 24 * 60)
        resp_time = base_timestamp + timedelta(minutes=offset_minutes)
        timestamp_str = resp_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Post-stratification synthetic weight centered around 1.0
        weight = round(rng.uniform(0.85, 1.25), 2)

        for q in spec["questions"]:
            response_id = f"RESP-{survey_key[:4].upper()}-{global_response_counter:06d}"
            global_response_counter += 1

            q_id = q["question_id"]
            q_text = q["question_text"]
            q_type = q["question_type"]

            # Generate answer according to question type
            if q_type == "rating":
                # Choices 1 through 5
                answer_val = str(rng.choices([1, 2, 3, 4, 5], weights=q["rating_weights"])[0])
            elif q_type == "nps":
                # Choices 0 through 10
                answer_val = str(rng.choices(list(range(11)), weights=q["nps_weights"])[0])
            elif q_type == "single_choice":
                answer_val = rng.choices(q["options"], weights=q["option_weights"])[0]
            elif q_type == "multi_select":
                # Pick 1 to 3 distinct options
                k = rng.randint(1, min(3, len(q["options"])))
                selected_options = rng.sample(q["options"], k)
                selected_options.sort()
                answer_val = json.dumps(selected_options)
            elif q_type == "text":
                answer_val = rng.choice(q["sample_texts"])
            else:
                answer_val = ""

            rows.append(
                {
                    "response_id": response_id,
                    "respondent_id": respondent_id,
                    "survey_type": spec["survey_type"],
                    "question_id": q_id,
                    "question_text": q_text,
                    "question_type": q_type,
                    "answer": answer_val,
                    "response_timestamp": timestamp_str,
                    "segment": segment,
                    "weight": weight,
                }
            )

    return pd.DataFrame(rows)


def generate_all_synthetic_datasets(
    output_dir: Union[str, Path] = "data/synthetic",
    n_respondents: int = 150,
    seed: int = 42,
) -> dict[str, Path]:
    """Generate all three canonical synthetic survey datasets and save to disk.

    Ensures that files are strictly written to the designated synthetic directory,
    never writing to 'data/raw/' or 'data/processed/'.

    Parameters
    ----------
    output_dir : Union[str, Path], optional
        Target directory for generated CSV files, by default "data/synthetic".
    n_respondents : int, optional
        Number of respondents per dataset, by default 150.
    seed : int, optional
        Base random seed, by default 42.

    Returns
    -------
    dict[str, Path]
        Mapping of survey keys to the created file paths.
    """
    out_path = Path(output_dir)

    # Safety check: Guard against accidental write to raw or processed
    resolved_parts = out_path.resolve().parts
    if "raw" in resolved_parts or "processed" in resolved_parts:
        raise ValueError(
            f"Safety guard: Output directory '{output_dir}' cannot point to 'raw' or 'processed'."
        )

    out_path.mkdir(parents=True, exist_ok=True)
    generated_files: dict[str, Path] = {}

    for idx, survey_key in enumerate(SURVEY_DEFINITIONS.keys()):
        # Use a deterministic domain-specific seed derived from the master seed
        domain_seed = seed + (idx * 100)
        df = generate_dataset(survey_key, n_respondents=n_respondents, seed=domain_seed)

        target_file = out_path / f"{survey_key}.csv"
        # Export with standard quoting so text containing quotes and commas is preserved
        df.to_csv(target_file, index=False, encoding="utf-8")
        generated_files[survey_key] = target_file

    return generated_files


def main() -> None:
    """CLI entry point for generating synthetic survey data."""
    parser = argparse.ArgumentParser(
        description="Deterministic Synthetic Survey Data Generator for Poll Results Visualizer."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/synthetic",
        help="Directory to save generated CSV files (default: data/synthetic).",
    )
    parser.add_argument(
        "--respondents",
        type=int,
        default=150,
        help="Number of respondents per dataset (default: 150).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Master random seed for reproducibility (default: 42).",
    )

    args = parser.parse_args()
    print(f"Generating synthetic datasets (respondents={args.respondents}, seed={args.seed})...")
    created = generate_all_synthetic_datasets(
        output_dir=args.output_dir,
        n_respondents=args.respondents,
        seed=args.seed,
    )
    for name, filepath in created.items():
        print(f"  [OK] Generated {name}: {filepath} ({filepath.stat().st_size} bytes)")
    print("Done! All synthetic datasets generated successfully.")


if __name__ == "__main__":
    main()
