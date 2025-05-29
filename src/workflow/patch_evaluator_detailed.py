# patch_evaluator_detailed.py
import json
import subprocess
import uuid
from typing import Optional

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
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
        instance_id = self.problem.instance_id
        model_name = self.config_agent.config_model.model_name
        output_path = self.environment.output_path
        swebench_path = self.environment.swebench_path

        # Load patch from cache if not provided
        if patch is None:
            patch_file = output_path / f"{instance_id}.patch"
            patch = patch_file.read_text()

        # Write predictions file
        predictions_path = output_path / f"{instance_id}.predictions.json"
        prediction = {
            "instance_id": instance_id,
            "model_patch": patch,
            "model_name_or_path": model_name,
        }
        predictions_path.write_text(json.dumps([prediction], indent=2))

        # Run evaluation
        run_id = f"agent-eval-{uuid.uuid4().hex[:8]}"
        self.logger.info(f"[Evaluator] \U0001F4CA Running SWE-bench (run_id={run_id})")

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

        # Construct TestSpec

        test_spec = TestSpec(
            instance_id=instance_id,
            repo=self.problem.repo,
            version=self.problem.version,
            # Expected type 'list[str]', got 'str' instead
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

        # Log file path
        log_path = str(swebench_path / "logs" / f"{run_id}.log")

        # Get detailed evaluation report and logs
        report_map = get_eval_report(
            test_spec=test_spec,
            prediction=prediction,
            test_log_path=log_path,
            include_tests_status=True,
        )
        logs, _ = get_logs_eval(test_spec=test_spec, log_fp=log_path)

        instance_report = report_map.get(instance_id, {})
        log_output = logs.get(instance_id, "")

        status = "RESOLVED" if instance_report.get("resolved", False) else "UNRESOLVED"

        self.logger.info(f"\U0001F50D Status: {status}")
        self.logger.info(f"\U0001F4C4 Patch:\n{patch.strip() or '[EMPTY PATCH]'}")
        self.logger.info(f"\U0001F4DD Log Summary:\n{log_output.strip()[:1000]}")

        traj_path = self.environment.output_path / f"{instance_id}.trajectory.jsonl"
        if traj_path.exists():
            self.logger.info(f"\U0001F4CD Trajectory log available at: {traj_path}")
        else:
            self.logger.info(f"\U0001F4CD No trajectory log found for: {instance_id}")

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


# EOF
