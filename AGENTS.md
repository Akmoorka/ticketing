# AGENTS.md — контекст для ИИ-ассистента

Backend продажи билетов: Django 6.1 + DRF, PostgreSQL 17, Redis, Celery. Модульный монолит + отдельный эмулятор платёжного шлюза (`payments_emulator/`, появится в КТ-4).

## Команды
- Поднять всё: `docker compose up -d` (web на :8000, Mailpit на :8025).
- Тесты: `DB_USER=tracker_v3 python -m pytest -q` (локально) или `docker compose exec web python -m pytest -q`.
- **Перед каждым PR:** `DB_USER=tracker_v3 bash scripts/check_all.sh` — должно быть «ЗЕЛЁНЫЙ». Вывод вставить в описание PR.

## Раскладка внутри модуля (ступень 2)
`models / services / selectors / filters / apis / urls / tasks / tests`
- Запись — только `services.py` (транзакции, блокировки, правила). Чтение — `selectors.py`.
- `apis.py` тонкие: валидация входа, вызов сервиса или селектора, ответ. Бизнес-правил во вьюхах нет.
- Входные сериализаторы перечисляют поля явно (нельзя передать `status`, `organization_id`, `is_staff`).
- Задача Celery принимает id, а не объекты; она идемпотентна и является тонкой обёрткой над сервисом.

## Границы модулей
Зависимости идут только вниз: reports → catalog, sales, ledger, organizations; checkin → sales, organizations; payments → sales, ledger, notifications; sales → catalog, organizations, notifications; catalog → organizations, notifications; organizations → accounts, notifications; accounts → notifications; ledger и notifications — ни от кого. От `common` может зависеть любой модуль.
- Чужие `services`, `selectors`, `domain` звать можно. Чужие `models`, `apis`, `tasks` импортировать нельзя.
- Нижний модуль сообщает верхнему через outbox, а не импортом.
- `sales/domain/` — только стандартная библиотека, без django и rest_framework.
- Проверяет `scripts/check_layers.sh`.

## Запреты
- `float` для денег (только `Decimal`), время без часового пояса.
- HTTP-вызов внутри открытой транзакции (`atomic`).
- `except Exception: pass` (ошибку логируем или пробрасываем).
- Секреты в коде и в git; значения в `.env.example`.
- Правка уже применённых миграций; удаление тестов прошлых КТ.
- Мусорный ввод не должен давать 500: только 400 или 404.

## Ошибки API
Конверт `{"message", "code", "extra"}`. 400 — плохой ввод, 409 — ввод хороший, но состояние не позволяет (место занято, лимит и т.д.). Остальные коды — в разделе 6.1 ТЗ.

## Процесс
- Коммиты по Conventional Commits; каждый коммит проходит тесты (`scripts/check_history.sh`).
- В `main` только через PR, не больше ~400 строк без миграций и схемы.
- В описании PR есть раздел «Где помогал ИИ».
