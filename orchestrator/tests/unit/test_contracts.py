import json
from pathlib import Path

import pytest

from app import create_app
from contracts import CommandResponse, PageView, PublicPage
from manifest import build_manifest, render_ts
from settings import Settings

GENERATED = Path(__file__).resolve().parents[3] / "frontend" / "src" / "generated"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return build_manifest()


@pytest.fixture(scope="module")
def openapi() -> dict:
    return create_app(Settings(env="development"), warm=False).openapi()


def test_the_committed_manifest_matches_the_code(manifest):
    path = GENERATED / "manifest.ts"
    if not path.exists():
        pytest.skip("front end not present")
    assert path.read_text(encoding="utf-8") == render_ts(manifest), \
        "run `make contracts` and commit frontend/src/generated"


def test_the_committed_openapi_matches_the_code(openapi):
    path = GENERATED / "openapi.json"
    if not path.exists():
        pytest.skip("front end not present")
    assert json.loads(path.read_text(encoding="utf-8")) == json.loads(
        json.dumps(openapi)), "run `make contracts` and commit frontend/src/generated"


def test_every_section_has_variants_a_default_and_a_label(manifest):
    for kind in manifest["sectionOrder"]:
        assert manifest["variants"][kind], kind
        assert manifest["defaultVariants"][kind] in manifest["variants"][kind], kind
        assert manifest["sectionLabels"][kind], kind


def test_every_pack_covers_every_section_with_a_real_variant(manifest):
    for name, pack in manifest["layoutPacks"].items():
        assert list(pack) == manifest["sectionOrder"], name
        for kind, variant in pack.items():
            assert variant in manifest["variants"][kind], (name, kind, variant)
        assert name in manifest["packDescriptions"], name
    assert manifest["defaultLayoutPack"] in manifest["layoutPacks"]
    assert manifest["defaultFontPair"] in manifest["fontPairs"]


def test_list_fields_and_pins_name_real_sections(manifest):
    kinds = set(manifest["sectionOrder"])
    assert set(manifest["listFields"]) <= kinds
    assert set(manifest["pinnedSections"]) <= kinds
    assert set(manifest["iconSections"]) <= kinds
    assert set(manifest["notInNav"]) <= kinds
    assert manifest["provenance"] == ["generated", "placeholder", "edited"]


def test_the_stream_events_are_part_of_the_contract(openapi):
    schemas = openapi["components"]["schemas"]
    assert {"StreamEvent", "StepEvent", "ResultEvent", "StreamErrorEvent",
            "CommandEvent", "StatusEvent"} <= set(schemas)
    stream = openapi["paths"]["/command/text/stream"]["post"]["responses"]["200"]
    assert stream["content"]["text/event-stream"]["schema"] == {
        "$ref": "#/components/schemas/StreamEvent"}


def test_every_route_declares_its_error_shape(openapi):
    for path, methods in openapi["paths"].items():
        for method, spec in methods.items():
            for status, response in spec["responses"].items():
                if status in ("404", "409", "422", "503"):
                    ref = response["content"]["application/json"]["schema"].get("$ref", "")
                    assert ref.endswith("/ErrorResponse") or ref.endswith(
                        "/HTTPValidationError"), (method, path, status)


def test_response_models_accept_what_the_services_return():
    from tests.unit.test_storage import HERO

    view = {"id": "p1", "version": 1, "name": "P", "url": "/p", "sections": [HERO],
            "theme": None, "published": None,
            "readiness": {"ready": True, "blocking": [], "warnings": []}}
    assert PageView(**view).version == 1
    assert PublicPage(url="/p", version=1, sections=[HERO], when="now").url == "/p"
    assert CommandResponse(recognizedCommand="x", message="m", summary="s", brief={},
                           clarifications=[], versions=[],
                           plan={"action": "createPage", "schema": [], "operations": []},
                           validation={"valid": True}).plan.schema_ == []
