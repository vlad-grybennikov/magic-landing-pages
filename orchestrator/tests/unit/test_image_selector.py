import json

import numpy as np
import pytest

import image_selector
from image_selector import CLIPImageService, StubImageService


@pytest.fixture
def library(tmp_path):
    records = [
        {"id": "1", "file": "bakery.jpg", "src": "/images/library/bakery.jpg",
         "category": "bakery", "alt": "Fresh bread on a counter",
         "photographer": "Ada", "photographer_url": "https://p/ada",
         "source_url": "https://pexels.com/1"},
        {"id": "2", "file": "yoga.jpg", "src": "/images/library/yoga.jpg",
         "category": "yoga studio", "alt": "People in a yoga class"},
        {"id": "3", "file": "plumb.jpg", "src": "/images/library/plumb.jpg",
         "category": "plumber working", "alt": "Plumber fixing a pipe"},
    ]
    (tmp_path / "index.json").write_text(json.dumps(records))
    np.save(tmp_path / "embeddings.npy", np.eye(3, dtype="float32"))
    return tmp_path


def service(library, query_vector):
    svc = CLIPImageService(library=library)
    svc._encode = lambda q: np.array(query_vector, dtype="float32")
    return svc


def test_rank_orders_by_cosine_similarity(library):
    svc = service(library, [0.1, 0.9, 0.2])
    ranked = svc.rank("calm yoga class", k=3)
    assert [r["id"] for r in ranked] == ["2", "3", "1"]


def test_rank_respects_k(library):
    assert len(service(library, [1, 0, 0]).rank("bread", k=2)) == 2


def test_choice_carries_attribution(library):
    choice = service(library, [1, 0, 0]).rank("bread", k=1)[0]
    assert choice["src"] == "/images/library/bakery.jpg"
    assert choice["category"] == "bakery"
    assert choice["photographer"] == "Ada"
    assert choice["source_url"] == "https://pexels.com/1"


def test_missing_attribution_is_none_not_absent(library):
    choice = service(library, [0, 1, 0]).rank("yoga", k=1)[0]
    assert choice["photographer"] is None and choice["source_url"] is None


def test_select_hero_returns_top_match(library):
    choice = service(library, [0, 0, 1]).select("hero", "plumber fixing a pipe")
    assert choice["id"] == "3"


def test_select_index_walks_down_the_ranking(library):
    svc = service(library, [0.9, 0.5, 0.1])
    assert svc.select("hero", "q", 0)["id"] == "1"
    assert svc.select("hero", "q", 1)["id"] == "2"


def test_library_out_of_sync_is_rejected(tmp_path):
    (tmp_path / "index.json").write_text(json.dumps([{"id": "1", "src": "/a.jpg"}]))
    np.save(tmp_path / "embeddings.npy", np.eye(3, dtype="float32"))
    with pytest.raises(ValueError, match="out of sync"):
        CLIPImageService(library=tmp_path)


def test_empty_library_ranks_nothing(tmp_path):
    (tmp_path / "index.json").write_text("[]")
    np.save(tmp_path / "embeddings.npy", np.zeros((0, 3), dtype="float32"))
    assert CLIPImageService(library=tmp_path).rank("anything") == []


def test_factory_returns_stub_when_asked(monkeypatch):
    monkeypatch.setenv("MLP_IMAGES", "stub")
    image_selector.build_image_service.cache_clear()
    assert isinstance(image_selector.build_image_service(), StubImageService)


def test_factory_falls_back_when_no_library(monkeypatch, tmp_path):
    monkeypatch.delenv("MLP_IMAGES", raising=False)
    monkeypatch.setattr(image_selector, "LIBRARY", tmp_path)
    image_selector.build_image_service.cache_clear()
    assert isinstance(image_selector.build_image_service(), StubImageService)


def test_factory_errors_when_clip_requested_without_library(monkeypatch, tmp_path):
    monkeypatch.setenv("MLP_IMAGES", "clip")
    monkeypatch.setattr(image_selector, "LIBRARY", tmp_path)
    image_selector.build_image_service.cache_clear()
    with pytest.raises(RuntimeError, match="fetch_library"):
        image_selector.build_image_service()
    image_selector.build_image_service.cache_clear()


def test_stub_service_shape():
    stub = StubImageService()
    hero = stub.select("hero", "anything")
    assert hero["src"].startswith("/images/")
    assert stub.rank("anything", k=3) and len(stub.rank("anything", k=1)) == 1
