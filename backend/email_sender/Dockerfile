FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install uv \
    && uv sync --frozen

COPY . .

CMD ["uv", "run", "celery", "-A", "core.celery:celery_app", "worker", "--loglevel=INFO"]
