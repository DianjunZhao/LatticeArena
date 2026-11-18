"""Write REPORT.md: a code-generated top-3 table plus LLM commentary."""
import json
from pathlib import Path

from agents.llm import chat

PROMPT = """You are interpreting a lattice-QCD benchmark result. Numbers below were computed by code; do not invent numbers.

Reference status: {status}
Failure reasons: {reasons}

Top candidates (risk = uncertainty term + departure term, lower is better; ratio is risk_local/risk_candidate):
{table}

Write 3-5 short bullets in Chinese explaining: (1) where the candidates differ, (2) the likely physics (excited-state contamination, smearing, signal-to-noise), (3) what to try next. Do not claim SOTA or a discovery. Return JSON only: {{"markdown": "..."}}"""


def run(output, model):
    output = Path(output)
    report = json.loads((output / 'validation_results.json').read_text())
    rows = [(name, value) for name, value in report['results'].items() if value.get('risk') is not None]
    rows.sort(key=lambda row: row[1]['risk'])
    table = '\n'.join(
        f"| {i + 1} | {name} | {value['risk']:.6g} | {value['variance']:.4g} | "
        f"{value['departure_squared']:.4g} | {value.get('diagnostic_loss_ratio_vs_local', '—')} | "
        f"{value.get('risk_95_interval')} |"
        for i, (name, value) in enumerate(rows[:3]))
    text = json.loads(chat(PROMPT.format(status=report['reference_passed'],
                                         reasons=report['reference_failure_reasons'],
                                         table=table), model))['markdown']

    (output / 'REPORT.md').write_text(
        f"# 结果解读\n\n"
        f"> 数字由代码从 `validation_results.json` 生成；下面的「LLM 解读」是模型叙述，不是证据。\n\n"
        f"## 参考状态\n\n- reference_passed: `{report['reference_passed']}`\n"
        f"- 失败原因：{report['reference_failure_reasons']}\n"
        f"- 分数状态：`{report['score_status']}`（参考未通过时所有 score 为 null）\n\n"
        f"## 前三名（按 risk 排序）\n\n"
        f"| 排名 | 候选 | risk | 方差项 | 偏离项 | 相对 local | 95% 区间 |\n"
        f"| --- | --- | ---: | ---: | ---: | ---: | --- |\n{table}\n\n"
        f"## LLM 解读（非权威）\n\n{text}\n")
    print(f'wrote {output / "REPORT.md"}')
