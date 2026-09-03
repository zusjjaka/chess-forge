from jinja2 import (
    Environment,
    FileSystemLoader,
)

from core.config import get_settings

settings = get_settings()


class TemplateRenderer:
    def __init__(self) -> None:
        templates_dir = settings.templates_dir
        self._environment = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=True,
        )

    def render(
        self,
        template_name: str,
        **context: str,
    ) -> str:
        template = self._environment.get_template(template_name)

        return template.render(**context)
