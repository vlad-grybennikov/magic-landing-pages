from __future__ import annotations

from pymongo import MongoClient

from pipeline import CommandContext, PipelineError
from providers import Providers
from schema import Page
from services import Services
from settings import Settings
from tatl.adapter import AgentAdapter, ComponentProbes, EpisodeOutcome
from tatl.annotations import TaskAnnotation
from transcriber import ScriptedTranscriber

OWNER = "tatl"


class MlpProbes(ComponentProbes):
    def __init__(self, lang, images=None):
        self.lang = lang
        self.images = images

    def classify(self, utterance: str) -> tuple[str, dict]:
        interp = self.lang.interpret(utterance)
        args = interp.args
        return interp.intent, args.model_dump() if hasattr(args, "model_dump") else dict(args)

    def plan_sections(self, slots: dict, instruction: str):
        brief = {
            "business": slots.get("business", "The Business"),
            "audience": slots.get("audience", "customers"),
            "goal": slots.get("goal", "generate enquiries"),
            "tone": None,
        }
        return self.lang.generate_schema(brief, instruction)

    def _ranked(self, query: str, k: int, field: str):
        from image_selector import CLIPImageService

        if not isinstance(self.images, CLIPImageService):
            return None
        return [choice.get(field) for choice in self.images.rank(query, k=k)]

    def rank_images(self, query: str, k: int):
        return self._ranked(query, k, "id")

    def rank_categories(self, query: str, k: int):
        return self._ranked(query, k, "category")


class MlpAdapter(AgentAdapter):
    def __init__(self, name: str | None = None, providers: Providers | None = None,
                 settings: Settings | None = None, client=None):
        self.settings = settings or Settings.from_env()
        self.providers = (providers or Providers()).warm()
        self.name = name or getattr(self.providers.lang, "model", "stub")
        self._client = client or MongoClient(self.settings.mongo_url)

    def services_for(self, db_name: str) -> Services:
        services = Services.from_db(self.settings, self._client[db_name], self.providers,
                                    ScriptedTranscriber())
        services.ensure_indexes()
        return services

    def run_episode(self, task: TaskAnnotation, run_index: int) -> EpisodeOutcome:
        db_name = f"vlp-tatl-{task.id}-{run_index}"
        self._client.drop_database(db_name)
        services = self.services_for(db_name)
        try:
            return run_task(services, task)
        finally:
            services.command_service.close()
            self._client.drop_database(db_name)

    def probes(self) -> MlpProbes:
        return MlpProbes(self.providers.lang, self.providers.images)

    def close(self) -> None:
        self._client.close()


class DeterministicAdapter(MlpAdapter):
    def __init__(self, name: str | None = None, settings: Settings | None = None,
                 client=None):
        from icon_selector import build_icon_service
        from image_selector import StubImageService
        from oracle import FixtureLanguageService

        super().__init__(name or "fixture-oracle",
                         Providers(lang=FixtureLanguageService(),
                                   images=StubImageService(),
                                   icons=build_icon_service()),
                         settings, client)


def run_task(services: Services, task: TaskAnnotation) -> EpisodeOutcome:
    page_id = None
    for page in task.setup_pages:
        doc = services.pages.create(Page(**page), OWNER)
        page_id = page_id or doc["_id"]

    initial = services.pages.snapshot()
    rejected_at = None
    ctx = CommandContext(page_id=page_id, owner=OWNER)
    try:
        result = services.command_service.execute(task.instruction, "en", ctx,
                                                  keep_trace=True)
        trace = result["_trace"]
    except PipelineError as e:
        trace = e.trace
        rejected_at = e.stage

    trace["initial_snapshot"] = initial
    trace["final_snapshot"] = services.pages.snapshot()
    return EpisodeOutcome(trace=trace, rejected_at=rejected_at)
