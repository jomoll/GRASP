"""
Split DBBench data into dev / val / test sets for the skill cycle.

Data split:
  dev  (skill learning) — 60% of standard.jsonl, stratified by type  (~180 samples)
  val  (monitoring)     — 40% of standard.jsonl, stratified by type  (~120 samples)
  test (held-out)       — dev.jsonl (the original benchmark dev set)   (60 samples)

dev.jsonl is kept fully held out as the true test set, mirroring the original
benchmark's intended train/eval structure.

Usage:
    python data/dbbench/split_dataset.py

Outputs:
    data/dbbench/split_dev.json
    data/dbbench/split_val.json
    data/dbbench/split_test.json
"""

import json
import random
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = REPO_ROOT / "data" / "dbbench"
SEED = 42


def _load_jsonl(path: Path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _make_sample(entry: dict, idx: int) -> dict:
    """Convert a raw dataset entry into a skill-cycle sample dict."""
    query_type = entry["type"][0]
    if query_type in ("INSERT", "DELETE", "UPDATE"):
        answer = entry["answer_md5"]
    else:
        answer = entry["label"]
    return {
        "id": idx,
        "description": entry["description"],
        "type": query_type,
        "answer": answer,
    }


def main():
    rng = random.Random(SEED)

    standard = _load_jsonl(DATA_DIR / "standard.jsonl")
    dev_file = _load_jsonl(DATA_DIR / "dev.jsonl")

    # Group standard entries by type for stratified split
    by_type = defaultdict(list)
    for idx, entry in enumerate(standard):
        by_type[entry["type"][0]].append((idx, entry))

    dev_samples = []
    val_samples = []

    for type_name, items in sorted(by_type.items()):
        rng.shuffle(items)
        split_at = max(1, int(len(items) * 0.6))
        dev_items = items[:split_at]
        val_items = items[split_at:]
        for idx, entry in dev_items:
            dev_samples.append(_make_sample(entry, idx))
        for idx, entry in val_items:
            val_samples.append(_make_sample(entry, idx))
        print(f"  {type_name}: {len(dev_items)} dev + {len(val_items)} val")

    # Test: dev.jsonl (offset indices by len(standard) to avoid collision)
    test_samples = [_make_sample(entry, len(standard) + i)
                    for i, entry in enumerate(dev_file)]

    print(f"\nDev:  {len(dev_samples)} samples")
    print(f"Val:  {len(val_samples)} samples")
    print(f"Test: {len(test_samples)} samples (dev.jsonl, held-out)")

    with open(DATA_DIR / "split_dev.json", "w", encoding="utf-8") as f:
        json.dump(dev_samples, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {DATA_DIR / 'split_dev.json'}")

    with open(DATA_DIR / "split_val.json", "w", encoding="utf-8") as f:
        json.dump(val_samples, f, indent=2, ensure_ascii=False)
    print(f"Wrote {DATA_DIR / 'split_val.json'}")

    with open(DATA_DIR / "split_test.json", "w", encoding="utf-8") as f:
        json.dump(test_samples, f, indent=2, ensure_ascii=False)
    print(f"Wrote {DATA_DIR / 'split_test.json'}")


if __name__ == "__main__":
    main()
