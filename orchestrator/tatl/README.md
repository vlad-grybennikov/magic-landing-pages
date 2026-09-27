# TATL -- Testing AI Agents at Three Levels

An evaluation harness for tool-using agents. Copied and adapted from
[three-level-agent-testing](https://github.com/vlad-grybennikov/three-level-agent-testing),
my own earlier companion code for the paper *Testing AI Agents at Three Levels:
An Evaluation Harness and Case Study*. Same author as this project.

The three stages are named for what they judge, not numbered:

| Stage | Classical analogue | Judges | Against |
|---|---|---|---|
| `outcome` | system test | what the run **achieved** | projected final state vs an annotated goal, `pass^k` over k repetitions |
| `path` | integration test | **how** it got there | required operations, data-flow edges, ordering, hard policy assertions |
| `component` | unit test | each **part** in isolation | frozen inputs: classification macro-F1, slot accuracy, Recall@k |

No stage subsumes the others. A run can reach the right state by a forbidden
path (`outcome` passes, `path` catches it) or take a clean path to the wrong
state (`path` nearly clean, `outcome` fails). `outcome` and `path` grade the
*same* live run, which is what keeps that disagreement observable.

## Writing a suite

A suite module reads like a pytest file. The decorator names its data file and
how many times to run it; the body receives the finished measurement and says
what counts as good.

```python
from tatl import outcome, path, component

@outcome(data="outcome/create_page_default.json", k=5)
def default_layout(result):
    """A brief naming no sections yields a page composed for the business, every run."""
    assert result.pass_hat_k == 1.0

@path(data="path/create_page_default.json", k=5)
def generation_path(result):
    """Nothing is persisted until it clears the schema gate."""
    assert result.node_recall == 1.0, f"missing: {result.missing_ops}"
    assert result.policies_passed, result.policy_failures

@component(data="component/create_page_default.json")
def default_components(result):
    """Every part is right for this one request, judged on its own."""
    assert result.intent_ok and result.sections_ok

@component.classification(data="dataset/intent_classification.json")
def intent(result):
    assert result.macro_f1 >= 0.85
```

Everything expensive -- running episodes, snapshotting and projecting state,
inferring edges, computing F1 and `pass^k` -- happens before the body is
called. Thresholds live in Python next to the sentence explaining them; the
JSON holds only data.

`k` is the size of the subset `pass^k` asks about and, by default, also how
many episodes run. Pass `runs` to sample more than `k`: with `runs=10, k=5`,
`pass_hat_k` is the τ-bench estimate `C(c,5)/C(10,5)` over the ten rather
than an all-or-nothing verdict on five. Outcome and path cases that describe
the same run share its episodes, so give both the same `runs`.

### What a body receives

| Decorator | Object | Useful fields |
|---|---|---|
| `@outcome` | `Outcome` | `pass_hat_k`, `pass_rate`, `passed`, `runs`, `passes`, `diffs`, `rejected_at`, `per_run` |
| `@path` | `Path` | `node_f1`, `node_recall`, `edge_f1`, `order_conformance`, `redundancy_ratio`, `policies_passed`, `missing_ops`, `observed_ops`, `policy_failures` |
| `@component` | `Components` | `intent_ok`, `slot_accuracy`, `per_slot`, `sections_ok`, `image_ok`, `errors` |
| `@component.classification` | `Classification` | `macro_f1`, `accuracy`, `per_class`, `errors` |
| `@component.extraction` | `Extraction` | `slot_accuracy`, `per_slot`, `errors` |
| `@component.retrieval` | `Retrieval` | `recall_at_k`, `hits`, `total`, `misses` |

## Data files

One file per stage per case, each standalone -- nothing needs reading beside
another file.

```
test_data/
  outcome/<case>.json     what the run must leave behind
  path/<case>.json        which operations must run, in what order
  component/<case>.json   every part judged on that one instruction
  dataset/<probe>.json    labeled inputs and outputs for a single component
```

**outcome** -- anything not mentioned must be unchanged, so an empty `expect`
asserts the run touched nothing.

```json
{
  "instruction": "Create a landing page for Maria's Bakery ...",
  "setup": [],
  "expect": {
    "created": { "pages": { "/maria-s-bakery": { "n_sections": 5 } } },
    "changed": { "pages": { "/other": { "publish": true } } }
  }
}
```

A value may be a matcher instead of a literal when the goal is a property
rather than one exact state. Matchers combine, and `$changed` compares
against the row's initial value, so it only makes sense under `changed`.

```json
{ "section_types": { "$startswith": "header,hero", "$contains": ["benefits"],
                     "$endswith": "faq,footer" },
  "n_sections": { "$between": [7, 11] },
  "section_images": { "$changed": true } }
```

`$contains` is substring on strings and membership on lists; `$between` is
inclusive, on a number or a list's length; `$startswith` / `$endswith` take a
string or, for lists, an element or prefix/suffix list. The same matchers work
for `sections` in a component file.

**path** -- `where` narrows a required operation to specific arguments;
`flows` are data dependencies, `before` is ordering.

```json
{
  "instruction": "Create a landing page for Maria's Bakery ...",
  "setup": [],
  "require": [
    { "tool": "generate_copy", "where": { "section": "hero" } },
    { "tool": "save_draft" }
  ],
  "flows":  [["assemble_page", "save_draft"]],
  "before": [["assemble_page", "save_draft"]],
  "policies": [
    { "require_before": ["assemble_page", "save_draft"] },
    { "require_before": ["interpret", "generate_schema"] }
  ]
}
```

Use `forbid` for cases that must be rejected. An unclear command, for
example, has `{ "forbid": "save_draft" }`.

**component** -- one instruction, its paraphrases, and what every part must
make of them. A variant may carry its own `slots` when a paraphrase
legitimately extracts differently, and a slot may list acceptable values.

```json
{
  "instruction": "Swap the first two steps",
  "variants": [
    "Move the first step down one",
    { "text": "Put Order online after We bake",
      "slots": { "path": { "$any": ["items.0", "items.order online"] } } }
  ],
  "expect": { "intent": "moveItem",
              "slots": { "section": "process", "path": "items.0", "position": "down" } }
}
```

Slot values match case-insensitively, by containment, or -- for values of two
or more words -- by word overlap, so a free-text slot such as `goal` accepts
a faithful paraphrase ("collect enquiries" for "collects enquiries") while
short slots like `path` stay exact.

**dataset** -- `probe` picks the component, `cases` are frozen input/output
pairs. Add `"reviewed": false` to park a case (e.g. an LLM-generated
paraphrase) until a human approves it.

```json
{
  "probe": "classify",
  "metric": "macro_f1",
  "cases": [{ "input": "Shorten the hero headline", "expect": "editContent" }]
}
```

Outcome and path files are fully independent. When two happen to describe
the identical run, the runner grades both from the same episodes instead of
running them twice -- an execution saving only; the files never reference each
other.

## Running

```
make suite                    # everything, prints the matrix, writes JSON + HTML
make suite SELECT=collision   # only cases whose name contains "collision"
make suite STAGE=component    # only the component probes
make suite MODEL=llama3.1:8b  # against a different local model
make test                     # the harness's own tests, offline
```

Exit status is non-zero if any case fails, so it drops into CI unchanged.

## Retargeting to another agent

Nothing in `tatl/` knows what the system under test does. To point it at
something else:

1. Implement `tatl.adapter.AgentAdapter`: `run_episode(task, run_index)`
   returns an `EpisodeOutcome` carrying a trace (`steps`, each
   `{"call": {"tool", "args"}, "result", "error"}`, plus
   `initial_snapshot` / `final_snapshot`), and `probes()` returns a
   `ComponentProbes`. Episodes must run against a fresh, isolated
   environment -- that is what makes the outcome stage's
   everything-else-unchanged rule meaningful, and lets episodes run
   concurrently.

   Two optional parts of the trace feed the report's top-level
   `telemetry` block, summed over every episode of the run: a step whose
   `result` is a status string (or a dict with a `status` key) is counted
   under `step_status`, with `"defaulted"` also broken down by tool; and a
   `telemetry` dict of nested integer counters is added key by key into
   `model_calls`.
2. Name it in `tatl.config.json` (`adapter`, `suite_dir`, `data_dir`), where
   the matrix columns are also defined.
3. Write suite modules and data files.

See [`mlp_adapter.py`](../mlp_adapter.py) for a worked example.

## Layout

```
tatl/
  adapter.py      the host-application contract
  suite.py        the decorators and the case registry
  data.py         the authoring format, converted to the evaluation types
  evaluators.py   all computation: the three evaluators and the scorers
  annotations.py  internal evaluation types (goal, dependency, policies)
  results.py      what a test body receives
  runner.py       orchestration: episodes, grading, verdicts
  report.py       view model + the colour matrix (terminal and HTML)
  templates/      the HTML template and stylesheet (Jinja2)
  config.py       suite config and matrix columns
```

## Known limitations

- **Edge inference** recovers a dependency only when a value literally
  reappears in a later call's arguments. An operation that hides its inputs
  shows no incoming edge even though one exists, and coincidental equality of
  common values can produce spurious edges.
- **Node precision** penalises running more distinct tools than the annotation
  requires, so a partial annotation reads as agent noise. Annotate the full
  expected operation set.
- **Outcome projection** drops fields that are generative (free text) by
  design; quality of that text is a human-rated metric, not an oracle.
