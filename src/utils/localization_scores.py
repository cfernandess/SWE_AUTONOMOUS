from typing import Set, Tuple, Dict, Union


def extract_file_and_lines_from_patch(patch: str) -> Tuple[Set[str], Set[int]]:
    files = set()
    lines = set()

    current_file = None
    current_new_line = None

    for line in patch.splitlines():
        if line.startswith("diff --git"):
            parts = line.split()
            if len(parts) >= 4:
                current_file = parts[2][2:]  # Strip 'a/'
                files.add(current_file)
        elif line.startswith("@@"):
            try:
                header_parts = line.split()
                new_file_range = header_parts[2]  # e.g., '+160,7'
                start = int(new_file_range.split(",")[0][1:])
                current_new_line = start
            except ValueError:
                continue
        elif line.startswith("+") and not line.startswith("+++"):
            if current_new_line is not None:
                lines.add(current_new_line)
                current_new_line += 1
        elif not line.startswith("-"):
            if current_new_line is not None:
                current_new_line += 1

    return files, lines


def compute_localization_scores(
    generated_patch: str, gold_patch: Union[str, None]
) -> Dict[str, float]:
    if not gold_patch:
        return {
            "localization_score_file": 0.0,
            "localization_score_line": 0.0,
        }

    gold_files, gold_lines = extract_file_and_lines_from_patch(gold_patch)
    pred_files, pred_lines = extract_file_and_lines_from_patch(generated_patch)

    file_score = 1.0 if gold_files & pred_files else 0.0
    line_score = len(gold_lines & pred_lines) / len(gold_lines) if gold_lines else 0.0

    return {
        "localization_score_file": file_score,
        "localization_score_line": line_score,
    }
