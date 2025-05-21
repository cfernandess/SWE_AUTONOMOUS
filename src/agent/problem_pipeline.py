# problem_pipeline.py
import json
import subprocess
import uuid
from pathlib import Path

from src.agent.agent import AutonomousAgent
from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
from src.tools.bash_tool import BashTool
from src.tools.edit_tool import EditorTool
from src.tools.ruff_lint_tool import RuffLintTool
from src.tools.sequential_thinking_tool import SequentialThinkingTool


class ProblemPipeline:
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
        self.traj_logger = environment.traj_logger

        self.tools = [
            BashTool(
                problem=self.problem,
                environment=self.environment,
                config_agent=self.config_agent,
            ),
            EditorTool(
                problem=self.problem,
                environment=self.environment,
                config_agent=self.config_agent,
            ),
            RuffLintTool(
                problem=self.problem,
                environment=self.environment,
                config_agent=self.config_agent,
            ),
            SequentialThinkingTool(
                problem=self.problem,
                environment=self.environment,
                config_agent=self.config_agent,
            ),
        ]
        self.agent = AutonomousAgent(
            problem=self.problem,
            environment=self.environment,
            config_agent=self.config_agent,
            tools=self.tools,
        )

    def generate(self, path: Path, generator, desc: str):
        if path.exists():
            self.logger.info(f"[Cache] ✅ Loaded cached {desc} from {path.name}")
            return json.loads(path.read_text())

        self.logger.info(f"[Cache] ❌ No cache found for {desc}, generating...")
        data = generator()
        self.logger.info(f"[Cache] ✅ Finished generating {desc}")
        path.write_text(json.dumps(data, indent=2))
        return data

    def generate_patch(self) -> str:
        self.logger.info("[Pipeline] 🧠 Generating single patch candidate...")
        patch_file = (
            self.environment.output_path / f"{self.environment.instance_id}.patch.json"
        )

        def run_agent() -> str:
            patch_str = self.agent.generate_patch()

            if not patch_str.strip():
                raise ValueError("Agent returned an empty patch string.")

            return patch_str

        patch = self.generate(patch_file, run_agent, "single solution patch")
        return patch

    def run(self) -> dict:
        self.logger.info("[Pipeline] 🚀 Starting single-patch pipeline...")

        patch = self.generate_patch()
        self.logger.info("[Pipeline] ✅ Patch generated.")

        # 1. Write patch prediction file
        predictions_path = (
            self.environment.output_path
            / f"{self.problem.instance_id}.predictions.json"
        )

        predictions_path.write_text(
            json.dumps(
                [
                    {
                        "instance_id": self.problem.instance_id,
                        "model_patch": patch,
                        "model_name_or_path": self.config_agent.config_model.model_name,
                    }
                ],
                indent=2,
            )
        )

        # 2. Call SWE-bench locally with 'verified' dataset
        run_id = f"agent-eval-{uuid.uuid4().hex[:8]}"
        swebench_path = self.environment.swebench_path
        self.logger.info(
            f"[Pipeline] 📊 Evaluating with SWE-bench... (run_id={run_id})"
        )

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
                    self.problem.instance_id,
                    "--max_workers",
                    "1",
                    "--namespace",
                    "",
                    "--dataset_name",
                    "princeton-nlp/SWE-bench_Verified",  # ← FULL HF path
                    "--split",
                    "test",
                ],
                cwd=swebench_path,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(f"[Pipeline] ❌ SWE-bench evaluation failed:\n{e}")
            raise

        self.logger.info("[Pipeline] ✅ Evaluation completed.")

        expected_prefix = f"{self.config_agent.config_model.model_name}.{run_id}"
        report_candidates = list(Path(swebench_path).glob(f"{expected_prefix}.json"))
        if not report_candidates:
            raise FileNotFoundError(
                f"No SWE-bench report found for {expected_prefix}.json in {swebench_path}"
            )
        actual_report = report_candidates[0]
        final_report_path = self.environment.output_path / actual_report.name
        actual_report.replace(final_report_path)
        results = json.loads(final_report_path.read_text())
        self.logger.info(f"[Pipeline] 🗂️  Report moved to {final_report_path}")

        # ⛔ Diagnostics for unresolved instances
        instance_id = self.problem.instance_id
        instance_result = results.get("results", {}).get(instance_id, {})
        status = instance_result.get("status", "UNKNOWN")
        resolved = status == "RESOLVED"

        if not resolved:
            self.logger.warning(f"[Pipeline] ❌ Instance NOT resolved: {instance_id}")
            self.logger.info(f"🔍 Status: {status}")
            self.logger.info(f"📄 Patch:\n{patch.strip() or '[EMPTY PATCH]'}")

            traj_path = self.environment.output_path / f"{instance_id}.trajectory.jsonl"
            if traj_path.exists():
                self.logger.info(f"📍 Trajectory log available at: {traj_path}")
            else:
                self.logger.info(f"📍 No trajectory log found at: {traj_path}")

        else:
            self.logger.info("[Pipeline] ✅ Instance resolved successfully!")

        return {"patch": patch, "evaluation": results}


# EOF
