import mongomock
import pytest

import auth
from auth import Authenticator, UserStore
from builds import BuildNotFound, BuildStore
from settings import ConfigError, Settings

GOOGLE = {"email": "vlad@example.com", "email_verified": True, "sub": "g-1",
          "name": "Vlad", "picture": "https://example.com/v.png"}


@pytest.fixture
def db():
    return mongomock.MongoClient()["vlp-auth"]


@pytest.fixture
def users(db):
    return UserStore(db["users"])


@pytest.fixture
def authenticator(users):
    return Authenticator(Settings(google_client_id="client"), users,
                         verifier=lambda credential: GOOGLE)


@pytest.fixture
def store(db):
    return BuildStore(db["builds"])


def test_a_google_account_becomes_a_user(users):
    user = users.upsert_google(GOOGLE)
    assert user["email"] == "vlad@example.com"
    assert user["name"] == "Vlad"
    assert user["id"]


def test_signing_in_again_is_the_same_user(users):
    first = users.upsert_google(GOOGLE)
    second = users.upsert_google({**GOOGLE, "name": "Vlad G"})

    assert second["id"] == first["id"]
    assert second["name"] == "Vlad G"


def test_tokens_round_trip(users, authenticator):
    user = users.upsert_google(GOOGLE)
    tokens = authenticator.issue_tokens(user["id"])

    assert authenticator.user_id_from(tokens["accessToken"]) == user["id"]
    assert authenticator.user_id_from(tokens["refreshToken"], "refresh") == user["id"]


def test_an_access_token_is_not_a_refresh_token(users, authenticator):
    tokens = authenticator.issue_tokens(users.upsert_google(GOOGLE)["id"])
    with pytest.raises(auth.AuthError):
        authenticator.user_id_from(tokens["accessToken"], "refresh")


def test_a_forged_token_is_refused(authenticator):
    with pytest.raises(auth.AuthError):
        authenticator.user_id_from("not.a.token")


def test_a_token_signed_with_another_secret_is_refused(users, authenticator):
    other = Authenticator(Settings(google_client_id="client", jwt_secret="other"), users)
    tokens = other.issue_tokens(users.upsert_google(GOOGLE)["id"])
    with pytest.raises(auth.AuthError):
        authenticator.user_id_from(tokens["accessToken"])


def test_signing_in_verifies_and_returns_tokens(authenticator):
    signed = authenticator.sign_in("credential")
    assert signed["user"]["email"] == "vlad@example.com"
    assert authenticator.authenticate(f"Bearer {signed['accessToken']}")["email"] \
        == "vlad@example.com"


def test_development_without_a_client_id_is_the_local_user(users):
    local = Authenticator(Settings(env="development"), users)
    assert not local.enabled
    assert local.authenticate(None) == auth.LOCAL_USER


def test_development_with_a_client_id_requires_a_token(users):
    signed = Authenticator(Settings(env="development", google_client_id="c"), users)
    assert signed.enabled
    with pytest.raises(auth.AuthError):
        signed.authenticate(None)


def test_production_never_falls_back_to_the_local_user(users):
    production = Authenticator(Settings(env="production", google_client_id="c",
                                        jwt_secret="long-random"), users)
    assert production.enabled
    with pytest.raises(auth.AuthError):
        production.authenticate(None)


def test_production_refuses_to_start_without_auth_configuration():
    with pytest.raises(ConfigError, match="GOOGLE_CLIENT_ID"):
        Settings(env="production", jwt_secret="x", cors_origins=("https://a",)).validate()
    with pytest.raises(ConfigError, match="MLP_JWT_SECRET"):
        Settings(env="production", google_client_id="c",
                 cors_origins=("https://a",)).validate()
    with pytest.raises(ConfigError, match="CORS"):
        Settings(env="production", google_client_id="c", jwt_secret="x").validate()
    Settings(env="production", google_client_id="c", jwt_secret="x",
             cors_origins=("https://a",)).validate()


def test_an_unknown_mode_is_refused():
    with pytest.raises(ConfigError):
        Settings(env="staging").validate()


def test_settings_read_the_environment():
    settings = Settings.from_env({"MLP_ENV": "Production", "GOOGLE_CLIENT_ID": " c ",
                                  "MLP_JWT_SECRET": "", "MLP_MAX_COMMANDS": "4",
                                  "MLP_CORS_ORIGINS": "https://a, https://b"})
    assert settings.production
    assert settings.google_client_id == "c"
    assert settings.jwt_secret == "mlp-dev-secret"
    assert settings.max_commands == 4
    assert settings.cors_origins == ("https://a", "https://b")


def test_a_build_starts_empty_and_belongs_to_its_owner(store):
    build = store.create("user-1")
    assert build["title"] == "New page"
    assert build["pageId"] is None
    assert build["turns"] == 0
    assert store.get(build["id"], "user-1")["owner"] == "user-1"


def test_builds_are_listed_newest_first(store):
    first = store.create("user-1")
    second = store.create("user-1")
    store.update(first["id"], "user-1", {"title": "Bakery"})

    listed = store.list("user-1")
    assert [b["id"] for b in listed] == [first["id"], second["id"]]
    assert listed[0]["title"] == "Bakery"


def test_one_user_cannot_see_or_touch_another_s_builds(store):
    mine = store.create("user-1")
    store.create("user-2")

    assert [b["id"] for b in store.list("user-2")] != [mine["id"]]
    with pytest.raises(BuildNotFound):
        store.get(mine["id"], "user-2")
    with pytest.raises(BuildNotFound):
        store.update(mine["id"], "user-2", {"title": "Hijacked"})
    with pytest.raises(BuildNotFound):
        store.attach(mine["id"], "user-2", "page-1")
    with pytest.raises(BuildNotFound):
        store.delete(mine["id"], "user-2")


def test_a_conversation_is_saved_and_comes_back(store):
    build = store.create("user-1")
    messages = [{"role": "user", "text": "a page for Maria's Bakery"},
                {"role": "assistant", "text": "Okay, understood."}]
    store.update(build["id"], "user-1", {"messages": messages, "title": "Maria's Bakery"})
    store.attach(build["id"], "user-1", "page-1")

    reopened = store.get(build["id"], "user-1")
    assert reopened["messages"] == messages
    assert reopened["page_id"] == "page-1"


def test_an_update_only_writes_what_it_was_given(store):
    build = store.create("user-1")
    store.update(build["id"], "user-1", {"title": "Bakery"})
    store.update(build["id"], "user-1", {"page_id": "sneaky", "messages": None})

    saved = store.get(build["id"], "user-1")
    assert saved["title"] == "Bakery"
    assert saved["page_id"] is None
