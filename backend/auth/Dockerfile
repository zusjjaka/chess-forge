FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install uv \
    && uv sync --frozen

COPY . .

EXPOSE 8000

CMD ["uv", "run", "fastapi", "run", "main.py", "--port", "8000"]
