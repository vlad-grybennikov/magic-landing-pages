from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping

DEFAULT_JWT_SECRET = "mlp-dev-secret"
MODES = ("development", "production")
LLM_PROVIDERS = ("ollama", "openrouter", "stub")
STT_PROVIDERS = ("local", "openai", "groq")


class ConfigError(RuntimeError):
    pass


def listed(text: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in text.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    env: str = "development"
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "vlp-local"
    google_client_id: str = ""
    jwt_secret: str = DEFAULT_JWT_SECRET
    access_ttl_min: int = 15
    refresh_ttl_days: int = 30
    stt: str = "local"
    stt_language: str | None = "en"
    stt_model: str | None = None
    stt_api_key: str = ""
    session_ttl: float = 900.0
    max_clarifications: int = 2
    max_commands: int = 2
    command_ttl_days: int = 7
    llm: str = "ollama"
    llm_models: tuple[str, ...] = ()
    openrouter_api_key: str = ""
    images: str = ""
    icons: str = ""
    cors_origins: tuple[str, ...] = field(default=("*",))
    release: str = "dev"
    commit: str = "unknown"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if environ is None else environ

        def text(key: str, default: str) -> str:
            return env.get(key, default)

        stt = text("MLP_STT", "local").strip().lower() or "local"
        return cls(
            env=text("MLP_ENV", "development").strip().lower() or "development",
            mongo_url=text("MONGO_URL", cls.mongo_url),
            mongo_db=text("MONGO_DB", cls.mongo_db),
            google_client_id=text("GOOGLE_CLIENT_ID", "").strip(),
            jwt_secret=text("MLP_JWT_SECRET", "").strip() or DEFAULT_JWT_SECRET,
            access_ttl_min=int(text("MLP_ACCESS_TTL_MIN", "15")),
            refresh_ttl_days=int(text("MLP_REFRESH_TTL_DAYS", "30")),
            stt=stt,
            stt_language=text("MLP_STT_LANG", "en") or None,
            stt_model=text("MLP_STT_MODEL", "").strip() or None,
            stt_api_key=text(f"{stt.upper()}_API_KEY", "").strip(),
            session_ttl=float(text("MLP_SESSION_TTL", "900")),
            max_clarifications=int(text("MLP_MAX_CLARIFICATIONS", "2")),
            max_commands=int(text("MLP_MAX_COMMANDS", "2")),
            command_ttl_days=int(text("MLP_COMMAND_TTL_DAYS", "7")),
            llm=text("MLP_LLM", "ollama").strip().lower() or "ollama",
            llm_models=listed(text("MLP_LLM_MODELS", "")),
            openrouter_api_key=text("OPENROUTER_API_KEY", "").strip(),
            images=text("MLP_IMAGES", "").strip().lower(),
            icons=text("MLP_ICONS", "").strip().lower(),
            cors_origins=listed(text("MLP_CORS_ORIGINS", "*")) or ("*",),
            release=text("MLP_RELEASE", "dev").strip() or "dev",
            commit=text("MLP_COMMIT", "unknown").strip() or "unknown",
        )

    @property
    def production(self) -> bool:
        return self.env == "production"

    @property
    def auth_enabled(self) -> bool:
        return self.production or bool(self.google_client_id)

    @property
    def llm_providers(self) -> set[str]:
        return {self.llm, *(entry.partition(":")[0] for entry in self.llm_models)}

    def validate(self) -> "Settings":
        if self.env not in MODES:
            raise ConfigError(
                f"MLP_ENV must be one of {', '.join(MODES)}, not {self.env!r}.")
        unknown = self.llm_providers - set(LLM_PROVIDERS)
        if unknown:
            raise ConfigError(
                f"MLP_LLM and MLP_LLM_MODELS accept {', '.join(LLM_PROVIDERS)}, "
                f"not {', '.join(sorted(unknown))}.")
        if "openrouter" in self.llm_providers and not self.openrouter_api_key:
            raise ConfigError("OPENROUTER_API_KEY is not set.")
        if self.stt not in STT_PROVIDERS:
            raise ConfigError(
                f"MLP_STT must be one of {', '.join(STT_PROVIDERS)}, not {self.stt!r}.")
        if self.stt != "local" and not self.stt_api_key:
            raise ConfigError(f"{self.stt.upper()}_API_KEY is not set.")
        if not self.production:
            return self
        problems = []
        if not self.google_client_id:
            problems.append("GOOGLE_CLIENT_ID is not set")
        if self.jwt_secret == DEFAULT_JWT_SECRET:
            problems.append("MLP_JWT_SECRET is the development default")
        if "*" in self.cors_origins:
            problems.append("MLP_CORS_ORIGINS must list the site origins, not *")
        if problems:
            raise ConfigError(
                "Refusing to start in production: " + "; ".join(problems) + ".")
        return self
