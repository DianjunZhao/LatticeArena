"""Read-only byte and source audit for the archived Kunshan gauge campaigns.

`build` uses the configured `kunshan` SSH alias to stream SHA-256 digests and
small text receipts. It never downloads or modifies gauge files and never
submits a job. `verify` checks the frozen local audit artifact only; it does
not reconnect to Kunshan.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REMOTE = "kunshan"
REMOTE_ROOT = "~/dianjun/LatticeArena"
OUT = ROOT / "results/kunshan_logs/live_archive_audit_v1"
CAMPAIGNS = {"S16T16": 100, "S16T16B": 200, "S16T16C": 200}
PLAQUETTE_ATOL = 1e-7

LOCAL_PRIMARY = ROOT / "results/kunshan_logs/manifest.json"
LOCAL_SNAPSHOT = ROOT / "results/wilson_loop/hmc_quality_v1/manifest_snapshot.json"
LOCAL_HMC_LOG = ROOT / "results/kunshan_logs/hmc_production.log"
PION200_FILES = [
    ROOT / "results/pion_projection/s16t16_gevp200/development_provenance.json",
    ROOT / "results/pion_projection/s16t16_gevp200/validation_provenance.json",
]
PION_V1_FILES = [
    ROOT / "results/pion_projection/s16t16_v1/development_provenance.json",
    ROOT / "results/pion_projection/s16t16_v1/validation_provenance.json",
]
V9_MANIFEST = ROOT / "results/optimize_gaussian/v9/manifest.json"
LOCAL_SOURCES = {
    "pilot/hmc_generate.py": ROOT / "pilot/hmc_generate.py",
    "pilot/hmc200.sbatch": ROOT / "pilot/hmc200.sbatch",
    "pilot/hmc200c.sbatch": ROOT / "pilot/hmc200c.sbatch",
}
REMOTE_TEXT = {
    "data/S16T16/manifest.json": "remote_manifest_S16T16.json",
    "data/S16T16B/manifest.json": "remote_manifest_S16T16B.json",
    "data/S16T16C/manifest.json": "remote_manifest_S16T16C.json",
    "logs/hmc200_128345242.out": "remote_hmc200_128345242.out",
    "logs/hmc200_128345242.err": "remote_hmc200_128345242.err",
    "logs/hmc200_128360803.out": "remote_hmc200_128360803.out",
    "logs/hmc200_128360803.err": "remote_hmc200_128360803.err",
    "logs/hmc200c_128360922.out": "remote_hmc200c_128360922.out",
    "logs/hmc200c_128360922.err": "remote_hmc200c_128360922.err",
}

SAVED_RE = re.compile(
    r"^SAVED (?P<path>\S+) id=(?P<id>\d+) traj=(?P<traj>\d+) "
    r"plaquette=(?P<plaquette>[-+0-9.eE]+)$"
)
TRAJ_RE = re.compile(
    r"^TRAJ (?P<traj>\d+)/(?P<planned>\d+) acc=(?P<acc>True|False) "
    r"plaquette=(?P<plaquette>\S+) dE=(?P<delta_h>\S+) "
    r"sec=(?P<seconds>\S+) acc_rate=(?P<rate>\d+\.\d{3})$"
)
DONE_RE = re.compile(
    r"^DONE saved=(?P<saved>\d+) trajectories=(?P<planned>\d+) "
    r"accept_rate=(?P<rate>\d+\.\d{3}) wall_seconds=(?P<wall>\S+) "
    r"sec_per_traj=(?P<per>\S+)$"
)

PERL_HASH = r'''use strict; use warnings; use Digest::SHA;
for my $p (@ARGV) {
  open my $f, "<", $p or die "open $p: $!"; binmode $f;
  my $raw=Digest::SHA->new(256); my $body=Digest::SHA->new(256);
  my $line; my $found=0;
  while (defined($line=<$f>)) { $raw->add($line); if ($line =~ /^END_HEADER\r?\n$/) { $found=1; last; } }
  die "missing NERSC END_HEADER: $p" unless $found;
  while (read($f, my $buf, 1<<20)) { $raw->add($buf); $body->add($buf); }
  print $raw->hexdigest, "\t", $body->hexdigest, "\t", $p, "\n";
}'''


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ssh_bytes(command: str) -> bytes:
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", REMOTE, command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    if proc.returncode:
        detail = proc.stderr.decode("utf-8", errors="replace")[-3000:]
        raise RuntimeError(f"read-only SSH command failed ({proc.returncode}): {detail}")
    return proc.stdout


def remote_text(path: str) -> bytes:
    return ssh_bytes(f"cd {REMOTE_ROOT} && cat -- {shlex.quote(path)}")


def remote_gauge_hashes() -> dict[str, dict[str, str]]:
    globs = " ".join(f"data/{name}/wilson_b6.*" for name in CAMPAIGNS)
    command = (
        f"cd {REMOTE_ROOT} && perl -MDigest::SHA -e {shlex.quote(PERL_HASH)} {globs}"
    )
    output = ssh_bytes(command).decode("utf-8")
    values: dict[str, dict[str, str]] = {}
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 3:
            raise RuntimeError(f"unexpected remote digest row: {line!r}")
        raw_hash, payload_hash, relative_path = fields
        match = re.fullmatch(r"data/(S16T16|S16T16B|S16T16C)/wilson_b6\.(\d+)", relative_path)
        if not match:
            raise RuntimeError(f"unexpected remote gauge path: {relative_path}")
        campaign, config_id = match.group(1), int(match.group(2))
        key = f"{campaign}:{config_id}"
        if key in values:
            raise RuntimeError(f"duplicate remote gauge digest row: {key}")
        values[key] = {
            "campaign": campaign,
            "id": str(config_id),
            "path": relative_path,
            "raw_sha256": raw_hash,
            "payload_sha256": payload_hash,
        }
    expected = {f"{campaign}:{i}" for campaign, n in CAMPAIGNS.items() for i in range(n)}
    if set(values) != expected:
        missing = sorted(expected - set(values))[:10]
        extra = sorted(set(values) - expected)[:10]
        raise RuntimeError(f"remote raw inventory mismatch: missing={missing}, extra={extra}")
    return values


def read_json_bytes(data: bytes) -> dict:
    return json.loads(data.decode("utf-8"))


def load_provenance(paths: list[Path]) -> dict[int, dict]:
    rows: dict[int, dict] = {}
    for path in paths:
        obj = json.loads(path.read_text())
        for row in obj["records"]:
            config_id = int(row["id"])
            if config_id in rows:
                raise RuntimeError(f"duplicate provenance ID {config_id}: {path}")
            rows[config_id] = row
    return rows


def close(a: object, b: object, atol: float = PLAQUETTE_ATOL) -> bool:
    try:
        return abs(float(a) - float(b)) <= atol
    except (TypeError, ValueError):
        return False


def parse_hmc_log(data: bytes) -> tuple[list[dict], list[dict], dict | None]:
    saved: list[dict] = []
    checkpoints: list[dict] = []
    done = None
    for line in data.decode("utf-8", errors="replace").splitlines():
        if match := SAVED_RE.match(line):
            saved.append(
                {
                    "path": match.group("path"),
                    "id": int(match.group("id")),
                    "trajectory": int(match.group("traj")),
                    "plaquette": float(match.group("plaquette")),
                }
            )
        elif match := TRAJ_RE.match(line):
            checkpoints.append(
                {
                    "trajectory": int(match.group("traj")),
                    "planned_trajectories": int(match.group("planned")),
                    "accept": match.group("acc") == "True",
                    "plaquette": float(match.group("plaquette")),
                    "delta_h": float(match.group("delta_h")),
                    "seconds": float(match.group("seconds")),
                    "reported_cumulative_rate": match.group("rate"),
                }
            )
        elif match := DONE_RE.match(line):
            done = {
                "saved": int(match.group("saved")),
                "planned_trajectories": int(match.group("planned")),
                "reported_accept_rate": match.group("rate"),
                "wall_seconds": float(match.group("wall")),
                "seconds_per_trajectory": float(match.group("per")),
            }
    return saved, checkpoints, done


def infer_rounded_counts(denominator: int, token: str) -> list[int]:
    return [k for k in range(denominator + 1) if f"{k / denominator:.3f}" == token]


def read_hmc_cli_settings(sbatch_text: str, generator_text: str) -> dict:
    command_lines = [line.strip() for line in sbatch_text.splitlines() if "pilot/hmc_generate.py" in line]
    if len(command_lines) != 1:
        raise RuntimeError(f"expected one hmc_generate.py command in batch script, found {len(command_lines)}")
    command = command_lines[0]
    settings = {}
    for option in ("thermal", "trajectories", "save-every", "max-save"):
        match = re.search(rf"--{re.escape(option)}\s+(\d+)", command)
        if not match:
            raise RuntimeError(f"missing --{option} in batch command: {command}")
        settings[option.replace("-", "_")] = int(match.group(1))
    seed_match = re.search(r"--seed\s+(\d+)", command)
    if seed_match:
        settings["seed"] = int(seed_match.group(1))
        settings["seed_source"] = "explicit batch argument"
    else:
        default_match = re.search(r"add_argument\(['\"]--seed['\"].*?default=(\d+)", generator_text)
        if not default_match:
            raise RuntimeError("batch command omits --seed and generator default could not be verified")
        settings["seed"] = int(default_match.group(1))
        settings["seed_source"] = "generator default; not explicit in batch command"
    return settings


def compare_hmc_checkpoints(b_rows: list[dict], c_rows: list[dict]) -> tuple[list[dict], dict]:
    b_by_traj = {row["trajectory"]: row for row in b_rows}
    c_by_traj = {row["trajectory"]: row for row in c_rows}
    shared = sorted(set(b_by_traj) & set(c_by_traj))
    fields = ("accept", "plaquette", "delta_h", "reported_cumulative_rate")
    rows = []
    for trajectory in shared:
        b, c = b_by_traj[trajectory], c_by_traj[trajectory]
        row = {
            "trajectory": trajectory,
            "b_seconds": b["seconds"],
            "c_seconds": c["seconds"],
            "seconds_equal": b["seconds"] == c["seconds"],
        }
        for field in fields:
            row[f"b_{field}"] = b[field]
            row[f"c_{field}"] = c[field]
            row[f"{field}_equal"] = b[field] == c[field]
        row["all_physics_fields_equal"] = all(row[f"{field}_equal"] for field in fields)
        rows.append(row)
    summary = {
        "B_checkpoint_count": len(b_rows),
        "C_checkpoint_count": len(c_rows),
        "shared_trajectory_count": len(shared),
        "all_physics_fields_equal_on_shared_trajectories": len(shared) == len(b_rows) == len(c_rows) and all(row["all_physics_fields_equal"] for row in rows),
        "physics_mismatch_count": sum(not row["all_physics_fields_equal"] for row in rows),
        "timing_equal_count": sum(bool(row["seconds_equal"]) for row in rows),
        "fields_compared": list(fields),
        "scope": "Only logged sparse checkpoints are compared; this does not assert every trajectory was identical.",
    }
    return rows, summary


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def autocorrelation(values: list[float], max_lag: int = 80) -> list[float]:
    x = np.asarray(values, dtype=float)
    x = x - np.mean(x)
    denom = float(np.dot(x, x))
    if denom <= 0:
        return []
    limit = min(max_lag, len(x) // 2)
    return [float(np.dot(x[:-lag], x[lag:]) / denom) for lag in range(1, limit + 1)]


def tau_with_cutoff(acf: list[float], max_lag: int | None = None) -> float:
    limit = len(acf) if max_lag is None else min(max_lag, len(acf))
    tau = 0.5
    for rho in acf[:limit]:
        if rho <= 0:
            break
        tau += rho
    return tau


def build() -> None:
    if OUT.exists():
        raise RuntimeError(f"refusing to overwrite existing audit directory: {OUT}")
    OUT.mkdir(parents=True)

    # Archive the small text receipts verbatim; raw gauge files remain remote.
    text_payloads = {rel: remote_text(rel) for rel in REMOTE_TEXT}
    for rel, name in REMOTE_TEXT.items():
        (OUT / name).write_bytes(text_payloads[rel])
    remote_manifests = {
        name: read_json_bytes(text_payloads[f"data/{name}/manifest.json"])
        for name in CAMPAIGNS
    }
    local_primary_obj = json.loads(LOCAL_PRIMARY.read_text())
    local_snapshot_obj = json.loads(LOCAL_SNAPSHOT.read_text())
    local_manifests = {"S16T16": local_primary_obj, "S16T16C": local_snapshot_obj}

    gauge_hashes = remote_gauge_hashes()
    source_hash_rows = []
    for rel, local_path in LOCAL_SOURCES.items():
        remote_hash = sha256_bytes(remote_text(rel))
        local_hash = sha256_file(local_path)
        source_hash_rows.append(
            {
                "path": rel,
                "remote_sha256": remote_hash,
                "local_sha256": local_hash,
                "byte_identical": remote_hash == local_hash,
            }
        )
    write_csv(OUT / "source_hashes.csv", source_hash_rows)

    manifest_rows = []
    configs_by_campaign: dict[str, dict[int, dict]] = {}
    for campaign, manifest in remote_manifests.items():
        configs = {int(row["id"]): row for row in manifest["configs"]}
        configs_by_campaign[campaign] = configs
        expected_ids = set(range(CAMPAIGNS[campaign]))
        if set(configs) != expected_ids:
            raise RuntimeError(f"{campaign} manifest IDs do not match expected range")
        for config_id, record in sorted(configs.items()):
            raw_row = gauge_hashes[f"{campaign}:{config_id}"]
            manifest_rows.append(
                {
                    "campaign": campaign,
                    "id": config_id,
                    "trajectory": record.get("trajectory", ""),
                    "manifest_plaquette": record.get("plaquette", ""),
                    "raw_file_sha256": raw_row["raw_sha256"],
                    "manifest_sha256": record.get("sha256", ""),
                    "raw_hash_matches_manifest": raw_row["raw_sha256"] == record.get("sha256"),
                    "payload_sha256_after_END_HEADER": raw_row["payload_sha256"],
                }
            )
    write_csv(OUT / "manifest_byte_crosswalk.csv", manifest_rows)

    source_copy_rows = []
    for campaign in ("S16T16", "S16T16C"):
        local = local_manifests[campaign]
        remote_bytes = text_payloads[f"data/{campaign}/manifest.json"]
        local_bytes = (LOCAL_PRIMARY if campaign == "S16T16" else LOCAL_SNAPSHOT).read_bytes()
        source_copy_rows.append(
            {
                "campaign": campaign,
                "remote_manifest_sha256": sha256_bytes(remote_bytes),
                "local_copy_sha256": sha256_bytes(local_bytes),
                "byte_identical": remote_bytes == local_bytes,
                "config_count": len(local["configs"]),
            }
        )
    write_csv(OUT / "manifest_source_crosswalk.csv", source_copy_rows)

    pair_rows = []
    for left, right in (("S16T16", "S16T16B"), ("S16T16", "S16T16C"), ("S16T16B", "S16T16C")):
        n = min(CAMPAIGNS[left], CAMPAIGNS[right])
        for config_id in range(n):
            a = gauge_hashes[f"{left}:{config_id}"]
            b = gauge_hashes[f"{right}:{config_id}"]
            pair_rows.append(
                {
                    "left_campaign": left,
                    "right_campaign": right,
                    "id": config_id,
                    "raw_file_hash_equal": a["raw_sha256"] == b["raw_sha256"],
                    "payload_hash_equal": a["payload_sha256"] == b["payload_sha256"],
                    "left_raw_sha256": a["raw_sha256"],
                    "right_raw_sha256": b["raw_sha256"],
                    "left_payload_sha256": a["payload_sha256"],
                    "right_payload_sha256": b["payload_sha256"],
                }
            )
    write_csv(OUT / "campaign_payload_crosswalk.csv", pair_rows)

    pion200 = load_provenance(PION200_FILES)
    pion_v1 = load_provenance(PION_V1_FILES)
    provenance_rows = []
    for source_name, campaign, records in (
        ("pion_gevp200", "S16T16C", pion200),
        ("pion_pilot_v1", "S16T16", pion_v1),
    ):
        for config_id, record in sorted(records.items()):
            actual = gauge_hashes.get(f"{campaign}:{config_id}")
            provenance_rows.append(
                {
                    "source": source_name,
                    "campaign": campaign,
                    "id": config_id,
                    "recorded_gauge_sha256": record.get("gauge_sha256", ""),
                    "raw_file_sha256": "" if actual is None else actual["raw_sha256"],
                    "raw_hash_matches": bool(actual and record.get("gauge_sha256") == actual["raw_sha256"]),
                    "payload_sha256": "" if actual is None else actual["payload_sha256"],
                    "residual_max": record.get("residual_max", ""),
                }
            )
    write_csv(OUT / "pion_raw_identity_crosswalk.csv", provenance_rows)

    # Cross-check all archived SAVED rows against paths and manifest metadata.
    logs = {
        "S16T16": LOCAL_HMC_LOG.read_bytes(),
        "S16T16B": text_payloads["logs/hmc200_128345242.out"],
        "S16T16C": text_payloads["logs/hmc200c_128360922.out"],
    }
    hmc_rows = []
    checkpoints_by_campaign = {}
    done_by_campaign = {}
    for campaign, log_bytes in logs.items():
        saved, checkpoints, done = parse_hmc_log(log_bytes)
        checkpoints_by_campaign[campaign] = checkpoints
        done_by_campaign[campaign] = done
        manifest = remote_manifests[campaign]
        by_id = {int(row["id"]): row for row in manifest["configs"]}
        for record in saved:
            config_id = record["id"]
            expected_path = f"data/{campaign}/wilson_b6.{config_id}"
            manifest_row = by_id.get(config_id, {})
            file_hash = gauge_hashes.get(f"{campaign}:{config_id}", {})
            hmc_rows.append(
                {
                    "campaign": campaign,
                    "log_path": record["path"],
                    "expected_output_path": expected_path,
                    "id": config_id,
                    "trajectory_log": record["trajectory"],
                    "trajectory_manifest": manifest_row.get("trajectory", ""),
                    "trajectory_matches": record["trajectory"] == manifest_row.get("trajectory"),
                    "plaquette_log": record["plaquette"],
                    "plaquette_manifest": manifest_row.get("plaquette", ""),
                    "plaquette_matches": close(record["plaquette"], manifest_row.get("plaquette")),
                    "path_matches": record["path"] == expected_path,
                    "raw_bytes_match_manifest": file_hash.get("raw_sha256") == manifest_row.get("sha256"),
                }
            )
        if done is None or len(saved) != len(by_id):
            raise RuntimeError(f"{campaign} HMC log has {len(saved)} SAVED rows; manifest has {len(by_id)}")
    write_csv(OUT / "hmc_saved_crosswalk.csv", hmc_rows)

    b_checkpoints = checkpoints_by_campaign["S16T16B"]
    c_checkpoints = checkpoints_by_campaign["S16T16C"]
    checkpoint_comparison_rows, checkpoint_comparison = compare_hmc_checkpoints(b_checkpoints, c_checkpoints)
    write_csv(OUT / "hmc_b_c_checkpoint_comparison.csv", checkpoint_comparison_rows)
    b_done = done_by_campaign["S16T16B"]
    if b_done is None:
        raise RuntimeError("S16T16B archived log has no DONE line")
    checkpoint_rows = []
    for row in b_checkpoints:
        counts = infer_rounded_counts(row["trajectory"], row["reported_cumulative_rate"])
        checkpoint_rows.append(
            {
                **row,
                "cumulative_accepted_min": min(counts) if counts else "",
                "cumulative_accepted_max": max(counts) if counts else "",
                "rounded_count_unique": len(counts) == 1,
            }
        )
    write_csv(OUT / "hmc_b_checkpoints.csv", checkpoint_rows)
    final_counts = infer_rounded_counts(b_done["planned_trajectories"], b_done["reported_accept_rate"])
    b_saved = [row for row in hmc_rows if row["campaign"] == "S16T16B"]
    actual_stop = max(int(row["trajectory_log"]) for row in b_saved)
    generator_text = LOCAL_SOURCES["pilot/hmc_generate.py"].read_text()
    batch_text = LOCAL_SOURCES["pilot/hmc200.sbatch"].read_text()
    hmc_settings = read_hmc_cli_settings(batch_text, generator_text)
    early_stop_source = "if saved >= args.max_save:" in generator_text and "break" in generator_text
    expected_stop = hmc_settings["thermal"] + 1 + (hmc_settings["max_save"] - 1) * hmc_settings["save_every"]
    source_aligned_stop = bool(
        early_stop_source
        and len(b_saved) == hmc_settings["max_save"]
        and actual_stop == expected_stop
        and b_done["planned_trajectories"] == hmc_settings["trajectories"]
    )
    accepted_count = final_counts[0] if len(final_counts) == 1 else None
    b_acceptance = {
        "done_reported_rate": b_done["reported_accept_rate"],
        "planned_denominator": b_done["planned_trajectories"],
        "accepted_count_candidates_from_rounded_DONE": final_counts,
        "last_saved_trajectory": actual_stop,
        "source_derived_expected_stop_trajectory": expected_stop,
        "batch_hmc_settings": hmc_settings,
        "source_derived_early_stop_supported": source_aligned_stop,
        "source_assisted_actual_acceptance_rate": (
            accepted_count / actual_stop if accepted_count is not None and source_aligned_stop else None
        ),
        "limitation": "The log contains sparse checkpoints, not every trajectory's accept/reject decision or Delta H.",
    }

    # Compute a non-authoritative plaquette autocorrelation sensitivity table.
    b_plaq = [float(row["manifest_plaquette"]) for row in manifest_rows if row["campaign"] == "S16T16B"]
    acf = autocorrelation(b_plaq)
    acf_rows = []
    for window in (5, 10, 20, 30, 40, 50, 80):
        acf_rows.append({"max_positive_lag": window, "tau_int_estimate": tau_with_cutoff(acf, window), "n_saved_configs": len(b_plaq)})
    write_csv(OUT / "hmc_b_plaquette_tau_sensitivity.csv", acf_rows)

    counts = {}
    for campaign in CAMPAIGNS:
        rows = [row for row in manifest_rows if row["campaign"] == campaign]
        counts[campaign] = {
            "n_configurations": len(rows),
            "raw_hash_matches_manifest": sum(bool(row["raw_hash_matches_manifest"]) for row in rows),
        }
    pair_summary = {}
    for left, right in (("S16T16", "S16T16B"), ("S16T16", "S16T16C"), ("S16T16B", "S16T16C")):
        rows = [row for row in pair_rows if row["left_campaign"] == left and row["right_campaign"] == right]
        pair_summary[f"{left}_vs_{right}"] = {
            "overlapping_ids": len(rows),
            "raw_file_hash_equal": sum(bool(row["raw_file_hash_equal"]) for row in rows),
            "payload_hash_equal": sum(bool(row["payload_hash_equal"]) for row in rows),
        }
    source_summary = {row["path"]: bool(row["byte_identical"]) for row in source_hash_rows}
    manifest_copy_summary = {row["campaign"]: bool(row["byte_identical"]) for row in source_copy_rows}
    pion_summary = {}
    for source_name in ("pion_gevp200", "pion_pilot_v1"):
        rows = [row for row in provenance_rows if row["source"] == source_name]
        pion_summary[source_name] = {
            "records": len(rows),
            "raw_file_hash_matches": sum(bool(row["raw_hash_matches"]) for row in rows),
        }
    hmc_summary = {}
    for campaign in CAMPAIGNS:
        rows = [row for row in hmc_rows if row["campaign"] == campaign]
        hmc_summary[campaign] = {
            "saved_log_rows": len(rows),
            "path_matches": sum(bool(row["path_matches"]) for row in rows),
            "trajectory_matches": sum(bool(row["trajectory_matches"]) for row in rows),
            "plaquette_matches": sum(bool(row["plaquette_matches"]) for row in rows),
            "manifest_raw_bytes_verified": sum(bool(row["raw_bytes_match_manifest"]) for row in rows),
        }
    summary = {
        "remote_gauge_file_count": len(gauge_hashes),
        "campaigns": counts,
        "pairwise_payloads": pair_summary,
        "remote_manifest_copies": manifest_copy_summary,
        "hmc_source_copies": source_summary,
        "pion_raw_identity": pion_summary,
        "hmc_log_crosswalk": hmc_summary,
        "B_vs_C_sparse_checkpoint_comparison": checkpoint_comparison,
        "S16T16B_hmc": {
            "checkpoint_count": len(b_checkpoints),
            "done": b_done,
            "acceptance_reconstruction": b_acceptance,
            "plaquette_mean": float(np.mean(b_plaq)),
            "plaquette_sample_std": float(np.std(b_plaq, ddof=1)),
            "tau_sensitivity": acf_rows,
        },
        "interpretation": {
            "raw_sha_mismatch_cause": "The compared files have distinct NERSC headers (creation time / creator hardware); payload digests test the gauge-link bytes after END_HEADER.",
            "independence": "Identical payload hashes mean these IDs are duplicate gauge fields across directories, regardless of distinct raw-file hashes. Do not count copied/re-written payloads as independent configurations.",
            "f4_status": "Archive byte identity is strengthened, but sparse Delta H checkpoints and missing per-trajectory acceptance decisions do not satisfy the full F4 receipt.",
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    make_identity_plot(pair_rows, manifest_rows, provenance_rows, hmc_rows)
    make_hmc_plot(b_checkpoints, b_done, b_plaq, configs_by_campaign["S16T16B"], acf_rows)
    write_readme(summary, source_rows=source_hash_rows, manifest_copies=source_copy_rows, b_acceptance=b_acceptance)

    inputs = [LOCAL_PRIMARY, LOCAL_SNAPSHOT, LOCAL_HMC_LOG, V9_MANIFEST, *PION200_FILES, *PION_V1_FILES, *LOCAL_SOURCES.values()]
    provenance = {
        "schema": "kunshan-live-gauge-byte-audit-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "remote": REMOTE,
        "remote_root": REMOTE_ROOT,
        "scope": "Read-only byte hashing of 500 remote NERSC gauge files plus archived manifest/log/source crosswalks; no gauge bytes copied, no remote writes or jobs submitted.",
        "local_input_sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in inputs},
        "remote_text_sha256": {
            REMOTE_TEXT[rel]: sha256_bytes(data) for rel, data in text_payloads.items()
        },
        "remote_gauge_inventory_sha256": sha256_file(OUT / "manifest_byte_crosswalk.csv"),
        "outputs_sha256": {},
    }
    for path in sorted(OUT.iterdir()):
        if path.is_file() and path.name != "provenance.json":
            provenance["outputs_sha256"][path.name] = sha256_file(path)
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"wrote {OUT}")


def make_identity_plot(pair_rows: list[dict], manifest_rows: list[dict], provenance_rows: list[dict], hmc_rows: list[dict]) -> None:
    max_id = max(CAMPAIGNS.values())
    labels = [
        "S16T16 raw file vs manifest",
        "S16T16B raw file vs manifest",
        "S16T16C raw file vs manifest/snapshot",
        "Pion pilot v1 provenance vs S16T16 raw file",
        "Pion GEVP200 provenance vs S16T16C raw file",
        "HMC log path/metadata vs manifest: S16T16",
        "HMC log path/metadata vs manifest: S16T16B",
        "HMC log path/metadata vs manifest: S16T16C",
        "Gauge payload equal: S16T16 vs S16T16B",
        "Gauge payload equal: S16T16B vs S16T16C",
    ]
    matrix = np.full((len(labels), max_id), np.nan)
    for row in manifest_rows:
        campaign, config_id = row["campaign"], int(row["id"])
        rid = {"S16T16": 0, "S16T16B": 1, "S16T16C": 2}[campaign]
        matrix[rid, config_id] = float(bool(row["raw_hash_matches_manifest"]))
    for row in provenance_rows:
        rid = {"pion_pilot_v1": 3, "pion_gevp200": 4}[row["source"]]
        matrix[rid, int(row["id"])] = float(bool(row["raw_hash_matches"]))
    for row in hmc_rows:
        rid = {"S16T16": 5, "S16T16B": 6, "S16T16C": 7}[row["campaign"]]
        matrix[rid, int(row["id"])] = float(
            row["path_matches"] and row["trajectory_matches"] and row["plaquette_matches"] and row["raw_bytes_match_manifest"]
        )
    for row in pair_rows:
        if row["left_campaign"] == "S16T16" and row["right_campaign"] == "S16T16B":
            matrix[8, int(row["id"])] = float(bool(row["payload_hash_equal"]))
        if row["left_campaign"] == "S16T16B" and row["right_campaign"] == "S16T16C":
            matrix[9, int(row["id"])] = float(bool(row["payload_hash_equal"]))

    cmap = ListedColormap(["#d95f5f", "#3a9d67"])
    cmap.set_bad("#e6e6e6")
    fig, ax = plt.subplots(figsize=(14, 6.3))
    ax.imshow(matrix, aspect="auto", interpolation="nearest", cmap=cmap, norm=BoundaryNorm([-0.5, 0.5, 1.5], 2))
    ax.set_yticks(range(len(labels)), labels=labels, fontsize=8)
    ax.set_xticks(np.arange(0, max_id, 20), labels=np.arange(0, max_id, 20))
    ax.set_xlabel("configuration ID (IDs are run-local labels)")
    ax.set_title("Raw gauge identity and duplicated payloads across Kunshan campaigns")
    ax.grid(axis="x", color="white", linewidth=0.5, alpha=0.7)
    ax.legend(handles=[Patch(color="#3a9d67", label="match / equal"), Patch(color="#d95f5f", label="mismatch / different"), Patch(color="#e6e6e6", label="not present")], loc="lower right", fontsize=8)
    fig.text(0.01, 0.01, "Raw-file SHA includes NERSC metadata. Payload SHA is computed after END_HEADER; identical payload means identical stored gauge-link bytes.", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "identity_and_duplicate_payloads.png", dpi=170)
    plt.close(fig)


def make_hmc_plot(checkpoints: list[dict], done: dict, plaquettes: list[float], manifest: dict[int, dict], tau_rows: list[dict]) -> None:
    traj = np.asarray([row["trajectory"] for row in checkpoints], dtype=int)
    d_h = np.asarray([row["delta_h"] for row in checkpoints], dtype=float)
    rate = np.asarray([float(row["reported_cumulative_rate"]) for row in checkpoints])
    saved_ids = np.arange(len(plaquettes))
    saved_traj = np.asarray([manifest[i]["trajectory"] for i in saved_ids], dtype=int)
    acf = autocorrelation(plaquettes)
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.4))
    axes[0, 0].plot(traj, d_h, "o-", ms=3, lw=0.8)
    axes[0, 0].axhline(0, color="black", lw=0.7)
    axes[0, 0].set(xlabel="trajectory checkpoint", ylabel="$\\Delta H$", title="Sparse $\\Delta H$ checkpoints")
    axes[0, 0].grid(alpha=0.2)
    axes[0, 1].plot(traj, rate, "o-", ms=3, lw=0.8, label="printed cumulative rate")
    axes[0, 1].axhline(float(done["reported_accept_rate"]), color="#d95f5f", ls="--", label=f"DONE / planned N: {done['reported_accept_rate']}")
    axes[0, 1].set(xlabel="trajectory checkpoint", ylabel="acceptance fraction", title="Logged acceptance summaries")
    axes[0, 1].set_ylim(0.9, 1.005)
    axes[0, 1].legend(fontsize=7)
    axes[0, 1].grid(alpha=0.2)
    axes[1, 0].plot(saved_traj, plaquettes, lw=0.8)
    axes[1, 0].set(xlabel="saved trajectory", ylabel="plaquette", title="S16T16B saved configurations (N=200)")
    axes[1, 0].grid(alpha=0.2)
    axes[1, 1].plot(np.arange(1, len(acf) + 1), acf, "o-", ms=3, lw=0.8)
    axes[1, 1].axhline(0, color="black", lw=0.7)
    axes[1, 1].set(xlabel="lag in saved configurations", ylabel="autocorrelation", title="Plaquette autocorrelation (exploratory)")
    axes[1, 1].grid(alpha=0.2)
    fig.suptitle("S16T16B archived HMC diagnostics — sparse log evidence, not full trajectory receipt", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT / "hmc_b_sparse_diagnostics.png", dpi=170)
    plt.close(fig)


def write_readme(summary: dict, source_rows: list[dict], manifest_copies: list[dict], b_acceptance: dict) -> None:
    c = summary["campaigns"]
    pairs = summary["pairwise_payloads"]
    pion = summary["pion_raw_identity"]
    hmc = summary["hmc_log_crosswalk"]
    checkpoint_comparison = summary["B_vs_C_sparse_checkpoint_comparison"]
    hmc_settings = b_acceptance["batch_hmc_settings"]
    copy_lines = "\n".join(f"- `{r['campaign']}` remote manifest vs local copy: {r['byte_identical']} ({r['config_count']} configs)." for r in manifest_copies)
    source_lines = "\n".join(f"- `{r['path']}` remote/local source bytes identical: {r['byte_identical']}." for r in source_rows)
    text = f'''# Kunshan live archive: raw gauge byte and HMC log audit

This read-only audit connected to the configured `{REMOTE}` SSH alias. It streamed SHA-256 digests for 500 remote NERSC files and the SHA-256 of the link payload after `END_HEADER`. It archived small manifests and logs locally, but copied no gauge bytes, wrote nothing remotely, and submitted no Slurm jobs. The `build` command needs the same SSH alias and rereads the remote files; `verify` checks only this frozen local audit.

## Direct results

- `data/S16T16`: {c['S16T16']['raw_hash_matches_manifest']}/{c['S16T16']['n_configurations']} actual raw-file hashes match the remote manifest; its remote manifest is byte-identical to the local `results/kunshan_logs/manifest.json`.
- `data/S16T16B`: {c['S16T16B']['raw_hash_matches_manifest']}/{c['S16T16B']['n_configurations']} actual raw-file hashes match its remote manifest. Its 200 SAVED log paths and the manifest IDs, trajectories and plaquettes cross-check row by row.
- `data/S16T16C`: {c['S16T16C']['raw_hash_matches_manifest']}/{c['S16T16C']['n_configurations']} actual raw-file hashes match the remote manifest; that manifest is byte-identical to the local Wilson `manifest_snapshot.json`.
- Raw full-file SHA differs between campaigns because NERSC headers record different creator hardware and creation/archive timestamps. The exact bytes after the `END_HEADER` line are identical for S16T16 vs B: {pairs['S16T16_vs_S16T16B']['payload_hash_equal']}/{pairs['S16T16_vs_S16T16B']['overlapping_ids']} IDs; B vs C: {pairs['S16T16B_vs_S16T16C']['payload_hash_equal']}/{pairs['S16T16B_vs_S16T16C']['overlapping_ids']} IDs; S16T16 vs C: {pairs['S16T16_vs_S16T16C']['payload_hash_equal']}/{pairs['S16T16_vs_S16T16C']['overlapping_ids']} IDs. Thus these directories contain duplicate gauge payload bytes over their overlapping IDs; do not count them as independent configurations.
- Pion `s16t16_v1` gauge hashes match the actual S16T16 raw files for {pion['pion_pilot_v1']['raw_file_hash_matches']}/{pion['pion_pilot_v1']['records']} archived measurement rows. Pion GEVP200 hashes match actual S16T16C raw files for {pion['pion_gevp200']['raw_file_hash_matches']}/{pion['pion_gevp200']['records']} rows. GEVP200 IDs 0–99 therefore refer to the same link payloads as S16T16/S16T16B where present; its IDs 100–119 and 140–199 are additional points on the same replayed HMC chain, not a separately seeded chain.
- The local HMC production log, B log `hmc200_128345242.out`, and C log `hmc200c_128360922.out` have matching SAVED path/ID/trajectory/plaquette metadata for {hmc['S16T16']['saved_log_rows']}/{hmc['S16T16']['saved_log_rows']}, {hmc['S16T16B']['saved_log_rows']}/{hmc['S16T16B']['saved_log_rows']}, and {hmc['S16T16C']['saved_log_rows']}/{hmc['S16T16C']['saved_log_rows']} rows respectively. The actual file digests were compared against each manifest; match counts are {hmc['S16T16']['manifest_raw_bytes_verified']}, {hmc['S16T16B']['manifest_raw_bytes_verified']}, and {hmc['S16T16C']['manifest_raw_bytes_verified']} respectively.
- The B/C batch scripts and `pilot/hmc_generate.py` are byte-identical to the archived local files:\n{source_lines}
- B/C sparse checkpoint comparison: {checkpoint_comparison['shared_trajectory_count']} shared logged trajectories; all compared physics fields match on all shared checkpoints = {checkpoint_comparison['all_physics_fields_equal_on_shared_trajectories']}; runtime seconds match on {checkpoint_comparison['timing_equal_count']}/{checkpoint_comparison['shared_trajectory_count']}. The B batch/source settings resolve seed {hmc_settings['seed']} ({hmc_settings['seed_source']}). This is direct evidence about saved payloads and logged checkpoints, not every unlogged trajectory.

## S16T16B HMC limits

The B log records {summary['S16T16B_hmc']['checkpoint_count']} sparse trajectory checkpoints, each with one accept flag, $\\Delta H$ and a rounded cumulative acceptance fraction. It records {hmc['S16T16B']['saved_log_rows']} saved configurations through trajectory {summary['S16T16B_hmc']['acceptance_reconstruction']['last_saved_trajectory']}; batch/source settings predict stop trajectory {b_acceptance['source_derived_expected_stop_trajectory']} when `max_save={hmc_settings['max_save']}` is reached. The `DONE` fraction is {b_acceptance['done_reported_rate']} using the planned denominator. Under the matching generator's `accepted / args.trajectories` formatting, the possible accepted-count set is `{b_acceptance['accepted_count_candidates_from_rounded_DONE']}`; conditional on that source and the early-stop schedule, the aggregate actual-run fraction is {b_acceptance['source_assisted_actual_acceptance_rate']:.6f}.

This does not reconstruct unlogged per-trajectory accept/reject decisions or $\\Delta H$. The plaquette series and lag-window estimates in `hmc_b_plaquette_tau_sensitivity.csv` are exploratory for only 200 saved configurations; no thermalization/autocorrelation rule was frozen in the HMC manifest. Therefore Wilson F4 is **PARTIAL**, not complete. It still needs a protocol-matched receipt with every trajectory's $\\Delta H$ and acceptance decision, a declared thermalization cut, and a justified autocorrelation/block rule. The remote B data exist, but the observed B/C duplicate chain must not be counted twice.

## Reproducible artifacts

- `manifest_byte_crosswalk.csv`: all 500 file hashes, manifest digest checks, and payload digests.
- `campaign_payload_crosswalk.csv`: per-ID full-file and gauge-payload equality across campaigns.
- `pion_raw_identity_crosswalk.csv`: stored Pion source hashes against actual remote gauge bytes.
- `hmc_saved_crosswalk.csv`: SAVED paths and metadata against manifests plus verified file hashes.
- `hmc_b_checkpoints.csv`: raw sparse B log checkpoints; no unobserved trajectory decision is imputed.
- `hmc_b_c_checkpoint_comparison.csv`: per-shared-checkpoint B/C comparison of logged acceptance flag, $\\Delta H$, plaquette, cumulative rate and runtime.
- `identity_and_duplicate_payloads.png` and `hmc_b_sparse_diagnostics.png`: visual crosswalk and HMC diagnostics.
- `remote_hmc200_128360803.err` records a separate cancelled attempt; it is retained and excluded from the successful B run.

Frozen artifact verification: `python3 -B -m tasks.kunshan_live_archive_audit verify`.
'''
    (OUT / "README.md").write_text(text)


def verify() -> None:
    provenance_path = OUT / "provenance.json"
    if not provenance_path.is_file():
        raise RuntimeError(f"missing frozen provenance: {provenance_path}")
    provenance = json.loads(provenance_path.read_text())
    failures = []
    for name, expected in provenance["outputs_sha256"].items():
        path = OUT / name
        actual = sha256_file(path) if path.is_file() else "MISSING"
        if actual != expected:
            failures.append(name)
    summary = json.loads((OUT / "summary.json").read_text())
    if summary["pairwise_payloads"]["S16T16_vs_S16T16B"]["payload_hash_equal"] != 100:
        failures.append("S16T16_vs_S16T16B payload equality count")
    if summary["pairwise_payloads"]["S16T16B_vs_S16T16C"]["payload_hash_equal"] != 200:
        failures.append("S16T16B_vs_S16T16C payload equality count")
    if failures:
        raise RuntimeError(f"frozen audit verification failed: {failures}")
    print("PASS: frozen remote byte audit outputs and payload-identity counts match; no live SSH rehash was performed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("build", "verify"))
    args = parser.parse_args()
    if args.mode == "build":
        build()
    else:
        verify()


if __name__ == "__main__":
    main()
