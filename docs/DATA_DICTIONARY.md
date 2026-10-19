# Data Dictionary

## 1. Overview
This document specifies the variable definitions, types, constraints, and format conventions for the **Poll Results Visualizer** project. 

The application utilizes a **long-format response schema** (one row per respondent per question answered). This layout is suitable for all survey types—including customer satisfaction (CSAT/NPS), employee engagement, product research, and opinion polling.

---

## 2. Final Long-Format Survey Response Schema

| Field Name | Data Type | Nullable | Allowed Values / Range | Description |
| :--- | :--- | :--- | :--- | :--- |
| `response_id` | String | No | Unique ID (e.g. `RESP-CSAT-000001`) | Globally unique identifier for this individual response row. |
| `respondent_id` | String | No | Alphanumeric (e.g. `CUST-0001`) | Anonymized identifier for the respondent. Appears across multiple rows if answering multiple questions. |
| `survey_type` | String | No | Categorical (`customer_satisfaction`, `employee_engagement`, etc.) | Domain or project identifier for the survey. |
| `question_id` | String | No | Alphanumeric code (e.g. `CSAT_OVERALL`, `EE_ENPS`) | Unique identifier for the specific survey question. |
| `question_text` | String | No | Free text | Full prompt or wording presented to the respondent. |
| `question_type` | String | No | `single_choice`, `rating`, `nps`, `multi_select`, `text` | Functional question classification driving downstream analytics. |
| `answer` | String | Yes | Type-dependent (see Section 3) | Respondent's submitted response. Null or empty string indicates an omitted / skipped question. |
| `response_timestamp` | String / Datetime | Yes | ISO 8601 (e.g. `2026-02-15T14:30:00Z`) | Timestamp when the survey response was submitted. |
| `segment` | String | Yes | Categorical (e.g. `Enterprise`, `Engineering`) | Demographic, cohort, or organizational segment for cross-tabulation. |
| `weight` | Float | Yes | $> 0.0$ (typically $0.5 \le w \le 2.0$, default $1.0$) | Post-stratification or sample weight assigned to this respondent. |

---

## 3. Supported Question Types & Value Constraints

| Question Type | Allowed Values & Format | Bounds / Constraints | Missing Value Handling |
| :--- | :--- | :--- | :--- |
| `single_choice` | Categorical string (e.g. `"Live Chat"`, `"Remote"`) | Must match survey option choices | Empty/NaN flagged as warning (skipped answer) |
| `rating` | Discrete integer stored as string (e.g. `"1"`, `"2"`, `"3"`, `"4"`, `"5"`) | **1 to 5 inclusive** ($1 \le x \le 5$). Non-numeric or out-of-bounds flagged as validation error | Empty/NaN flagged as warning (skipped answer) |
| `nps` | Net Promoter Score integer stored as string (e.g. `"0"` to `"10"`) | **0 to 10 inclusive** ($0 \le x \le 10$). Non-numeric or out-of-bounds flagged as validation error | `"0"` is treated as a valid detractor score; genuine empty/NaN flagged as warning |
| `multi_select` | Valid JSON array string of selected options (e.g. `'["Email", "Chat"]'`) | Must be valid JSON array of strings | Empty array `'[]'` or NaN represents no options selected |
| `text` | Unstructured open-ended string | RFC 4180 compliant CSV text (handles commas, quotes, newlines) | Empty/NaN treated as no comment submitted |

---

## 4. Duplicate Rules & Key Uniqueness
1. **Response ID (`response_id`)**: Must be globally unique across all rows in a dataset. Duplicate response IDs indicate corrupted data ingestion.
2. **Single-Answer Uniqueness (`(respondent_id, question_id)`)**: For single-answer question types (`single_choice`, `rating`, `nps`, `text`), a respondent may only have one response row per question. Duplicates trigger a validation error.
3. **Multi-Select Representation**: Multi-select responses consolidate all selected options into a single JSON array string within the `answer` field on one row.

---

## 5. Storage Directory Conventions
- **`data/raw/`**: Unmodified original datasets received from external sources (strictly read-only).
- **`data/processed/`**: Cleaned, imputed, and standardized datasets produced by processing pipelines.
- **`data/synthetic/`**: Deterministic mock datasets generated for testing, demos, and portfolio exploration.
