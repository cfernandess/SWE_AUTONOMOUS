# swe_bench_util.py
from typing import List

from datasets import load_dataset

from src.models.problem import Problem


def load_swe_bench(
    instance_id: str, path: str = "SWE-bench/SWE-bench_Verified", split: str = "test"
) -> Problem:
    dataset = load_dataset(path=path, split=split, streaming=False).filter(
        lambda x: x["instance_id"] == instance_id
    )
    samples = list(dataset)
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


def load_swe_bench_difficulty(
    path: str = "princeton-nlp/SWE-bench_Verified",
    split: str = "test",
    difficulty_tag: str = "<15 min fix"
) -> List[Problem]:
    dataset = load_dataset(path=path, split=split, streaming=False)

    # Filter for the easiest problems using the difficulty attribute
    easy_samples = dataset.filter(lambda x: x.get("difficulty", "") == difficulty_tag)

    return [
        Problem(
            instance_id=s["instance_id"],
            problem_statement=s["problem_statement"],
            repo=s["repo"],
            base_commit=s["base_commit"],
            hints_text=s.get("hints_text", "N/A"),
            created_at=s.get("created_at", "N/A"),
            version=s.get("version", "N/A"),
            environment_setup_commit=s.get("environment_setup_commit", "N/A"),
            patch=s.get("patch", "N/A"),
            test_patch=s.get("test_patch", "N/A"),
            FAIL_TO_PASS=s.get("FAIL_TO_PASS", "N/A"),
            PASS_TO_PASS=s.get("PASS_TO_PASS", "N/A"),
        )
        for s in easy_samples
    ]




# EOF
