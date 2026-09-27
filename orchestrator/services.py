from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from auth import Authenticator, UserStore
from builds import BuildStore
from command_service import CommandService, CommandStore
from page_service import PageService
from providers import Providers
from session import SessionStore
from settings import Settings
from storage import PageStore
from transcriber import Transcriber, build_transcriber

logger = logging.getLogger("mlp.services")


@dataclass
class Services:
    settings: Settings
    users: UserStore
    auth: Authenticator
    pages: PageStore
    builds: BuildStore
    sessions: SessionStore
    commands: CommandStore
    providers: Providers
    transcriber: Transcriber
    page_service: PageService
    command_service: CommandService
    client: Optional[object] = None

    @classmethod
    def from_db(cls, settings: Settings, db, providers: Optional[Providers] = None,
                transcriber=None, client=None, verifier=None) -> "Services":
        users = UserStore(db["users"])
        pages = PageStore(db["pages"])
        builds = BuildStore(db["builds"])
        sessions = SessionStore(db["sessions"], ttl=settings.session_ttl,
                                max_clarifications=settings.max_clarifications)
        commands = CommandStore(db["commands"], ttl_days=settings.command_ttl_days)
        providers = providers or Providers()
        transcriber = transcriber or build_transcriber(settings)
        page_service = PageService(pages, builds)
        command_service = CommandService(pages, sessions, commands, providers, transcriber,
                                         page_service, max_workers=settings.max_commands)
        return cls(settings=settings, users=users,
                   auth=Authenticator(settings, users, verifier=verifier),
                   pages=pages, builds=builds, sessions=sessions, commands=commands,
                   providers=providers, transcriber=transcriber,
                   page_service=page_service, command_service=command_service,
                   client=client)

    @classmethod
    def from_settings(cls, settings: Settings, providers: Optional[Providers] = None,
                      transcriber=None) -> "Services":
        from pymongo import MongoClient

        client = MongoClient(settings.mongo_url)
        return cls.from_db(settings, client[settings.mongo_db], providers, transcriber,
                           client=client)

    def ensure_indexes(self) -> None:
        for store in (self.users, self.pages, self.builds, self.sessions, self.commands):
            store.ensure_indexes()

    def ping(self) -> bool:
        if self.client is None:
            return True
        try:
            self.client.admin.command("ping")
            return True
        except Exception:  # noqa: BLE001
            logger.warning("mongo ping failed", exc_info=True)
            return False

    def close(self) -> None:
        self.command_service.close()
        self.transcriber.close()
        if self.client is not None:
            self.client.close()
