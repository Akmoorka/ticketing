# Changelog

Формат: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версии по [SemVer](https://semver.org/lang/ru/).

## [Unreleased]

### Added
- Каркас проекта: Django 6.1, настройки `base`/`dev`/`test`/`prod`, pytest.
- `docker-compose.yml`: web (gunicorn), worker, beat, db (PostgreSQL 17), redis, mailpit.
- Логи с `request_id` и заголовок `X-Request-ID`.
- Проверки здоровья `/health/live/` и `/health/ready/`.
- Swagger UI `/api/v1/docs/` и схема OpenAPI.
- Скрипты `check_all.sh`, `check_layers.sh`, `check_history.sh`.
- `AGENTS.md`, `docs/architecture.md` и первые четыре ADR.
