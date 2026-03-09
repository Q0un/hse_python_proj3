# Сервис сокращения ссылок

## Запуск

```bash
docker compose up --build
```

После запуска:
- API доступен на `http://localhost:8000`
- Swagger-документация: `http://localhost:8000/docs`

## Описание API

### Авторизация

| Метод | Эндпоинт       | Тело запроса                | Описание                       | Авторизация |
|-------|----------------|-----------------------------|--------------------------------|-------------|
| POST  | `/auth/signup` | `{"login", "password"}`     | Регистрация нового пользователя| Нет         |
| POST  | `/auth/login`  | `{"login", "password"}`     | Получение JWT-токена           | Нет         |

### Ссылки

| Метод  | Эндпоинт                 | Описание                                    | Авторизация   |
|--------|--------------------------|---------------------------------------------|---------------|
| POST   | `/links/shorten`         | Создать короткую ссылку                     | Необязательна |
| GET    | `/links/{code}`          | Переход по короткой ссылке (307 redirect)   | Нет           |
| PUT    | `/links/{code}`          | Обновить URL                                | Обязательна   |
| DELETE | `/links/{code}`          | Удалить ссылку                              | Обязательна   |
| GET    | `/links/{code}/stats`    | Статистика по ссылке                        | Нет           |
| GET    | `/links/search`          | Поиск по оригинальному URL                  | Нет           |
| GET    | `/links-expired`         | История истёкших/почищенных ссылок          | Нет           |
| POST   | `/links-cleanup`         | Почистить давно не используемые ссылки      | Обязательна   |

## Примеры запросов

### Регистрация и логин

```bash
# Регистрация
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"login": "alice", "password": "qwerty123"}'

# Логин — в ответе приходит токен
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login": "alice", "password": "qwerty123"}'
# -> {"access_token": "eyJ...", "token_type": "bearer"}
```

### Создание ссылки

```bash
# Без авторизации, автоматический код
curl -X POST http://localhost:8000/links/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/page"}'

# С кастомным alias и временем жизни (авторизованный)
curl -X POST http://localhost:8000/links/shorten \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"url": "https://example.com", "alias": "mylink", "expires_at": "2026-12-31T23:59:00Z"}'
```

### Переход по ссылке

```bash
curl -L http://localhost:8000/links/mylink
# редирект на https://example.com
```

### Статистика

```bash
curl http://localhost:8000/links/mylink/stats
```

Ответ:

```json
{
  "code": "mylink",
  "target": "https://example.com/",
  "created_at": "2026-03-09T20:15:00+00:00",
  "visited_at": "2026-03-09T21:03:00+00:00",
  "hits": 5,
  "expires_at": "2026-12-31T23:59:00+00:00",
  "active": true
}
```

### Поиск по оригинальному URL

```bash
curl "http://localhost:8000/links/search?original_url=https://example.com"
```

### Обновление ссылки

```bash
curl -X PUT http://localhost:8000/links/mylink \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"url": "https://new-target.com"}'
```

### Удаление ссылки

```bash
curl -X DELETE http://localhost:8000/links/mylink \
  -H "Authorization: Bearer <token>"
```

### История просроченных ссылок

```bash
curl http://localhost:8000/links-expired
```

### Очистка неиспользуемых ссылок

Деактивирует ссылки, к которым не обращались дольше N дней (по умолчанию 30):

```bash
curl -X POST http://localhost:8000/links-cleanup \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"days": 14}'
```

## Описание БД

Используется PostgreSQL. Таблицы создаются автоматически при запуске приложения.

### Таблица `users`

| Колонка         | Тип             | Описание                      |
|-----------------|-----------------|-------------------------------|
| `id`            | `integer` PK    | Идентификатор                 |
| `login`         | `varchar(64)`   | Логин (уникальный)            |
| `pw_hash`       | `varchar(256)`  | Хэш пароля (bcrypt)           |
| `registered_at` | `timestamptz`   | Дата регистрации              |

### Таблица `links`

| Колонка      | Тип           | Описание                                    |
|--------------|---------------|---------------------------------------------|
| `id`         | `integer` PK  | Идентификатор                               |
| `code`       | `varchar(64)` | Короткий код (уникальный, индексирован)     |
| `target`     | `text`        | Оригинальный URL (индексирован)             |
| `owner_id`   | `integer` FK  | Создатель ссылки (`NULL` — аноним)          |
| `created_at` | `timestamptz` | Дата создания                               |
| `expires_at` | `timestamptz` | Срок действия (`NULL` — бессрочно)          |
| `visited_at` | `timestamptz` | Дата последнего перехода                    |
| `hits`       | `integer`     | Счётчик переходов                           |
| `active`     | `boolean`     | Активна ли ссылка                           |

### Связи

- `links.owner_id` → `users.id` (один пользователь — много ссылок)

## Кэширование (Redis)

- **Редирект** (`GET /links/{code}`) — URL кэшируется; счётчик переходов накапливается в Redis и каждые 60 секунд пишется в PostgreSQL.
- **Статистика** (`GET /links/{code}/stats`) и **поиск** (`GET /links/search`) — ответы кэшируются на 10 минут.
- При обновлении или удалении ссылки связанный кэш сбрасывается.

## Фоновые задачи

- Каждые 60 секунд проверяются ссылки с истёкшим `expires_at` и деактивируются.
- Каждые 60 секунд счётчики переходов из Redis синхронизируются в PostgreSQL.
