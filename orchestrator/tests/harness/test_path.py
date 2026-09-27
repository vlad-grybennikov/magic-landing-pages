from tatl import DependencyGraph, Edge, GoalState, OpSpec, PolicyAssertion, Projection
from tatl import evaluate_outcome, evaluate_path

DEP = DependencyGraph(
    required_ops=[
        OpSpec(tool="interpret"),
        OpSpec(tool="generate_copy", args_include={"section": "hero"}),
        OpSpec(tool="assemble_page"),
        OpSpec(tool="save_draft"),
    ],
    ordering=[
        Edge(source="interpret", target="assemble_page"),
        Edge(source="assemble_page", target="save_draft"),
    ],
)
NEVER_PERSIST_UNVALIDATED = PolicyAssertion(
    kind="require_before", first="assemble_page", then="save_draft")


def step(tool, args=None, result=None, error=None):
    return {"call": {"tool": tool, "args": args or {}}, "result": result, "error": error}


def trace(steps, initial=None, final=None):
    empty = {"tables": {"pages": []}}
    return {"instruction": "x", "steps": steps,
            "initial_snapshot": initial or empty,
            "final_snapshot": final or empty, "summary": ""}


GOOD_STEPS = [
    step("interpret", {"transcript": "a page for Maria's Bakery"},
         {"intent": "createPage", "args": {"business": "Maria's Bakery"}}),
    step("generate_copy", {"section": "hero"}, {"fields": ["headline"]}),
    step("assemble_section", {"section": "hero"}, "ok"),
    step("assemble_page", {"name": "Maria's Bakery", "sections": ["hero"]},
         {"url": "/maria-s-bakery", "sections": 1}),
    step("save_draft", {"url": "/maria-s-bakery"}, "ok"),
]


def test_clean_path_scores_perfectly():
    result = evaluate_path(trace(GOOD_STEPS), DEP, [NEVER_PERSIST_UNVALIDATED])
    assert result.node_recall == 1.0
    assert result.order_conformance == 1.0
    assert result.redundancy_ratio == 0.0
    assert result.policies_passed
    assert result.missing_ops == []


def test_missing_required_op_lowers_node_recall():
    without_copy = [s for s in GOOD_STEPS if s["call"]["tool"] != "generate_copy"]
    result = evaluate_path(trace(without_copy), DEP, [])
    assert result.node_recall == 0.75
    assert "generate_copy" in result.missing_ops


def test_args_include_distinguishes_same_tool_different_section():
    faq_only = [step("interpret"), step("generate_copy", {"section": "faq"}),
                step("assemble_page"), step("save_draft")]
    result = evaluate_path(trace(faq_only), DEP, [])
    assert "generate_copy" in result.missing_ops


def test_out_of_order_persist_violates_policy():
    reordered = [
        GOOD_STEPS[0], GOOD_STEPS[1], GOOD_STEPS[2],
        step("save_draft", {"url": "/maria-s-bakery"}, "ok"),
        step("assemble_page", {}, {"url": "/maria-s-bakery", "sections": 1}),
    ]
    final = {"tables": {"pages": [{"id": "/maria-s-bakery", "url": "/maria-s-bakery",
                                   "name": "Maria's Bakery", "publish": False,
                                   "sections": [{"type": "hero"}], "versions": []}]}}
    tr = trace(reordered, final=final)

    goal = GoalState(created={"pages": {"/maria-s-bakery": {"n_sections": 1}}})
    assert evaluate_outcome(tr, goal, Projection()).passed

    l2 = evaluate_path(tr, DEP, [NEVER_PERSIST_UNVALIDATED])
    assert not l2.policies_passed
    assert l2.order_conformance < 1.0


def test_forbidden_call_on_rejection_task():
    steps = [step("interpret", {}, {"intent": "unsupported"}, error="not allowed")]
    forbid = PolicyAssertion(kind="forbid_call", tool="save_draft")
    assert evaluate_path(trace(steps), DependencyGraph(), [forbid]).policies_passed

    leaked = steps + [step("save_draft", {"url": "/x"}, "ok")]
    assert not evaluate_path(trace(leaked), DependencyGraph(), [forbid]).policies_passed


def test_failed_steps_are_not_counted_as_successful():
    steps = [step("interpret", {}, None, error="boom")]
    forbid = PolicyAssertion(kind="forbid_call", tool="interpret")
    assert evaluate_path(trace(steps), DependencyGraph(), [forbid]).policies_passed


def test_redundancy_counts_repeated_identical_calls():
    repeated = GOOD_STEPS + [step("generate_copy", {"section": "hero"}, {"fields": ["headline"]})]
    result = evaluate_path(trace(repeated), DEP, [])
    assert result.redundancy_ratio > 0


def test_edges_inferred_by_value_matching():
    dep = DependencyGraph(edges=[
        Edge(source="interpret", target="assemble_page"),
        Edge(source="assemble_page", target="save_draft"),
    ])
    result = evaluate_path(trace(GOOD_STEPS), dep, [])
    assert result.edge_recall == 1.0


def test_edge_not_inferred_when_a_step_hides_its_inputs():
    hidden = list(GOOD_STEPS)
    hidden[3] = step("assemble_page", {}, {"url": "/maria-s-bakery", "sections": 1})
    dep = DependencyGraph(edges=[Edge(source="interpret", target="assemble_page")])
    assert evaluate_path(trace(hidden), dep, []).edge_recall == 0.0
