[← README](../../README.md)

# ADR-0002: FastAPI

FastAPI выбран вместо Django/DRF для получения практического опыта с современным ASGI-фреймворком и Python асинхронностью.

Дополнительные причины:

- встроенная поддержка OpenAPI;
- Pydantic;
- удобная работа с async/await;
- WebSocket support;
- распространённость FastAPI в современных Python проектах.

Для работы с PostgreSQL будет использоваться SQLAlchemy и Alembic.
