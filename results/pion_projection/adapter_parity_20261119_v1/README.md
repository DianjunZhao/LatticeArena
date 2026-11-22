# Synthetic文件入口adapter parity

{
  "schema": "pion-synthetic-adapter-v1",
  "synthetic": true,
  "physical_score": null,
  "status": "PASS",
  "mutations": {
    "submission_protocol": {
      "rejected": true,
      "reason": "submission protocol hash does not match the run protocol; validation report submission hash differs from the submission file"
    },
    "reference_identity": {
      "rejected": true,
      "reason": "reference implementation hash is missing or inconsistent; validation report submission hash differs from the submission file; validation report reference spec differs from the submission"
    },
    "gate_identity": {
      "rejected": true,
      "reason": "validation report submission hash differs from the submission file"
    },
    "report_identity": {
      "rejected": true,
      "reason": "validation report data hash differs from validation.npz"
    },
    "late_metric": {
      "rejected": true,
      "reason": "validation report submission hash differs from the submission file"
    }
  },
  "max_abs_draw_difference": 0.0,
  "n_draw_candidate_comparisons": 12,
  "gate_parity": true,
  "certificate_status": "certified",
  "code_sha256": {
    "synthetic_adapter.py": "b7e95345e1374869d33299a5f0fa4fab1b6581174834878e233712eda0ed7249",
    "experiment.py": "0aee2035d1de3651de3a278bd222e5218ec80c496296a1ba48aaaac4d6135842",
    "joint.py": "bad510d05437c74ae3612ae923cbb8e616cc409c2a61c8d1f8c19a33f56216bb",
    "identity.py": "0de741940b935b1e56f457618e13ce543ec3edca6ac358716c2f17c535078eab",
    "statistics.py": "69cda40c0f997a29179f1941388a90ea68d7f059ec686226b37a87bffc77d0e5",
    "reference.py": "153675ba921fda9f339342694ba7b84426a8a96f892b049a7bec060f85c0eb4a"
  }
}

输入为120开发/60验证synthetic配置；4 outer×8 inner只验程序一致性，不是MC校准。真实develop→evaluate→joint调用improvement_certificate；直接helper使用保存的全部共同索引逐draw复算，不另写gate。protocol通过common.PROTOCOL_PATH临时绑定至新run，未mock算法/认证。生产输出可能含条件score，该run是synthetic，physical_score始终null，不作物理排名。

每项mutation仅改本目录文件并恢复原始bytes；记录明确拒绝原因。主402/cell MC未执行。若BLOCKED则查看execution.log与blocker，不伪造结果。

## 验收读数与故障解释

| 检查 | 实测 |
|---|---|
| 真实文件入口 | develop → evaluate → joint → improvement_certificate 全部运行 |
| 逐draw比较 | 4 draws × 3 candidates=12项，最大绝对差0 |
| 完整生产gate与直接helper | 同一seed、bootstrap预算，passed一致 |
| submission protocol变化 | 拒绝protocol及report→submission绑定 |
| reference实现hash变化 | 拒绝实现身份及report reference绑定 |
| gate artifact变化 | 拒绝report→submission内容hash绑定 |
| report validation hash变化 | 拒绝report→data绑定 |
| late metric变化 | 拒绝report→submission内容hash绑定 |

最后两类submission内部mutation首先被外层内容hash拒绝；本实验不声称已隔离验证“同时伪造全部receipt”的对抗场景。合法conditional certificate状态为certified，只是程序可到达性（outer4），不代表足够统计证据，更不是physical认证。

新回归 `tests/test_pion_synthetic_adapter.py`：1 passed（0.71s）。402/cell主MC仍NOT_RUN。重新执行请用全新 `--dest`，例如 `PYTHONDONTWRITEBYTECODE=1 python -B -m tasks.pion_projection.synthetic_adapter --dest results/pion_projection/adapter_parity_<fresh_id>`。
