"""Validate and summarize a completed same-seed source-aligned Pion replay."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta

from .full_gate_executor import SCENARIOS
from .source_aligned_mc import SOURCE_FILES


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAN = ROOT / "results/pion_projection/full_gate_mc_20261119_v2_amendment_03"
DEFAULT_REPLAY = ROOT / "results/pion_projection/full_gate_amendment03_execution_01"
DEFAULT_PARENT = ROOT / "results/pion_projection/full_gate_amendment02_execution_01"
PRIMARY_FIELDS = ("status", "reference_accepted", "candidate_certified", "certificate_status")
DETERMINISTIC_FIELDS = PRIMARY_FIELDS + (
    "stage", "full_budget", "gate_parity", "max_abs_draw_difference",
    "n_draw_candidate_comparisons", "mutations",
)
RECEIPT_CODE_FILES = (
    "experiment.py", "identity.py", "joint.py", "reference.py", "statistics.py",
    "synthetic_adapter.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cp95(k: int, n: int) -> tuple[float, float]:
    lo = float(beta.ppf(0.025, k, n - k + 1)) if k else 0.0
    hi = float(beta.ppf(0.975, k + 1, n - k)) if k < n else 1.0
    return lo, hi


def load_rows(path: Path) -> list[dict]:
    value = json.loads(path.read_text())
    if value.get("physical_score") is not None:
        raise ValueError(f"physical_score must remain null: {path}")
    rows = value.get("rows")
    if not isinstance(rows, list):
        raise ValueError(f"missing rows: {path}")
    return rows


def validate_source_chain(plan: Path, replay: Path, rows: list[dict]) -> dict:
    prereg = json.loads((plan / "preregistration.json").read_text())
    executor = json.loads((plan / "executor_spec.json").read_text())
    frozen = json.loads((plan / "source_manifest.json").read_text())["hashes"]
    manifest_equal = prereg.get("code_sha256") == executor.get("code_hashes") == frozen
    current = {name: sha256(ROOT / "tasks/pion_projection" / name) for name in SOURCE_FILES}
    mismatches = sorted(name for name, digest in frozen.items() if current.get(name) != digest)
    launch = json.loads((replay / "launch_validation.json").read_text())
    driver = json.loads((replay / "parallel_driver_spec.json").read_text())
    amendment_path = replay / "execution_amendment_01.json"
    amendment = json.loads(amendment_path.read_text()) if amendment_path.exists() else None
    receipt_mismatches = []
    current_receipt_hashes = {
        name: sha256(ROOT / "tasks/pion_projection" / name)
        for name in RECEIPT_CODE_FILES
    }
    for row in rows:
        recorded = row.get("code_sha256", {})
        for name in RECEIPT_CODE_FILES:
            if recorded.get(name) != current_receipt_hashes[name]:
                receipt_mismatches.append((row["scenario"], row["dataset"], name))
                break
    if not manifest_equal or mismatches:
        raise ValueError(f"source manifest mismatch: equal={manifest_equal}, files={mismatches}")
    if not launch.get("source_hashes_match") or not driver.get("source_hashes_match"):
        raise ValueError("launch or driver source-hash check did not pass")
    if launch.get("source_manifest_sha256") != sha256(plan / "source_manifest.json"):
        raise ValueError("launch validation refers to a different source manifest")
    if launch.get("preregistration_sha256") != sha256(plan / "preregistration.json"):
        raise ValueError("launch validation refers to a different preregistration")
    if launch.get("executor_spec_sha256") != sha256(plan / "executor_spec.json"):
        raise ValueError("launch validation refers to a different executor spec")
    if driver.get("plan_executor_spec_sha256") != sha256(plan / "executor_spec.json"):
        raise ValueError("parallel driver refers to a different executor spec")
    if driver.get("driver_sha256") != sha256(ROOT / "tasks/pion_projection/full_gate_parallel_driver.py"):
        raise ValueError("parallel driver source hash does not match current source")
    if amendment is not None:
        archived = replay / amendment["prior_parallel_driver_spec"]
        if not archived.exists() or sha256(archived) != amendment.get("prior_parallel_driver_spec_sha256"):
            raise ValueError("archived pre-resume driver spec hash is invalid")
        if int(driver.get("workers", 0)) != int(amendment.get("resumed_workers", -1)):
            raise ValueError("final driver worker count does not match the execution amendment")
    if receipt_mismatches:
        raise ValueError(f"receipt code hashes differ from current code: {receipt_mismatches[:5]}")
    return {
        "source_count": len(frozen),
        "manifest_sha256": sha256(plan / "source_manifest.json"),
        "preregistration_sha256": sha256(plan / "preregistration.json"),
        "executor_spec_sha256": sha256(plan / "executor_spec.json"),
        "manifest_equal": manifest_equal,
        "current_source_hashes_match": not mismatches,
        "launch_source_hashes_match": bool(launch.get("source_hashes_match")),
        "driver_source_hashes_match": bool(driver.get("source_hashes_match")),
        "receipt_core_hashes_match": not receipt_mismatches,
        "same_seed_as_amendment02": bool(executor.get("replay_relationship", "").startswith("same seed")),
        "workers_final": int(driver["workers"]),
        "execution_amendment": amendment,
    }


def pair_rows(parent_rows: list[dict], replay_rows: list[dict]) -> tuple[dict, list[dict]]:
    key = lambda row: (row["scenario"], int(row["dataset"]), int(row["seed"]))
    parent = {key(row): row for row in parent_rows}
    replay = {key(row): row for row in replay_rows}
    if set(parent) != set(replay):
        raise ValueError(f"dataset identity sets differ: parent={len(parent)}, replay={len(replay)}")
    if len(parent) != 2814:
        raise ValueError(f"expected 2814 paired worlds, got {len(parent)}")
    disagreements = []
    for identity in sorted(parent):
        left, right = parent[identity], replay[identity]
        changed = [field for field in DETERMINISTIC_FIELDS if left.get(field) != right.get(field)]
        if changed:
            disagreements.append({
                "scenario": identity[0], "dataset": identity[1], "seed": identity[2],
                "fields": changed,
                "amendment02": {field: left.get(field) for field in changed},
                "amendment03": {field: right.get(field) for field in changed},
            })
    by_scenario = {}
    for scenario in SCENARIOS:
        original = [row for row in parent.values() if row["scenario"] == scenario]
        replayed = [row for row in replay.values() if row["scenario"] == scenario]
        if len(original) != 402 or len(replayed) != 402:
            raise ValueError(f"{scenario} denominator differs from 402")
        fields = {}
        for field in ("reference_accepted", "candidate_certified"):
            fields[field] = {
                "amendment02_k": sum(bool(row.get(field)) for row in original),
                "amendment03_k": sum(bool(row.get(field)) for row in replayed),
            }
        fields["expected_rejection"] = {
            "amendment02_k": sum(row.get("status") == "EXPECTED_REJECTION" for row in original),
            "amendment03_k": sum(row.get("status") == "EXPECTED_REJECTION" for row in replayed),
        }
        fields["unexpected_execution_failure"] = {
            "amendment02_k": sum(
                row.get("status") not in ("PASS", "EXPECTED_REJECTION")
                or (bool(row.get("failure")) and row.get("status") != "EXPECTED_REJECTION")
                for row in original
            ),
            "amendment03_k": sum(
                row.get("status") not in ("PASS", "EXPECTED_REJECTION")
                or (bool(row.get("failure")) and row.get("status") != "EXPECTED_REJECTION")
                for row in replayed
            ),
        }
        fields["primary_field_disagreements"] = sum(
            any(parent[key(row)].get(field) != row.get(field) for field in PRIMARY_FIELDS)
            for row in replayed
        )
        fields["deterministic_field_disagreements"] = sum(
            any(parent[key(row)].get(field) != row.get(field) for field in DETERMINISTIC_FIELDS)
            for row in replayed
        )
        by_scenario[scenario] = fields
    return by_scenario, disagreements


def validate_receipts(replay_dir: Path, rows: list[dict]) -> dict:
    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status"))
        if status not in ("PASS", "EXPECTED_REJECTION"):
            raise ValueError(f"nonterminal or unexpected receipt status: {status}")
        status_counts[status] = status_counts.get(status, 0) + 1
        path = replay_dir / row["receipt"]
        if not path.is_file():
            raise ValueError(f"receipt file missing: {path}")
        if path.parents[1].name != f"dataset_{int(row['dataset']):04d}" or path.parents[2].name != row["scenario"]:
            raise ValueError(f"receipt path does not match row identity: {path}")
        receipt = json.loads(path.read_text())
        for field in ("scenario", "seed", "status", "code_sha256"):
            if receipt.get(field) != row.get(field):
                raise ValueError(f"receipt/summary mismatch for {field}: {path}")
        if receipt.get("physical_score") is not None:
            raise ValueError(f"physical_score must remain null in receipt: {path}")
    return {"receipt_count": len(rows), "status_counts": status_counts}


def compare_raw_inputs(parent_dir: Path, replay_dir: Path, parent_rows: list[dict], replay_rows: list[dict]) -> dict:
    key = lambda row: (row["scenario"], int(row["dataset"]), int(row["seed"]))
    parent = {key(row): row for row in parent_rows}
    replay = {key(row): row for row in replay_rows}
    if set(parent) != set(replay):
        raise ValueError("raw input pairing requires identical scenario/dataset/seed identities")
    mismatches = []
    for identity in sorted(parent):
        left_path = (parent_dir / parent[identity]["receipt"]).with_name("raw_inputs.npz")
        right_path = (replay_dir / replay[identity]["receipt"]).with_name("raw_inputs.npz")
        if not left_path.is_file() or not right_path.is_file():
            raise ValueError(f"raw input archive missing for {identity}")
        with np.load(left_path) as left, np.load(right_path) as right:
            if set(left.files) != set(right.files):
                mismatches.append({"scenario": identity[0], "dataset": identity[1], "reason": "archive keys differ"})
                continue
            changed = [
                name for name in left.files
                if left[name].shape != right[name].shape
                or left[name].dtype != right[name].dtype
                or not np.array_equal(left[name], right[name], equal_nan=True)
            ]
            if changed:
                mismatches.append({
                    "scenario": identity[0], "dataset": identity[1],
                    "reason": "raw array contents differ", "arrays": changed,
                })
    by_scenario = {
        scenario: sum(item["scenario"] == scenario for item in mismatches)
        for scenario in SCENARIOS
    }
    return {
        "n_paired_datasets": len(parent),
        "identical_raw_input_datasets": len(parent) - len(mismatches),
        "mismatching_raw_input_datasets": len(mismatches),
        "mismatches_by_scenario": by_scenario,
        "mismatch_examples": mismatches[:20],
    }


def make_figure(path: Path, scenario_summary: dict, disagreements: list[dict], raw_comparison: dict) -> None:
    scenarios = list(SCENARIOS)
    labels = [name.replace("_", "\n") for name in scenarios]
    short_labels = ["null", "known lower", "window mismatch", "reflection", "relative error", "wrong state", "nonfinite"]
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [2, 1.45]})
    x = np.arange(len(scenarios))
    width = 0.16
    panels = (
        ("reference_accepted", "Reference accepted"),
        ("candidate_certified", "Candidate certified"),
    )
    colors = ("#4477AA", "#CC6677")
    for index, (field, title) in enumerate(panels):
        offsets = (-width / 2, width / 2)
        for run_index, (run_name, offset) in enumerate(zip(("amendment02", "amendment03"), offsets)):
            counts = np.asarray([scenario_summary[s][field][run_name + "_k"] for s in scenarios])
            n = 402
            rates = counts / n
            intervals = np.asarray([cp95(int(k), n) for k in counts])
            axes[0].errorbar(
                x + index * 0.45 + offset, rates,
                yerr=np.vstack((rates - intervals[:, 0], intervals[:, 1] - rates)),
                fmt="o", capsize=3, color=colors[run_index],
                label=f"{title}: {run_name}", alpha=0.9,
            )
        axes[0].set_xticks(x + 0.225, labels, fontsize=8)
    axes[0].set_ylim(-0.04, 1.04)
    axes[0].set_ylabel("dataset fraction (marginal CP95)")
    axes[0].set_title("Outcome rates by scenario; the two runs use the same seeds")
    axes[0].grid(alpha=0.22)
    axes[0].legend(ncol=2, fontsize=8, loc="upper center")

    changed = np.zeros((len(scenarios), len(PRIMARY_FIELDS) + 1), dtype=int)
    for row in disagreements:
        index = scenarios.index(row["scenario"])
        for field in row["fields"]:
            if field in PRIMARY_FIELDS:
                changed[index, PRIMARY_FIELDS.index(field)] += 1
    for index, scenario in enumerate(scenarios):
        changed[index, -1] = raw_comparison["mismatches_by_scenario"][scenario]
    image = axes[1].imshow(changed, aspect="auto", cmap="Reds", vmin=0, vmax=max(1, int(changed.max())))
    axes[1].set_xticks(
        range(len(PRIMARY_FIELDS) + 1),
        [f"{field} changed" for field in PRIMARY_FIELDS] + ["raw inputs differ"],
        fontsize=8,
    )
    axes[1].set_yticks(range(len(scenarios)), short_labels, fontsize=8)
    axes[1].set_title("Paired outcome disagreements (count of same-seed datasets)")
    for i in range(changed.shape[0]):
        for j in range(changed.shape[1]):
            axes[1].text(j, i, str(changed[i, j]), ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=axes[1], shrink=0.8, label="datasets")
    fig.suptitle("Pion amendment03 source-aligned reproducibility replay", fontsize=14)
    fig.text(
        0.5, 0.01,
        "Same seeds as amendment02: marginal CP95 bars are descriptive only; do not pool runs or count them as independent MC evidence.",
        ha="center", fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    fig.savefig(path, dpi=170)
    plt.close(fig)


def write_reports(
    replay_dir: Path,
    source: dict,
    scenario_summary: dict,
    disagreements: list[dict],
    raw_comparison: dict,
) -> None:
    rows = []
    for scenario, values in scenario_summary.items():
        cert02 = values["candidate_certified"]["amendment02_k"]
        cert03 = values["candidate_certified"]["amendment03_k"]
        ref02 = values["reference_accepted"]["amendment02_k"]
        ref03 = values["reference_accepted"]["amendment03_k"]
        rej03 = values["expected_rejection"]["amendment03_k"]
        fail03 = values["unexpected_execution_failure"]["amendment03_k"]
        lo, hi = cp95(cert03, 402)
        rows.append(
            f"| `{scenario}` | {ref02}/402 | {ref03}/402 | {cert02}/402 | "
            f"{cert03}/402 | [{lo:.3f}, {hi:.3f}] | {rej03} | {fail03} | "
            f"{values['primary_field_disagreements']} | {values['deterministic_field_disagreements']} | "
            f"{values['raw_inputs_differ']} |"
        )
    summary = (
        "# Amendment03 source-aligned replay: analysis\n\n"
        "## 目的与样本关系\n\n"
        "此轮按 amendment02 的相同 seed、场景与 402/cell 设计重放当前代码，只用于检查来源 hash 闭合和同种子结果复现。"
        "相同 seed 标签本身不保证原始数组相同，因此下文另行逐 dataset 比较 development / validation arrays。无论数组是否完全一致，两轮都不是独立 Monte Carlo 样本；不得合并分子/分母、缩窄区间或称作独立复验。\n\n"
        "## 结果\n\n"
        "下表逐场景并列 amendment02 / amendment03 的参考接受数、候选认证数；CP95 只显示 amendment03 当前 replay 的单次边际二项区间。"
        "同 seed 配对差由图下方的字段不一致矩阵直接给出。EXPECTED_REJECTION 是计划中的输入拒绝，不计为意外执行失败。\n\n"
        "| 场景 | ref accept A02 | ref accept A03 | certified A02 | certified A03 | A03 cert CP95 | expected reject A03 | unexpected execution failure A03 | 主字段不一致 | 其他确定性字段不一致 | raw input 不一致 |\n"
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |\n"
        + "\n".join(rows)
        + "\n\n![Amendment03 same-seed source replay diagnostics](candidate_rates_diagnostic.png)\n\n"
        "## 来源核验与限制\n\n"
        f"- Frozen source manifest 包含 {source['source_count']} 个文件；preregistration、executor spec 与 manifest 内容相同。\n"
        f"- 当前源文件、launch validation、parallel driver spec 与逐例 receipt 中的核心代码 hash 均匹配：{source['current_source_hashes_match']}。\n"
        f"- 三个 plan artifact 的 SHA256：manifest `{source['manifest_sha256']}`，preregistration `{source['preregistration_sha256']}`，executor `{source['executor_spec_sha256']}`。\n"
        f"- amendment03 与 amendment02 使用同一 seed：{source['same_seed_as_amendment02']}；primary outcome differences：{sum(v['primary_field_disagreements'] for v in scenario_summary.values())}/2814，other deterministic field differences：{sum(v['deterministic_field_disagreements'] for v in scenario_summary.values())}/2814。\n"
        f"- Same-seed raw inputs exact comparison: {raw_comparison['identical_raw_input_datasets']}/{raw_comparison['n_paired_datasets']} datasets match across `development` and `validation`; mismatches by scenario: `{raw_comparison['mismatches_by_scenario']}`.\n"
        f"- 执行并发最终为 {source['workers_final']} workers；6-worker 到 10-worker 的断点调整及保留的旧配置见 `execution_amendment_01.json` / `parallel_driver_spec_workers06.json`。并发只改变 walltime 和 receipt elapsed time，不改变每条 seed 的生成规则、输入或评分代码。\n"
        f"- Receipt 审计：{source['receipt_count']} 个 receipt 文件均存在并与汇总行一致；status 计数 `{source['receipt_status_counts']}`。`physical_score` 保持 null；本实验不含物理 gauge data、独立 anchor、真实相关函数、GPU/MPI 执行或 production calibration。\n"
        "- amendment02 原先的高层 prereg adapter hash 冲突仍然是历史事实；本轮为新 plan 下的 source-aligned replay，不能回写或修复旧 receipt 的来源链。\n"
    )
    (replay_dir / "ANALYSIS.md").write_text(summary)
    review = (
        "# Amendment03 source-aligned replay: run review\n\n"
        "Status: complete synthetic reproducibility/source audit; not a new independent calibration.\n\n"
        "## Acceptance checks\n\n"
        f"- Expected and observed worlds: 2814 (7 scenarios × 402); all same-seed identities matched amendment02.\n"
        f"- Plan manifest closure: {source['manifest_equal']}; current source bytes match frozen hashes: {source['current_source_hashes_match']}.\n"
        f"- Launch / driver frozen-source checks: {source['launch_source_hashes_match']} / {source['driver_source_hashes_match']}.\n"
        f"- Receipt core-code hash check: {source['receipt_core_hashes_match']}; expected-rejection receipts remain distinct from execution failures.\n"
        f"- Execution used {source['workers_final']} workers after a recorded resume from 6; the original driver spec is retained at `parallel_driver_spec_workers06.json`, with the change documented in `execution_amendment_01.json`.\n"
        f"- Receipt files audited: {source['receipt_count']}; terminal statuses: `{source['receipt_status_counts']}`.\n"
        f"- Primary outcome field disagreements across same-seed records: {sum(v['primary_field_disagreements'] for v in scenario_summary.values())}; all deterministic-field disagreements: {sum(v['deterministic_field_disagreements'] for v in scenario_summary.values())}.\n"
        f"- Exact raw input array comparisons: {raw_comparison['identical_raw_input_datasets']}/{raw_comparison['n_paired_datasets']} datasets match; mismatches by scenario: `{raw_comparison['mismatches_by_scenario']}`.\n"
        "- No physical score was generated; `physical_score=null`.\n\n"
        "## Interpretation\n\n"
        "A matching same-seed replay establishes that this new frozen source manifest can reproduce the recorded synthetic path to the extent captured by its receipts. "
        "It does not add independent MC information and must not be pooled with amendment02. The old amendment02 preregistration/executor hash discrepancy remains unresolved because the original source bytes were unavailable; this run does not retroactively repair it. "
        "The next scientific gate is an independently identified physical anchor / production measurement, which remains NOT_RUN without GPU/cluster inputs.\n"
    )
    (replay_dir / "RUN_REVIEW.md").write_text(review)
    (replay_dir / "README.md").write_text(
        "# Amendment03 source-aligned replay\n\n"
        "Status: COMPLETE; 2814/2814 synthetic worlds executed with the amendment02 seed set. "
        "This is a same-seed provenance/reproducibility audit and not independent Monte Carlo evidence.\n\n"
        "Read [analysis](ANALYSIS.md), [run review](RUN_REVIEW.md), and the [candidate-rate and replay-concordance figure](candidate_rates_diagnostic.png). "
        "The frozen [amendment03 plan](../full_gate_mc_20261119_v2_amendment_03/README.md) remains separate from these execution outputs. "
        "A concurrency-only resume is documented in [execution_amendment_01.json](execution_amendment_01.json); analysis artifact hashes are recorded in [analysis_provenance.json](analysis_provenance.json). "
        "The post-run checker is [source_aligned_replay_summary.py](../../../tasks/pion_projection/source_aligned_replay_summary.py). "
        "The original amendment02 source-chain classification remains `PARTIAL`; this new replay does not rewrite its receipts. `physical_score=null`.\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--parent", type=Path, default=DEFAULT_PARENT)
    args = parser.parse_args()
    replay_aggregate = json.loads((args.replay / "aggregate.json").read_text())
    parent_aggregate = json.loads((args.parent / "aggregate.json").read_text())
    if replay_aggregate.get("status") != "COMPLETE" or replay_aggregate.get("n_executed") != 2814:
        raise ValueError("source-aligned replay is not complete at 2814/2814")
    if replay_aggregate.get("n_planned") != 2814 or replay_aggregate.get("physical_score") is not None:
        raise ValueError("replay aggregate planned count or physical_score is invalid")
    if parent_aggregate.get("status") != "COMPLETE" or parent_aggregate.get("n_executed") != 2814:
        raise ValueError("parent amendment02 is not a complete 2814-world run")
    if parent_aggregate.get("n_planned") != 2814 or parent_aggregate.get("physical_score") is not None:
        raise ValueError("parent aggregate planned count or physical_score is invalid")
    replay_plan = json.loads((args.plan / "preregistration.json").read_text())
    replay_executor = json.loads((args.plan / "executor_spec.json").read_text())
    parent_plan_dir = args.parent.parent / "full_gate_mc_20261119_v2_amendment_02"
    parent_plan = json.loads((parent_plan_dir / "preregistration.json").read_text())
    if replay_plan.get("seed") != parent_plan.get("seed"):
        raise ValueError("amendment02 and amendment03 seed bases differ")
    if replay_plan.get("scenarios") != parent_plan.get("scenarios"):
        raise ValueError("amendment02 and amendment03 scenario lists differ")
    if replay_plan.get("scenarios") != list(SCENARIOS) or replay_executor.get("scenarios") != list(SCENARIOS):
        raise ValueError("frozen plans and current scenario implementation differ")
    if replay_plan.get("mc_target", {}).get("n_independent_datasets_per_cell") != 402:
        raise ValueError("replay plan does not freeze 402 independent datasets per cell")
    if replay_executor.get("n_per_cell") != 402:
        raise ValueError("executor does not target 402 datasets per cell")
    replay_rows = load_rows(args.replay / "dataset_results.json")
    parent_rows = load_rows(args.parent / "dataset_results.json")
    if len(replay_rows) != 2814:
        raise ValueError(f"expected 2814 replay rows, got {len(replay_rows)}")
    base_seed = int(replay_plan["seed"])
    for row in replay_rows:
        expected_seed = base_seed + SCENARIOS.index(row["scenario"]) * 100_000 + int(row["dataset"])
        if int(row["seed"]) != expected_seed:
            raise ValueError(f"seed does not match frozen rule: {row['scenario']}/{row['dataset']}")
    source = validate_source_chain(args.plan, args.replay, replay_rows)
    receipt_audit = validate_receipts(args.replay, replay_rows)
    source["receipt_count"] = receipt_audit["receipt_count"]
    source["receipt_status_counts"] = receipt_audit["status_counts"]
    scenario_summary, disagreements = pair_rows(parent_rows, replay_rows)
    raw_comparison = compare_raw_inputs(args.parent, args.replay, parent_rows, replay_rows)
    for scenario in SCENARIOS:
        scenario_summary[scenario]["raw_inputs_differ"] = raw_comparison["mismatches_by_scenario"][scenario]
    make_figure(args.replay / "candidate_rates_diagnostic.png", scenario_summary, disagreements, raw_comparison)
    write_reports(args.replay, source, scenario_summary, disagreements, raw_comparison)
    primary_difference_count = sum(v["primary_field_disagreements"] for v in scenario_summary.values())
    deterministic_difference_count = sum(v["deterministic_field_disagreements"] for v in scenario_summary.values())
    provenance = {
        "schema": "pion-source-aligned-replay-analysis-provenance-v1",
        "analysis_script_path": str(Path(__file__).resolve().relative_to(ROOT)),
        "analysis_script_sha256": sha256(Path(__file__).resolve()),
        "source_manifest_sha256": sha256(args.plan / "source_manifest.json"),
        "preregistration_sha256": sha256(args.plan / "preregistration.json"),
        "executor_spec_sha256": sha256(args.plan / "executor_spec.json"),
        "parent_aggregate_sha256": sha256(args.parent / "aggregate.json"),
        "parent_dataset_results_sha256": sha256(args.parent / "dataset_results.json"),
        "replay_aggregate_sha256": sha256(args.replay / "aggregate.json"),
        "replay_dataset_results_sha256": sha256(args.replay / "dataset_results.json"),
        "analysis_sha256": sha256(args.replay / "ANALYSIS.md"),
        "run_review_sha256": sha256(args.replay / "RUN_REVIEW.md"),
        "plot_sha256": sha256(args.replay / "candidate_rates_diagnostic.png"),
        "execution_amendment_sha256": sha256(args.replay / "execution_amendment_01.json") if (args.replay / "execution_amendment_01.json").exists() else None,
        "n_same_seed_worlds": 2814,
        "receipt_audit": receipt_audit,
        "raw_input_comparison": raw_comparison,
        "primary_outcome_disagreements": primary_difference_count,
        "deterministic_field_disagreements": deterministic_difference_count,
        "independent_mc_sample": False,
        "physical_score": None,
    }
    (args.replay / "analysis_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": "COMPLETE",
        "n_rows": len(replay_rows),
        "source": source,
        "paired_primary_field_disagreements": primary_difference_count,
        "deterministic_field_disagreements": deterministic_difference_count,
        "output": str(args.replay),
    }, indent=2))


if __name__ == "__main__":
    main()
