from pathlib import Path

import pytest
from jinja2 import TemplateNotFound

from services import template_renderer
from services.template_renderer import TemplateRenderer


def test_render_template(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = tmp_path / 'test.html'

    template.write_text(
        '<h1>Hello {{ name }}</h1>',
        encoding='utf-8',
    )

    monkeypatch.setattr(
        template_renderer.settings,
        'templates_dir',
        tmp_path,
    )

    renderer = TemplateRenderer()

    result = renderer.render(
        'test.html',
        name='ChessForge',
    )

    assert result == '<h1>Hello ChessForge</h1>'


def test_render_escapes_html(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = tmp_path / 'test.html'

    template.write_text(
        '<p>{{ value }}</p>',
        encoding='utf-8',
    )

    monkeypatch.setattr(
        template_renderer.settings,
        'templates_dir',
        tmp_path,
    )

    renderer = TemplateRenderer()

    result = renderer.render(
        'test.html',
        value='<script>alert("xss")</script>',
    )

    assert '<script>' not in result
    assert '&lt;script&gt;' in result


def test_render_passes_multiple_context_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = tmp_path / 'test.html'

    template.write_text(
        '{{ first }} - {{ second }}',
        encoding='utf-8',
    )

    monkeypatch.setattr(
        template_renderer.settings,
        'templates_dir',
        tmp_path,
    )

    renderer = TemplateRenderer()

    result = renderer.render(
        'test.html',
        first='Hello',
        second='World',
    )

    assert result == 'Hello - World'


def test_render_raises_when_template_does_not_exist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        template_renderer.settings,
        'templates_dir',
        tmp_path,
    )

    renderer = TemplateRenderer()

    with pytest.raises(TemplateNotFound):
        renderer.render('missing.html')
