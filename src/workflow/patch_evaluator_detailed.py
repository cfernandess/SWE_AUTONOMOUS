# patch_evaluator_detailed.py
import difflib
import json
import subprocess
import uuid
from typing import Optional

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
from src.utils.localization_scores import compute_localization_scores
from swebench.harness.grading import get_eval_report, get_logs_eval
from swebench.harness.test_spec.test_spec import TestSpec


class PatchEvaluatorDetailed:
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

        # Reset repo
        subprocess.run(
            ["git", "reset", "--hard", self.problem.base_commit],
            cwd=self.environment.repo_path,
            check=True,
        )
        self.logger.info(
            f"[Evaluator] 🔁 Reset repo to base_commit: {self.problem.base_commit}"
        )

        # Verify HEAD is correct
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

        # Load patch if not given
        if patch is None:
            patch_file = output_path / f"{instance_id}.patch"
            patch = patch_file.read_text()

        # Write and check patch
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

        # Write predictions
        predictions_path = output_path / f"{instance_id}.predictions.json"
        prediction = {
            "instance_id": instance_id,
            "model_patch": patch,
            "model_name_or_path": model_name,
        }
        predictions_path.write_text(json.dumps([prediction], indent=2))

        # Run evaluation
        run_id = f"agent-eval-{uuid.uuid4().hex[:8]}"
        self.logger.info(f"[Evaluator] 📊 Running SWE-bench (run_id={run_id})")

        try:
            subprocess.run(
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
                check=True,
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(f"[Evaluator] ❌ SWE-bench failed:\n{e}")
            raise

        # TestSpec + log file
        test_spec = TestSpec(
            instance_id=instance_id,
            repo=self.problem.repo,
            version=self.problem.version,
            FAIL_TO_PASS=self.problem.fail_to_pass,
            PASS_TO_PASS=self.problem.pass_to_pass,
            repo_script_list=[],
            eval_script_list=[],
            env_script_list=[],
            arch="amd64",
            language="python",
            docker_specs={},
            namespace="",
        )
        log_path = (
            swebench_path
            / "logs"
            / "run_evaluation"
            / run_id
            / model_name
            / instance_id
            / "run_instance.log"
        )
        logs, _ = get_logs_eval(test_spec, str(log_path))
        log_output = logs.get(instance_id, "")

        # Read summary to determine status
        report_name = f"{model_name}.{run_id}.json"
        report_path = swebench_path / report_name
        summary = json.loads(report_path.read_text())
        resolved = instance_id in summary.get("resolved_ids", [])
        status = "RESOLVED" if resolved else "UNRESOLVED"

        # Extract detailed test report
        report_map = get_eval_report(
            test_spec=test_spec,
            prediction=prediction,
            test_log_path=str(log_path),
            include_tests_status=True,
        )
        instance_report = report_map.get(instance_id, {})
        instance_report["resolved"] = resolved

        # Add localization scores
        localization_scores = compute_localization_scores(patch, self.problem.patch)
        instance_report.update(localization_scores)

        # Logging
        self.logger.info(
            f"{'✅✅ RESOLVED' if status == 'RESOLVED' else '❌❌ UNRESOLVED'}"
        )
        self.logger.info(f"📄 Patch:\n{patch.strip() or '[EMPTY PATCH]'}")
        self.logger.info(f"📝 Log Summary:\n{log_output.strip()[:1000]}")

        traj_path = output_path / f"{instance_id}.trajectory.jsonl"
        if traj_path.exists():
            self.logger.info(f"📍 Trajectory log available at: {traj_path}")
        else:
            self.logger.info(f"📍 No trajectory log found for: {instance_id}")

        return {
            "patch": patch,
            "evaluation": {
                "run_id": run_id,
                "status": status,
                "report": instance_report,
                "log": log_output,
            },
        }

    def normalize_patch(self, patch: str) -> str:
        return patch if patch.endswith("\n") else patch + "\n"

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
