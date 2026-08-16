# ChessForge

ChessForge - это веб-приложение для создания, изучения и тренировки шахматных репертуаров.

Основная идея проекта - упростить процесс обучения шахматным заготовкам и сделать его похожим на Anki или Duolingo:

1. Пользователь создаёт свой репертуар.
2. Разбирает варианты на шахматной доске.
3. Получает анализ позиции от Stockfish.
4. Сохраняет дерево вариантов.
5. Выбирает позицию, с которой хочет начать тренировку.
6. Система случайно выбирает одну из доступных линий.
7. Пользователь должен воспроизвести выбранную последовательность ходов без ошибок.

Проект также используется как практическая площадка для изучения backend-разработки, микросервисной архитектуры, gRPC, WebSockets, асинхронных задач и deployment.

## Documentation

Основная документация проекта находится в [`docs/`](docs/).

- [High level design](docs/high-level-design.md)
- [Low level design](docs/low-level-design.md)
- [API specification](docs/api.md)
- [Cyber Security](docs/security.md)

### Requirements

- [Requirements](docs/requirements.md) - функциональные требования проекта, разделённые на Must-have, Intermediate и Future Features.

### Architecture Decisions

Архитектурные решения находятся в [`docs/adr/`](docs/adr/).

- [ADR-0001 — Microservices Architecture](docs/adr/0001-microservices.md)
- [ADR-0002 — FastAPI](docs/adr/0002-fastapi.md)
- [ADR-0003 — JWT Authentication](docs/adr/0003-jwt.md)
- [ADR-0004 — gRPC](docs/adr/0004-grpc.md)
- [ADR-0005 — WebSockets](docs/adr/0005-websockets.md)
- [ADR-0006 — Redis](docs/adr/0006-redis.md)
- [ADR-0007 — RabbitMQ](docs/adr/0007-rabbitmq.md)
- [ADR-0008 — Celery](docs/adr/0008-celery.md)

## Tech Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- RabbitMQ
- Celery

### Frontend

- HTML
- CSS
- JavaScript

### Communication

- REST
- gRPC
- WebSockets

### Infrastructure

- Docker
- Nginx
- Uvicorn

### Code Quality

- ruff
- mypy
- pytest

## License

[MIT License.](LICENSE)
