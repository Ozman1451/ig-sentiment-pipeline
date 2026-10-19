# IG Sentiment & Trend Pipeline (Gen Z QSR Edition)

An end-to-end, locally hosted data pipeline for scraping, cleaning, and classifying Instagram comments. This project focuses on the Pakistani Quick Service Restaurant (QSR) sector, utilizing large language models to parse Roman Urdu and Gen Z slang into structured, actionable sentiment data.

## 🏗 System Architecture

The pipeline is entirely self-contained and modular, designed to run inference locally on consumer GPU hardware without relying on paid LLM APIs.

1. **Extraction:** Asynchronous scraping of target Instagram URLs via Apify.
2. **Sanitization:** Strict Pandas filtering to deduplicate comments, hash usernames for privacy, and strip meaningless text/spam.
3. **Local Inference:** `vLLM` serving **Qwen 2.5-7B-Instruct** (FP8 quantized) on an RTX 5070 Ti, enforcing strict JSON schemas via Pydantic.
4. **Validation:** Automated canary testing and manual audit sampling (Wilson Score Interval calculation) to ensure >80% tagging accuracy.
5. **Visualization:** Interactive Streamlit dashboard for real-time exploratory data analysis.

## 🛠 Tech Stack

*   **Data Collection:** `apify-client`
*   **Data Processing:** `pandas`, `pyarrow`, `re`
*   **LLM Backend:** `vLLM` (TORCH_SDPA backend), `OpenAI` Python Client
*   **Validation:** `Pydantic`
*   **Visualization:** `Streamlit`, `Plotly`

## 📂 Repository Structure
.
├── config/
│   └── brands.txt                # Target Instagram URLs
├── prompts/
│   └── tagger_system.md          # Persona, context, and taxonomy rules
├── reports/
│   ├── final_qsr_data.csv        # Master structured dataset
│   ├── qsr_summary.md            # High-level aggregate markdown report
│   └── qsr_audit_sample.csv      # Human-validated sample for accuracy metrics
├── src/
│   ├── aggregate.py              # Merges AI tags with clean text
│   ├── clean.py / strict_clean.py# Removes spam, hashes users, drops garbage text
│   ├── collect.py / collect_*.py # Apify extraction scripts
│   ├── dashboard.py              # Streamlit interactive UI
│   ├── schema.py                 # Pydantic JSON enforcement models
│   ├── tag.py                    # Batched LLM inference script
│   └── test_canaries.py          # Pre-flight alignment tests
└── README.md
## 🚀 Key Features

*   **Roman Urdu & Slang Comprehension:** Custom system prompts allow the model to accurately classify hyper-local internet slang (e.g., "mid", "scene on hai", "W").
*   **Garbage Filtering:** Regex-based sanitization ensures the LLM only processes comments with semantic value, preventing false-positive hallucination on blank or emoji-only inputs.
*   **Hardware Optimized:** Utilizes `CUDA_DEVICE_ORDER` isolation and FlashAttention (SDPA) for high-throughput local inference (~1.7 iterations/sec on a 7B model).
