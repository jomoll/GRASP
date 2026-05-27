"""
Dataset split for MedAgentBench (test_data_v2.json)

300 tasks, 30 per task type across 10 clinical types.

OOD test   : tasks 6, 7  (30 each — held out, out-of-distribution)
In-dist    : tasks 1–5, 8, 9, 10  (8 task types × 30 samples)
  Dev      : 12 per in-dist task type  →  96 total
  Val      : 10 per in-dist task type  →  80 total
  ID test  :  8 per in-dist task type  →  64 total

Fixed seed for reproducibility: SEED = 42
"""

import json
import random
from collections import defaultdict
from pathlib import Path
import tempfile

SEED      = 42
OOD_TASKS = {"task6", "task7"}
DEV_N     = 12
VAL_N     = 10
ID_TEST_N =  8

DATA_DIR = Path(__file__).parent
INPUT_FILE = DATA_DIR / "test_data_v2.json"
OUTPUT_FILES = {
    "test":    DATA_DIR / "split_test.json",
    "id_test": DATA_DIR / "split_id_test.json",
    "dev":     DATA_DIR / "split_dev.json",
    "val":     DATA_DIR / "split_val.json",
}


def get_task_id(sample: dict) -> str:
    return sample["id"].rsplit("_", 1)[0]


def _atomic_dump_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        prefix=f".{path.stem}.",
        suffix=".tmp",
    ) as tmp:
        json.dump(payload, tmp, indent=2, ensure_ascii=False)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def main():
    with open(INPUT_FILE) as f:
        data = json.load(f)

    by_task = defaultdict(list)
    for sample in data:
        by_task[get_task_id(sample)].append(sample)

    test, id_test, dev, val = [], [], [], []
    rng = random.Random(SEED)

    for task, samples in sorted(by_task.items()):
        if task in OOD_TASKS:
            test.extend(samples)
        else:
            assert len(samples) == DEV_N + VAL_N + ID_TEST_N, (
                f"{task}: expected {DEV_N + VAL_N + ID_TEST_N} samples, got {len(samples)}"
            )
            shuffled = samples[:]
            rng.shuffle(shuffled)
            dev.extend(shuffled[:DEV_N])
            val.extend(shuffled[DEV_N : DEV_N + VAL_N])
            id_test.extend(shuffled[DEV_N + VAL_N :])

    assert len(test) + len(id_test) + len(dev) + len(val) == len(data), \
        "Split sizes do not sum to total"
    assert set(get_task_id(s) for s in test) == OOD_TASKS, \
        "OOD test set contains unexpected tasks"
    assert not (set(get_task_id(s) for s in dev) & OOD_TASKS), \
        "Dev set contains held-out tasks"
    assert not (set(get_task_id(s) for s in val) & OOD_TASKS), \
        "Val set contains held-out tasks"
    assert not (set(get_task_id(s) for s in id_test) & OOD_TASKS), \
        "ID test set contains held-out tasks"
    assert not {s["id"] for s in dev} & {s["id"] for s in val}, \
        "Dev and val sets overlap"
    assert not {s["id"] for s in dev} & {s["id"] for s in id_test}, \
        "Dev and id_test sets overlap"
    assert not {s["id"] for s in val} & {s["id"] for s in id_test}, \
        "Val and id_test sets overlap"

    for split_name, split_data in [("test", test), ("id_test", id_test), ("dev", dev), ("val", val)]:
        _atomic_dump_json(OUTPUT_FILES[split_name], split_data)

    print(f"Input:      {INPUT_FILE}")
    print(f"Seed:       {SEED}")
    print(f"OOD tasks:  {sorted(OOD_TASKS)}")
    print(f"Per in-dist task: dev={DEV_N}, val={VAL_N}, id_test={ID_TEST_N}")
    print()

    dev_by_task     = defaultdict(int)
    val_by_task     = defaultdict(int)
    id_test_by_task = defaultdict(int)
    test_by_task    = defaultdict(int)
    for s in dev:     dev_by_task[get_task_id(s)]     += 1
    for s in val:     val_by_task[get_task_id(s)]     += 1
    for s in id_test: id_test_by_task[get_task_id(s)] += 1
    for s in test:    test_by_task[get_task_id(s)]    += 1

    all_tasks = sorted(by_task.keys(), key=lambda x: int(x.replace("task", "")))
    print(f"{'task':<10} {'dev':>6} {'val':>6} {'id_test':>8} {'ood_test':>9}")
    print("-" * 43)
    for task in all_tasks:
        print(
            f"{task:<10} {dev_by_task[task]:>6} {val_by_task[task]:>6}"
            f" {id_test_by_task[task]:>8} {test_by_task[task]:>9}"
        )
    print("-" * 43)
    print(f"{'TOTAL':<10} {len(dev):>6} {len(val):>6} {len(id_test):>8} {len(test):>9}")
    print(f"\nWrote: {[str(OUTPUT_FILES[s]) for s in ('dev', 'val', 'id_test', 'test')]}")


if __name__ == "__main__":
    main()
