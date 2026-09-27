from tatl import component, outcome, path


@outcome(data="outcome/create_page_default.json", k=5)
def default_layout(result):
    """A brief naming no sections gets a page composed for the business: hero,
    benefits, testimonials and an FAQ are always there, and it runs to between
    five and nine sections -- every run."""
    assert result.pass_hat_k == 1.0


@outcome(data="outcome/create_page_named_sections.json", k=5)
def named_sections(result):
    """Asking for a hero and an FAQ produces exactly those two sections."""
    assert result.pass_hat_k == 1.0


@outcome(data="outcome/create_page_promotion_cue.json", k=5)
def promotion_cue(result):
    """A described offer counts as naming a section: it becomes a promotion,
    and no extra sections are invented alongside it."""
    assert result.pass_hat_k == 1.0


@outcome(data="outcome/create_page_collision.json", k=5)
def slug_collision(result):
    """A second page for the same business takes its own URL and leaves the
    published original untouched."""
    assert result.pass_hat_k == 1.0


@outcome(data="outcome/reject_unsupported_intent.json", k=5)
def reject_unsupported(result):
    """A request that is not about a page is refused and stores nothing."""
    assert result.passed
    assert result.rejected_at == "intent"


@outcome(data="outcome/reject_unclear_command.json", k=5)
def reject_unclear(result):
    """Silence transcribed into filler is refused before any model runs."""
    assert result.passed
    assert result.rejected_at == "command"


@path(data="path/create_page_default.json", k=5)
def generation_path(result):
    """Each section is written, illustrated and validated before the page is
    assembled, and nothing is persisted until it clears the schema gate."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.order_conformance == 1.0
    assert result.redundancy_ratio == 0.0
    assert result.policies_passed, result.policy_failures


@path(data="path/create_page_collision.json", k=5)
def collision_path(result):
    """The colliding page is persisted under the suffixed URL, and only after
    it has been validated."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.policies_passed, result.policy_failures


@path(data="path/create_page_named_sections.json", k=5)
def named_sections_path(result):
    """Only the two requested sections are generated -- no work is done for
    sections the user never asked for."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.policies_passed, result.policy_failures


@path(data="path/create_page_promotion_cue.json", k=5)
def promotion_cue_path(result):
    """The described offer is planned and built as a promotion section."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.policies_passed, result.policy_failures


@path(data="path/reject_unsupported_intent.json", k=5)
def refusal_path(result):
    """A refused request must not reach generation or persistence at all."""
    assert result.policies_passed, result.policy_failures
    assert "save_draft" not in result.observed_ops


@path(data="path/reject_unclear_command.json", k=5)
def unclear_command_path(result):
    """An unusable transcript is stopped before any model is called, so the
    refusal costs nothing."""
    assert result.policies_passed, result.policy_failures
    assert result.observed_ops == []


@component(data="component/create_page_default.json")
def default_layout_components(report):
    """Intent, brief, layout and photo are each judged on their own, across
    every way of phrasing the same request."""
    assert report.intent_accuracy == 1.0, report.errors
    assert report.slot_accuracy >= 0.9, report.errors
    assert report.sections_accuracy >= 0.75, report.errors
    assert report.image_recall >= 0.7, report.errors


@component(data="component/create_page_named_sections.json")
def named_sections_components(report):
    """The named sections are recovered by the planner, not just by the run."""
    assert report.intent_accuracy == 1.0, report.errors
    assert report.slot_accuracy >= 0.75, report.errors
    assert report.sections_accuracy >= 0.75, report.errors


@component(data="component/create_page_promotion_cue.json")
def promotion_cue_components(report):
    """A described offer is planned as a promotion, with nothing added."""
    assert report.intent_accuracy == 1.0, report.errors
    assert report.sections_accuracy >= 0.75, report.errors


@component(data="component/create_page_collision.json")
def collision_components(report):
    """Slug collisions are a storage concern: the components see the same
    request as the first create and must read it identically."""
    assert report.intent_accuracy == 1.0, report.errors
    assert report.slot_accuracy >= 0.9, report.errors


@component(data="component/reject_unsupported_intent.json")
def unsupported_components(report):
    """Refusal is a classifier decision, measurable without running anything."""
    assert report.intent_accuracy == 1.0, report.errors


@component(data="component/reject_unclear_command.json")
def unclear_components(report):
    """Even filler text must not be read as a page request."""
    assert report.intent_accuracy == 1.0, report.errors


@component.classification(data="dataset/intent_classification.json")
def intent_classification(report):
    """Closed-set action classification across the thirteen executable intents
    plus refusal (unsupported). Report target: macro-F1 >= 0.85."""
    assert report.macro_f1 >= 0.85, f"errors: {report.errors[:5]}"


@component.extraction(data="dataset/brief_slots.json")
def brief_slots(report):
    """business / audience / goal, filled from a single utterance.
    Report target: slot accuracy >= 0.90."""
    assert report.slot_accuracy >= 0.90, f"errors: {report.errors[:5]}"


@component.classification(data="dataset/section_planning.json")
def section_planning(report):
    """The layout chosen for a brief, as a comma-joined section list."""
    assert report.accuracy >= 0.80, f"errors: {report.errors[:5]}"


@component.retrieval(data="dataset/image_retrieval.json", k=5,
                     name="image_recall_at_5")
def image_selection(report):
    """The right kind of photo for a business, judged by category: several
    library photos are usually equally correct for one query, so scoring
    against one chosen file would understate real retrieval quality.

    The queries are written as real hero copy and deliberately never name the
    trade -- "burst pipe at midnight", not "plumber" -- so this measures whether
    retrieval understands the business, not whether it can match a keyword.
    Report target: Recall@5 >= 0.70."""
    assert report.recall_at_k >= 0.70, f"misses: {report.misses[:5]}"


@component.retrieval(data="dataset/image_retrieval.json", k=1,
                     name="image_recall_at_1")
def image_selection_top1(report):
    """The stricter read: the very first photo offered is the one a user sees
    on the hero, so top-1 is what the page quality actually depends on."""
    assert report.recall_at_k >= 0.50, f"misses: {report.misses[:5]}"
