# patch_evaluator.py
import difflib
import json
import subprocess
import uuid
from typing import Optional

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
from src.utils.localization_scores import compute_localization_scores


class PatchEvaluator:
    def __init__(
        self,
        problem: Problem,
        environment: Environment,
        config_agent: ConfigAgent,
    ):
        self.problem = problem
        self.environment = environment
        self.config_agent = config_agent
        self.logger = environment.logger

    def evaluate(self, patch: Optional[str] = None) -> dict:
        patch = self.normalize_patch(patch)
        # Fix #1: Reset repo to base_commit
        subprocess.run(
            ["git", "reset", "--hard", self.problem.base_commit],
            cwd=self.environment.repo_path,
            check=True,
        )
        self.logger.info(
            f"[Evaluator] 🔁 Reset repo to base_commit: {self.problem.base_commit}"
        )

        # Fix #2: Verify HEAD == base_commit
        git_hash = (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=self.environment.repo_path
            )
            .decode()
            .strip()
        )
        assert (
            git_hash == self.problem.base_commit
        ), f"Repo HEAD is at {git_hash}, expected {self.problem.base_commit}"
        instance_id = self.problem.instance_id
        model_name = self.config_agent.config_model.model_name
        output_path = self.environment.output_path
        swebench_path = self.environment.swebench_path
        repo_path = self.environment.repo_path

        if patch is None:
            patch_file = output_path / f"{instance_id}.patch"
            patch = patch_file.read_text()

        # Save patch to file and check if it applies
        patch_path = output_path / f"{instance_id}.patch"
        patch_path.write_text(patch)

        apply_check = subprocess.run(
            ["git", "apply", "--check", str(patch_path)],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if apply_check.returncode != 0:
            error_msg = apply_check.stderr.decode()
            self.logger.error(f"[Evaluator] ❌ Patch failed to apply:\n{error_msg}")
            self._maybe_log_gold_patch_diff(patch)
            return {
                "patch": patch,
                "evaluation": {
                    "run_id": "skipped-apply",
                    "status": "ERROR",
                    "report": {},
                    "log": error_msg,
                },
            }

        # Write predictions file
        predictions_path = output_path / f"{instance_id}.predictions.json"
        predictions_path.write_text(
            json.dumps(
                [
                    {
                        "instance_id": instance_id,
                        "model_patch": patch,
                        "model_name_or_path": model_name,
                    }
                ],
                indent=2,
            )
        )

        run_id = f"agent-eval-{uuid.uuid4().hex[:8]}"
        self.logger.info(f"[Evaluator] 📊 Running SWE-bench (run_id={run_id})")

        try:
            completed = subprocess.run(
                [
                    "python",
                    "-m",
                    "swebench.harness.run_evaluation",
                    "--predictions_path",
                    str(predictions_path),
                    "--run_id",
                    run_id,
                    "--instance_ids",
                    instance_id,
                    "--max_workers",
                    "1",
                    "--namespace",
                    "",
                    "--dataset_name",
                    "princeton-nlp/SWE-bench_Verified",
                    "--split",
                    "test",
                ],
                cwd=swebench_path,
                capture_output=True,
                text=True,
                check=True,
            )
            self.logger.info("[Evaluator] ✅ Evaluation subprocess completed.")
            self.logger.debug(f"🔧 STDOUT:\n{completed.stdout.strip()}")
            self.logger.debug(f"🛑 STDERR:\n{completed.stderr.strip()}")

        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"[Evaluator] ❌ SWE-bench failed with error code {e.returncode}"
            )
            self.logger.error(f"🔧 STDOUT:\n{e.stdout.strip()}")
            self.logger.error(f"🛑 STDERR:\n{e.stderr.strip()}")
            raise RuntimeError(
                f"SWE-bench subprocess failed:\n{e.stderr.strip()}"
            ) from e

        report_name = f"{model_name}.{run_id}.json"
        report_path = swebench_path / report_name
        if not report_path.exists():
            raise FileNotFoundError(f"No SWE-bench summary report found: {report_path}")

        summary = json.loads(report_path.read_text())
        self.logger.info(f"[Evaluator] 📁 Summary report saved to {report_path}")
        self._print_summary_diagnostics(
            summary, patch, completed.stdout, completed.stderr
        )
        # Compute localization scores
        localization_scores = compute_localization_scores(patch, self.problem.patch)
        summary.update(localization_scores)

        return {"patch": patch, "evaluation": summary}

    def normalize_patch(self, patch: str) -> str:
        return patch if patch.endswith("\n") else patch + "\n"

    def _print_summary_diagnostics(
        self, summary: dict, patch: str, stdout: str, stderr: str
    ):
        instance_id = self.problem.instance_id

        if instance_id in summary.get("resolved_ids", []):
            status = "RESOLVED"
            self.logger.info(
                f"[Evaluator] ✅ Instance {instance_id} resolved successfully!"
            )
        elif instance_id in summary.get("unresolved_ids", []):
            status = "UNRESOLVED"
            self.logger.warning(f"[Evaluator] ❌ Instance {instance_id} NOT resolved")
        else:
            status = "UNKNOWN"
            self.logger.warning(
                f"[Evaluator] ⚠️ No result entry found for: {instance_id}"
            )

        self.logger.info(f"🔍 Status: {status}")
        self.logger.info(f"📄 Patch:\n{patch.strip() or '[EMPTY PATCH]'}")

        traj_path = self.environment.output_path / f"{instance_id}.trajectory.jsonl"
        if traj_path.exists():
            self.logger.info(f"📍 Trajectory log available at: {traj_path}")
        else:
            self.logger.info(f"📍 No trajectory log found for: {instance_id}")

        if status != "RESOLVED":
            self.logger.info("🔎 Additional diagnostic output:")
            self.logger.info(f"🧵 STDOUT:\n{stdout.strip()}")
            self.logger.info(f"🧵 STDERR:\n{stderr.strip()}")

    def _maybe_log_gold_patch_diff(self, generated_patch: str):
        gold_patch = getattr(self.problem, "standard_patch", None)
        if not gold_patch:
            return

        diff = list(
            difflib.unified_diff(
                generated_patch.strip().splitlines(),
                gold_patch.strip().splitlines(),
                fromfile="generated_patch",
                tofile="gold_patch",
                lineterm="",
            )
        )
        if diff:
            self.logger.warning("📐 Diff between generated and gold patch:")
            for line in diff:
                self.logger.warning(line)


# EOF
