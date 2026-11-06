# Ticketing

Backend сервиса продажи билетов на концерты, спектакли и митапы: Django 6.1 + DRF, PostgreSQL 17, Redis, Celery. Модульный монолит плюс отдельный эмулятор платёжного шлюза (появится в КТ-4).

## Запуск за 10 минут

Нужны Docker и Docker Compose.

```bash
git clone https://github.com/Akmoorka/ticketing.git
cd ticketing
cp .env.example .env
docker compose up -d --build
```

Первая сборка занимает несколько минут. Проверка:

```bash
docker compose ps
curl http://localhost:8000/health/live/
curl http://localhost:8000/health/ready/
```

| Что | Адрес |
|---|---|
| API | http://localhost:8000/api/v1/ |
| Swagger UI | http://localhost:8000/api/v1/docs/ |
| Схема OpenAPI | http://localhost:8000/api/v1/schema/ |
| Письма (Mailpit) | http://localhost:8025 |

Демо-данные (`manage.py seed_demo`) появятся вместе с моделями в КТ-1.

Стенд с HTTPS: ссылка появится после первого деплоя.

## Тесты и проверки

В контейнере:

```bash
docker compose exec web python -m pytest -q
```

Локально (нужны venv, PostgreSQL и пользователь с правом создавать базы):

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
DB_USER=<пользователь> python -m pytest -q
```

Перед каждым PR запускается один скрипт со всеми проверками (Django check, тесты, миграции, границы модулей, актуальность `openapi.yaml`, история коммитов):

```bash
DB_USER=<пользователь> bash scripts/check_all.sh
```

## Устройство проекта

- [AGENTS.md](AGENTS.md): правила слоёв, границы модулей, запреты.
- [docs/architecture.md](docs/architecture.md): сервисы, зависимости модулей, порядок блокировок.
- [docs/adr/](docs/adr/): принятые решения и их цена.
- [CHANGELOG.md](CHANGELOG.md): что вошло в каждый релиз.
