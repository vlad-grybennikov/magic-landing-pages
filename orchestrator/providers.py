from __future__ import annotations

from typing import Optional


class Providers:
    def __init__(self, lang=None, images=None, icons=None, models=None):
        self._lang = lang
        self._images = images
        self._icons = icons
        self._models = models

    @property
    def models(self):
        if self._models is None:
            from llm import LanguageModels
            self._models = LanguageModels.from_env(self._lang)
        return self._models

    @property
    def lang(self):
        if self._lang is None:
            self._lang = self.models.default
        return self._lang

    @lang.setter
    def lang(self, value) -> None:
        self._lang = value
        self._models = None

    @property
    def images(self):
        if self._images is None:
            from image_selector import build_image_service
            self._images = build_image_service()
        return self._images

    @images.setter
    def images(self, value) -> None:
        self._images = value

    @property
    def icons(self):
        if self._icons is None:
            from icon_selector import build_icon_service
            self._icons = build_icon_service()
        return self._icons

    @icons.setter
    def icons(self, value) -> None:
        self._icons = value

    def configure(self, lang=None, images=None, icons=None) -> "Providers":
        if lang is not None:
            self.lang = lang
        if images is not None:
            self._images = images
        if icons is not None:
            self._icons = icons
        return self

    def for_model(self, model_id: Optional[str]) -> "Providers":
        if not model_id or model_id == self.models.default_id:
            return self
        return Providers(lang=self.models.get(model_id), images=self.images,
                         icons=self.icons, models=self.models)

    def loaded(self) -> dict[str, bool]:
        return {"lang": self._lang is not None, "images": self._images is not None,
                "icons": self._icons is not None}

    def warm(self) -> "Providers":
        self.lang, self.images, self.icons  # noqa: B018
        return self


DEFAULT = Providers()


def resolve(providers: Optional[Providers]) -> Providers:
    return DEFAULT if providers is None else providers
