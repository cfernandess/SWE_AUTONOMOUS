# patch_evaluator.py
import json
import subprocess
import uuid

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

    def evaluate(self, patch: str) -> dict:
        instance_id = self.problem.instance_id
        predictions_path = (
            self.environment.output_path / f"{instance_id}.predictions.json"
        )

        predictions_path.write_text(
            json.dumps(
                [
                    {
                        "instance_id": instance_id,
                        "model_patch": patch,
                        "model_name_or_path": self.config_agent.config_model.model_name,
                    }
                ],
                indent=2,
            )
        )

        run_id = f"agent-eval-{uuid.uuid4().hex[:8]}"
        swebench_path = self.environment.swebench_path
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

        report_name = f"{self.config_agent.config_model.model_name}.{run_id}.json"
        actual_report = swebench_path / report_name
        final_report_path = self.environment.output_path / report_name

        if not actual_report.exists():
            raise FileNotFoundError(f"No SWE-bench report found: {actual_report}")

        actual_report.replace(final_report_path)
        results = json.loads(final_report_path.read_text())
        self.logger.info(f"[Evaluator] 📁 Report saved to {final_report_path}")

        self._print_diagnostics(results, patch)
        return {"patch": patch, "evaluation": results}

    def _print_diagnostics(self, results: dict, patch: str):
        instance_id = self.problem.instance_id
        result = results.get("results", {}).get(instance_id, {})
        status = result.get("status", "UNKNOWN")
        resolved = status == "RESOLVED"

        if resolved:
            self.logger.info("[Evaluator] ✅ Instance resolved successfully!")
        else:
            self.logger.warning(f"[Evaluator] ❌ Instance NOT resolved: {instance_id}")
            self.logger.info(f"🔍 Status: {status}")
            self.logger.info(f"📄 Patch:\n{patch.strip() or '[EMPTY PATCH]'}")

            traj_path = self.environment.output_path / f"{instance_id}.trajectory.jsonl"
            if traj_path.exists():
                self.logger.info(f"📍 Trajectory log available at: {traj_path}")
            else:
                self.logger.info(f"📍 No trajectory log found at: {traj_path}")


# EOF
