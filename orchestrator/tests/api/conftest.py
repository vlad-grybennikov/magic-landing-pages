import mongomock
import pytest
from fastapi.testclient import TestClient

from app import create_app
from icon_selector import build_icon_service
from image_selector import StubImageService
from oracle import FixtureLanguageService
from providers import Providers
from services import Services
from settings import Settings
from transcriber import ScriptedTranscriber

ACCOUNTS = {
    "alice": {"email": "alice@example.com", "email_verified": True, "sub": "g-a",
              "name": "Alice"},
    "bob": {"email": "bob@example.com", "email_verified": True, "sub": "g-b",
            "name": "Bob"},
}


def make_services(settings=None, lang=None, transcriber=None):
    settings = settings or Settings(env="development", google_client_id="test-client",
                                    jwt_secret="test-secret", max_commands=2)
    db = mongomock.MongoClient()["vlp-api"]
    providers = Providers(lang=lang or FixtureLanguageService(), images=StubImageService(),
                          icons=build_icon_service())
    services = Services.from_db(settings, db, providers,
                                transcriber or ScriptedTranscriber(""),
                                verifier=lambda credential: ACCOUNTS[credential])
    services.ensure_indexes()
    return services


@pytest.fixture
def services():
    svc = make_services()
    yield svc
    svc.close()


@pytest.fixture
def client(services):
    with TestClient(create_app(services.settings, services)) as client:
        yield client


class Session:
    def __init__(self, client, name):
        self.client = client
        self.name = name
        signed = client.post("/auth/google", json={"idToken": name}).json()
        self.user = signed["user"]
        self.headers = {"Authorization": f"Bearer {signed['accessToken']}"}

    def _call(self, method, path, headers=None, **kw):
        return getattr(self.client, method)(path, headers={**self.headers, **(headers or {})},
                                            **kw)

    def get(self, path, **kw):
        return self._call("get", path, **kw)

    def post(self, path, **kw):
        return self._call("post", path, **kw)

    def put(self, path, **kw):
        return self._call("put", path, **kw)

    def patch(self, path, **kw):
        return self._call("patch", path, **kw)

    def delete(self, path, **kw):
        return self._call("delete", path, **kw)

    def create_page(self, text="Create a landing page for Maria's Bakery with a hero and an FAQ"):
        response = self.post("/command/text", json={"text": text})
        assert response.status_code == 200, response.text
        return response.json()["page"]


@pytest.fixture
def alice(client):
    return Session(client, "alice")


@pytest.fixture
def bob(client):
    return Session(client, "bob")
