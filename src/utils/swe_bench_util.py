from typing import List

from datasets import load_dataset
from src.models.problem import Problem


def load_swe_bench(dataset_name: str, split: str = "dev", index=None) -> List[Problem]:
    if index is None:
        index = []
    dataset = load_dataset(dataset_name, split=split)
    return [
        Problem(
            instance_id=sample["instance_id"],
            problem_statement=sample["problem_statement"],
            repo=sample["repo"],
            base_commit=sample["base_commit"],
            hints_text=sample.get("hints_text", "N/A"),
            created_at=sample.get("created_at", "N/A"),
            version=sample.get("version", "N/A"),
            environment_setup_commit=sample.get("environment_setup_commit", "N/A"),
            patch=sample.get("patch", "N/A"),
            test_patch=sample.get("test_patch", "N/A"),
            FAIL_TO_PASS=sample.get("FAIL_TO_PASS", "N/A"),
            PASS_TO_PASS=sample.get("PASS_TO_PASS", "N/A"),
        )
        for i in index
        for sample in [dataset[i]]
    ]


def load_swe_bench_verified_by_id(instance_id: str) -> Problem:
    dataset = load_dataset(
        "princeton-nlp/SWE-bench_Verified",
        split="dev",
        streaming=False
    ).filter(lambda x: x["instance_id"] == instance_id)

    samples = list(dataset)  # Force evaluation of filtered subset

    if not samples:
        raise ValueError(f"Instance ID {instance_id} not found.")

    sample = samples[0]
    return Problem(
        instance_id=sample["instance_id"],
        problem_statement=sample["problem_statement"],
        repo=sample["repo"],
        base_commit=sample["base_commit"],
        hints_text=sample.get("hints_text", "N/A"),
        created_at=sample.get("created_at", "N/A"),
        version=sample.get("version", "N/A"),
        environment_setup_commit=sample.get("environment_setup_commit", "N/A"),
        patch=sample.get("patch", "N/A"),
        test_patch=sample.get("test_patch", "N/A"),
        FAIL_TO_PASS=sample.get("FAIL_TO_PASS", "N/A"),
        PASS_TO_PASS=sample.get("PASS_TO_PASS", "N/A"),
    )
