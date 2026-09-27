from tatl import component, outcome, path


@outcome(data="outcome/edit_headline.json", k=5)
def edit_headline(result):
    """Changing the headline puts the requested words in the hero and leaves
    the structure alone: same sections, same URL, and the page is still a
    draft."""
    assert result.pass_hat_k == 1.0, result.diffs


@outcome(data="outcome/add_section.json", k=5)
def add_section(result):
    """A new section lands in canonical order without being told where to go --
    the user asked for testimonials, not for a layout."""
    assert result.pass_hat_k == 1.0, result.diffs


@outcome(data="outcome/remove_section.json", k=5)
def remove_section(result):
    """Removal leaves a valid page behind, not an empty one."""
    assert result.pass_hat_k == 1.0, result.diffs


@outcome(data="outcome/set_theme.json", k=5)
def set_theme(result):
    """Recolouring a page gives it a palette and touches nothing else: same
    sections, same URL, still a draft."""
    assert result.pass_hat_k == 1.0, result.diffs


@path(data="path/edit_headline.json", k=5)
def edit_path(result):
    """An edit reads the page, changes it, re-validates it, and only then
    stores it. Skipping the re-validation would let an edit persist something
    the generator could never have produced."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.order_conformance == 1.0
    assert result.policies_passed, result.policy_failures


@path(data="path/set_theme.json", k=5)
def set_theme_path(result):
    """A recolour is a generation step like any other: the palette is chosen,
    applied, and re-validated with the page before it is stored."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.order_conformance == 1.0
    assert result.policies_passed, result.policy_failures


@component(data="component/edit_headline.json")
def edit_components(result):
    """The three arguments an edit needs -- which section, which field, and the
    new text -- all come from one utterance."""
    assert result.intent_accuracy == 1.0, result.errors
    assert result.slot_accuracy >= 0.9, result.errors


@component(data="component/set_theme.json")
def set_theme_components(result):
    """A colour instruction is recognised as a theme change, with what the
    user asked for kept as the style hint."""
    assert result.intent_accuracy == 1.0, result.errors
    assert result.slot_accuracy >= 0.75, result.errors


@outcome(data="outcome/replace_image.json", k=5)
def replace_image(result):
    """Swapping a photo leaves the page's shape alone: the same sections, the
    same entries, still a draft."""
    assert result.pass_hat_k == 1.0, result.diffs


@outcome(data="outcome/set_variant.json", k=5)
def set_variant(result):
    """A layout change lands on the named section only; nothing else moves."""
    assert result.pass_hat_k == 1.0, result.diffs


@outcome(data="outcome/move_section.json", k=5)
def move_section(result):
    """Moving a section reorders the page without adding, dropping or editing
    anything."""
    assert result.pass_hat_k == 1.0, result.diffs


@outcome(data="outcome/add_item.json", k=5)
def add_item(result):
    """One more entry appears at the end of the named list, and only there."""
    assert result.pass_hat_k == 1.0, result.diffs


@outcome(data="outcome/remove_item.json", k=5)
def remove_item(result):
    """The named entry goes; its neighbours keep their order."""
    assert result.pass_hat_k == 1.0, result.diffs


@outcome(data="outcome/move_item.json", k=5)
def move_item(result):
    """Reordering entries changes their order and nothing else about them."""
    assert result.pass_hat_k == 1.0, result.diffs


@outcome(data="outcome/set_icon.json", k=5)
def set_icon(result):
    """Changing one icon leaves every entry and section in place."""
    assert result.pass_hat_k == 1.0, result.diffs


@outcome(data="outcome/rewrite_reviews.json", k=5)
def rewrite_reviews(result):
    """Asking for the reviews to be written again keeps the page's structure;
    what the reviews say is the model's, and is judged elsewhere."""
    assert result.pass_hat_k == 1.0, result.diffs


@path(data="path/add_section.json", k=5)
def add_section_path(result):
    """Adding a section writes only that section, without re-planning the page
    or picking a palette again."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.policies_passed, result.policy_failures


@path(data="path/remove_section.json", k=5)
def remove_section_path(result):
    """Removing a section generates nothing: load, remove, validate, store."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.policies_passed, result.policy_failures


@path(data="path/replace_image.json", k=5)
def replace_image_path(result):
    """A new photo is retrieved for the named section and nothing is written."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.order_conformance == 1.0
    assert result.policies_passed, result.policy_failures


@path(data="path/set_variant.json", k=5)
def set_variant_path(result):
    """A layout change touches no model at all."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.policies_passed, result.policy_failures


@path(data="path/move_section.json", k=5)
def move_section_path(result):
    """Reordering touches no model at all."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.policies_passed, result.policy_failures


@path(data="path/add_item.json", k=5)
def add_item_path(result):
    """A new entry is a structural edit, not a generation."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.policies_passed, result.policy_failures


@path(data="path/remove_item.json", k=5)
def remove_item_path(result):
    """Removing an entry touches no model at all."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.policies_passed, result.policy_failures


@path(data="path/move_item.json", k=5)
def move_item_path(result):
    """Reordering entries touches no model at all."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.policies_passed, result.policy_failures


@path(data="path/set_icon.json", k=5)
def set_icon_path(result):
    """One icon is looked up for the named section; no copy is written."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.order_conformance == 1.0
    assert result.policies_passed, result.policy_failures


@path(data="path/rewrite_reviews.json", k=5)
def rewrite_reviews_path(result):
    """A rewrite writes and validates the one section, without re-planning the
    page or choosing a palette, and stores only after the page validates."""
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.order_conformance == 1.0
    assert result.policies_passed, result.policy_failures


@component(data="component/add_section.json")
def add_section_components(result):
    """Wanting a section that is not there is read as adding that section."""
    assert result.intent_accuracy == 1.0, result.errors
    assert result.slot_accuracy >= 0.75, result.errors


@component(data="component/remove_section.json")
def remove_section_components(result):
    """Wanting a section gone names the section."""
    assert result.intent_accuracy == 1.0, result.errors
    assert result.slot_accuracy >= 0.75, result.errors


@component(data="component/replace_image.json")
def replace_image_components(result):
    """A picture request is a picture request, whichever word is used for it."""
    assert result.intent_accuracy == 1.0, result.errors
    assert result.slot_accuracy >= 0.75, result.errors


@component(data="component/set_variant.json")
def set_variant_components(result):
    """Wanting a section to look different is a layout change, and the layout
    named is recovered."""
    assert result.intent_accuracy == 1.0, result.errors
    assert result.slot_accuracy >= 0.75, result.errors


@component(data="component/move_section.json")
def move_section_components(result):
    """Wanting a section higher or lower is a move, with the direction kept."""
    assert result.intent_accuracy == 1.0, result.errors
    assert result.slot_accuracy >= 0.75, result.errors


@component(data="component/add_item.json")
def add_item_components(result):
    """Another benefit is an entry, not a section."""
    assert result.intent_accuracy == 1.0, result.errors
    assert result.slot_accuracy >= 0.75, result.errors


@component(data="component/remove_item.json")
def remove_item_components(result):
    """Which entry to remove is addressed by position, counted from zero."""
    assert result.intent_accuracy == 1.0, result.errors
    assert result.slot_accuracy >= 0.75, result.errors


@component(data="component/move_item.json")
def move_item_components(result):
    """Swapping two entries is moving one of them."""
    assert result.intent_accuracy == 1.0, result.errors
    assert result.slot_accuracy >= 0.75, result.errors


@component(data="component/set_icon.json")
def set_icon_components(result):
    """An icon request names the entry and the icon."""
    assert result.intent_accuracy == 1.0, result.errors
    assert result.slot_accuracy >= 0.75, result.errors


@component(data="component/rewrite_reviews.json")
def rewrite_reviews_components(result):
    """Asking for the reviews to be more real is a rewrite of the entries, not
    a dictated edit and not a new section."""
    assert result.intent_accuracy == 1.0, result.errors
    assert result.slot_accuracy >= 0.75, result.errors


@component.extraction(data="dataset/edit_slots.json")
def edit_slots(report):
    """Dictated edits: which section, which line or entry, and the exact words.
    Report target: slot accuracy >= 0.80."""
    assert report.slot_accuracy >= 0.80, f"errors: {report.errors[:5]}"


@component.extraction(data="dataset/rewrite_slots.json")
def rewrite_slots(report):
    """Rewrites: which section, how much of it, and how it should differ.
    Report target: slot accuracy >= 0.75."""
    assert report.slot_accuracy >= 0.75, f"errors: {report.errors[:5]}"


@component.extraction(data="dataset/structure_slots.json")
def structure_slots(report):
    """Structural edits: the section, the entry counted from zero, and the
    direction, layout or icon asked for. Report target: slot accuracy >= 0.80."""
    assert report.slot_accuracy >= 0.80, f"errors: {report.errors[:5]}"
