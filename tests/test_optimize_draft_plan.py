from tasks.optimize_gaussian.draft_plan import build_plan


def test_selected_f2_contrasts_are_bound_to_fail_closed_no_launch_plan():
    plan = build_plan()
    task = plan["task_spec"]
    run = plan["run_spec"]
    comparisons = [
        "trainable_W_vs_same_budget_SLSQP",
        "trainable_W_vs_fixed_degree4_Chebyshev",
    ]

    assert task["metric"]["comparison_family"] == comparisons
    assert run["task"]["metric"]["comparison_family"] == comparisons
    assert task["budget"]["methods"] == [
        "trainable_W", "same_budget_SLSQP", "fixed_degree4_Chebyshev",
    ]
    assert run["task"]["budget"]["objective_gradient_call_cap_per_arm"] == 160
    assert run["task"]["metric"]["D06"]["r_star"] == 10 / 9
    assert run["task"]["metric"]["D06"]["family_size"] == 2

    assert plan["status"] == "DRAFT_NO_LAUNCH"
    assert run["status"] == "DRAFT_NO_LAUNCH"
    assert plan["launch_allowed"] is False
    assert run["launch_allowed"] is False
    assert plan["physical_score"] is None
    assert run["physical_score"] is None
    assert run["data"] == {}
    assert run["authorization"] == {"production_data": False, "gpu_quda": False}
    assert plan["denominators"]["physical_gates"] == {
        "planned": 5, "valid": 0, "failed": 0, "abstained": 5,
        "unit": "operator/reference/numerical/statistical/comparison certification stages",
    }
