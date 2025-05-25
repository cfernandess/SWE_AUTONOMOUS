# patch_evaluator.py
import json
import subprocess
import uuid
from typing import Optional

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem


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

        # Read summary report
        report_name = f"{model_name}.{run_id}.json"
        report_path = swebench_path / report_name
        if not report_path.exists():
            raise FileNotFoundError(f"No SWE-bench summary report found: {report_path}")

        summary = json.loads(report_path.read_text())
        self.logger.info(f"[Evaluator] 📁 Summary report saved to {report_path}")

        # Print status using summary
        self._print_summary_diagnostics(summary, patch)

        return {"patch": patch, "evaluation": summary}

    def normalize_patch(self, patch: str) -> str:
        return patch if patch.endswith("\n") else patch + "\n"

    def _print_summary_diagnostics(self, summary: dict, patch: str):
        instance_id = self.problem.instance_id

        if instance_id in summary.get("resolved_ids", []):
            self.logger.info(
                f"[Evaluator] ✅ Instance {instance_id} resolved successfully!"
            )
            status = "RESOLVED"
        elif instance_id in summary.get("unresolved_ids", []):
            self.logger.warning(f"[Evaluator] ❌ Instance {instance_id} NOT resolved")
            status = "UNRESOLVED"
        else:
            self.logger.warning(
                f"[Evaluator] ⚠️ No result entry found for: {instance_id}"
            )
            status = "UNKNOWN"

        self.logger.info(f"🔍 Status: {status}")
        self.logger.info(f"📄 Patch:\n{patch.strip() or '[EMPTY PATCH]'}")

        traj_path = self.environment.output_path / f"{instance_id}.trajectory.jsonl"
        if traj_path.exists():
            self.logger.info(f"📍 Trajectory log available at: {traj_path}")
        else:
            self.logger.info(f"📍 No trajectory log found for: {instance_id}")


# EOF
