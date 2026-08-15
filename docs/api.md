[← README](../README.md)

# API

Публичное АПИ поделено на два протокола:

<style>
  a {
    color: #94d3e7;
  }
  a:hover {
    color: #609cae;
  }
</style>

- REST API: <a href="#api">/api/v1/...</a>
- WebSocket API: <a href="#websocket-api">/ws/v1/...</a>

Аутентификация использует JWT. Защищенные http endpoints требуют валидного access токена.

---

## Scheme

<pre>
/api/v1/
├── auth/
│   ├── <a href="#post-apiv1authregister">register</a>
│   ├── <a href="#post-apiv1authlogin">login</a>
│   ├── <a href="#post-apiv1authlogout">logout</a>
│   ├── tokens/
│   │   ├── <a href="#post-apiv1authtokensapproval">approval</a>
│   │   └── <a href="#post-apiv1authtokensrefresh">refresh</a>
│   ├── password/
│   │   ├── <a href="#post-apiv1authpasswordresetrequest">reset/request</a>
│   │   ├── <a href="#post-apiv1authpasswordresetconfirm">reset/confirm</a>
│   │   └── <a href="#post-apiv1authpasswordchange">change</a>
│   ├── email/
│   │   ├── <a href="#post-apiv1authemailchange">change</a>
│   │   └── <a href="#post-apiv1authemailchangeconfirm">change/confirm</a>
│   └── <a href="#get-apiv1authme">me</a>
│
├── <a href="#get-apiv1repertoires">repertoires/</a>
│   └── <a href="#get-apiv1repertoiresrepertoire_id">{repertoire_id}</a>
│       └── <a href="#get-apiv1repertoiresrepertoire_idlines">lines/</a>
│           └── <a href="#patch-apiv1repertoiresrepertoire_idlinesline_id">{line_id}</a>
│
└── training/
    ├── <a href="#get-apiv1trainingsessions">sessions/</a>
    │   └── <a href="#get-apiv1trainingsessionssession_id">{session_id}</a>
    └── <a href="#post-apiv1trainingsessionssession_idmoves">sessions/{session_id}/moves</a>


/ws/v1/
└── engine/
    └── <a href="#ws-ws-v1engineanalysis">analysis</a>
</pre>

---

# Methods

## Authentication

### `POST /api/v1/auth/register`

Регистрирует нового пользователя.

**Input**

```json
{
  "email": "user@example.com",
  "password": "string",
  "password_repeat": "string"
}
```

**Output — `201 Created`**

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "status": "pending_verification"
}
```

Код подтверждения отправлен пользователю на почту.

---

### `POST /api/v1/auth/login`

Аутентифицирует пользователя.

**Input**

```json
{
  "email": "user@example.com",
  "password": "string"
}
```

**Output — `200 OK`**

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

### `POST /api/v1/auth/logout`

Делает все refresh токены пользователя неактивными.
Текущий access token остаётся действительным до истечения срока действия.
В обычных условиях access токен теряется при перенаправлении на домашнюю страницу сайта.

**Input**

Access токен передается через заголовок Authorization: 'Bearer \<access-token\>'

**Output — `204 No Content`**

---

### `POST /api/v1/auth/tokens/approval`

Подтверждение почты через отправленный код

**Input**

```json
{
  "code": "123456"
}
```

**Output — `200 OK`**

```json
{
  "status": "approved"
}
```

---

### `POST /api/v1/auth/tokens/refresh`

Запрашивает новую пару токенов.

**Input**

**Output — `200 OK`**

```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "expires_in": 900
}
```

Refresh token устанавливается сервером в HttpOnly, Secure, Same-Site: Strict cookie.

---

## Password

### `POST /api/v1/auth/password/reset/request`

Начинает процесс восстановления пароля.

**Input**

```json
{
  "email": "user@example.com"
}
```

**Output — `202 Accepted`**

```json
{
  "status": "email_sent"
}
```

Сервис отправляет на почту код для подтверждения.

---

### `POST /api/v1/auth/password/reset/confirm`

Восстановление пароля для пользователя.

**Input**

```json
{
  "code": "123456",
  "password": "string",
  "password_repeat": "string"
}
```

**Output — `204 No Content`**

---

### `POST /api/v1/auth/password/change`

Смена пароля для авторизованного пользователя.

**Input**

```json
{
  "current_password": "string",
  "new_password": "string",
  "new_password_repeat": "string"
}
```

**Output — `204 No Content`**

---

## Email

### `POST /api/v1/auth/email/change`

Запрос на смену почты.

**Input**

```json
{
  "new_email": "new@example.com",
  "password": "string"
}
```

**Output — `202 Accepted`**

```json
{
  "status": "verification_sent"
}
```

Письмо с кодом подтверждения отправлено на почту.

---

### `POST /api/v1/auth/email/change/confirm`

Подтверждение новой почты.

**Input**

```json
{
  "code": "123456"
}
```

**Output — `204 No Content`**

---

# Users

### `GET /api/v1/auth/me`

Возвращает данные об авторизованном пользователе.

**Input**

**Output — `200 OK`**

```json
{
  "email": "user@example.com",
  "created_at": "2026-01-01T12:00:00Z"
}
```

---

### `PATCH /api/v1/auth/me`

Изменяет данные пользователя

**Input**

```json
{
  "display_name": "string"
}
```

Все поля опциональные.

**Output — `200 OK`**

```json
{
  "email": "user@example.com",
  "display_name": "string",
  "created_at": "2026-01-01T12:00:00Z"
}
```

---

# Repertoires

repertoire - коллекция дебютов и репертуаров пользователя

### `GET /api/v1/repertoires`

Возвращает репертуар авторизованного пользователя.

**Input**

Параметры запроса:

```text
/api/v1/repertoires?page=1
```

**Output — `200 OK`**

```json
{
  "items": [
    {
      "name": "White repertoire",
      "id": "uuid",
      "version": 2,
      "side": "White",
      "created_at": "2026-01-01T12:00:00Z",
      "updated_at": "2026-01-01T12:03:33Z",
    }
  ],
  "page": 1,
  "limit": 20,
  "total": 1
}
```

---

### `POST /api/v1/repertoires`

Создать новый репертуар.

**Input**

```json
{
  "name": "White repertoire",
  "description": "My main white repertoire",
  "side": "Black"
}
```

**Output — `201 Created`**

```json
{
  "name": "White repertoire",
  "id": "uuid",
  "side": "Black",
  "description": "My main white repertoire",
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-01-01T12:00:00Z"
}
```

---

### `GET /api/v1/repertoires/{repertoire_id}`

Возвращает определенный репертуар.

**Input**

Параметр пути:

```text
repertoire_id: UUID
```

**Output — `200 OK`**

```json
{
  "name": "White repertoire",
  "id": "uuid",
  "version": 2,
  "side": "Black",
  "description": "My main white repertoire",
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-01-01T12:03:33Z"
}
```

---

### `PATCH /api/v1/repertoires/{repertoire_id}`

Обновляет метаданные репертуара.

**Input**

```json
{
  "side": "Black",
  "name": "Updated name",
  "description": "Updated description"
}
```

**Output — `204 No Content`**

---

### `DELETE /api/v1/repertoires/{repertoire_id}`

Удаляет репертуар.

**Input**

Параметр пути:

```text
repertoire_id: UUID
```

**Output — `204 No Content`**

---

## Repertoire Lines

### `GET /api/v1/repertoires/{repertoire_id}/lines`

Возвращает все варианты репертуара

**Input**

Опциональные параметры запроса:

```text
?exclude_tag_regex=tag-1&exclude_tag_regex=tag-2
?exclude_tag_regex=^tag-[12]
```

Исключаются линии, соответствующие хотя бы одному регулярному выражению.

**Output — `200 OK`**

```json
{
  "items": [
    {
      "tag": "italian-main",
      "id": "uuid",
      "moves": [
        "e2e4",
        "e7e5",
        "g1f3",
        "b8c6",
        "f1c4"
      ],
      "children": [
        {
          "tag": "giuoco-piano",
          "id": "uuid",
          "moves": [
            "f8c5",
            "b2b4"
          ],
          "children": []
        },
        {
          "tag": "two-knights",
          "id": "uuid",
          "moves": [
            "g8f6",
            "f3g5"
          ],
          "children": []
        }
      ]
    }
  ]
}
```

---

### `PUT /api/v1/repertoires/{repertoire_id}/lines`

Полностью меняет вариацию в репертуаре.

**Input**

```json
{
  "items": [
    {
      "tag": "italian-main",
      "moves": [
        "e2e4",
        "e7e5",
        "g1f3",
        "b8c6",
        "f1c4"
      ],
      "children": [
        {
          "tag": "giuoco-piano",
          "moves": [
            "f8c5",
            "b2b4"
          ],
          "children": []
        },
        {
          "tag": "two-knights",
          "moves": [
            "g8f6",
            "f3g5"
          ],
          "children": []
        }
      ]
    }
  ]
}
```

**Output — `204 No Content`**

---

### `GET /api/v1/repertoires/{repertoire_id}/lines/{line_id}`

Возвращает определенную линию репертуара.

**Input**

Параметры пути:

```text
repertoire_id: UUID
line_id: UUID
```

**Output — `200 OK`**

```json
{
  "items": [
    {
      "id": "uuid",
      "tag": "italian-main",
      "moves": [
        "e2e4",
        "e7e5",
        "g1f3",
        "b8c6",
        "f1c4"
      ],
      "children": [
        {
          "id": "uuid",
          "tag": "giuoco-piano",
          "moves": [
            "f8c5",
            "b2b4"
          ],
          "children": []
        },
      ]
    }
  ]
}
```

---

### `POST /api/v1/repertoires/{repertoire_id}/lines/{line_id}`

Добавляет разветвление в репертуар относительно родительского line_id.

**Input**

Параметры пути:

```text
repertoire_id: UUID
line_id: UUID
```

```json
{
    "tag": "some-tag",
    "moves": ["e2e4", "e7e5", "g1f3"]
}
```

**Output — `204 No Content`**

---

### `DELETE /api/v1/repertoires/{repertoire_id}/lines/{line_id}`

Удаляет саму линию и всё её поддерево.

**Input**

Параметры пути:

```text
repertoire_id: UUID
line_id: UUID
```

**Output — `204 No Content`**

---

### `PATCH /api/v1/repertoires/{repertoire_id}/lines/{line_id}`

Изменяет определенную линию

**Input**

Параметры пути:

```text
repertoire_id: UUID
line_id: UUID
```

```json
{
    "tag": "new-tag",
    "moves": [
        "new-move-1",
        "new-move-2",
        ...
    ]
}
```

Все поля опциональны

**Output — `204 No Content`**

---

# Training

Тренировочная сессия представляет собой активную или завершенную попытку повторить репертуар.

### `GET /api/v1/training/sessions`

Возвращает информацию о всех сессиях пользователя.

**Input**

Опциональные параметры запроса:

```text
?status=active&page=1
```

**Output — `200 OK`**

```json
{
  "items": [
    {
      "id": "uuid",
      "status": "active",
      "created_at": "2026-01-01T12:00:00Z"
    }
  ],
  "page": 1,
  "limit": 20,
  "total": 1
}
```

---

### `POST /api/v1/training/sessions`

Создать сессию тренировки.

**Input**

```json
{
  "repertoire_id": "uuid",
  "line_id": "uuid",
  "exclude_tag_regex": [
    "^sicilian-",
    "^french-"
  ]
}
```

line_id считается фиксированной линией и не может быть исключенной.
До неё берутся родительские линии, а перед ней - наугад, но не входящие в фильтры.

**Output — `201 Created`**

```json
{
  "id": "uuid",
  "repertoire_id": "uuid",
  "line_id": "uuid",
  "status": "active",
  "created_at": "2026-01-01T12:00:00Z"
}
```

---

### `GET /api/v1/training/sessions/{session_id}`

Возвращает текущее состояние и результат тренировочной сессии.

**Input**

Параметры пути:

```text
session_id: UUID
```

**Output — `200 OK`**

```json
{
  "id": "uuid",
  "status": "invalidated",
  "line_id": "uuid",
  "repertoire_version": 7,
  "current_ply": 6,
}
```

version проверяет версии репертуара в момент создания сессии и в момент хода.
repertoire.version != training_session.repertoire_version: status -> invalidated.

---

### `POST /api/v1/training/sessions/{session_id}/moves`

Проверяет ход, сделанный пользователем.

**Input**

Параметры пути:

```text
session_id: UUID
```

```json
{
  "move": "f1c4"
}
```

**Output — `200 OK`**

```json
{
  "correct": true,
  "next_move": "g8f6",
  "current_ply": 7
}
```

Тренировочный сервис проверяет валидность хода и обновляет состояние сессии.
При неправильном ответе, сессия становится failed.

---

### `POST /api/v1/training/sessions/{session_id}/finish`

Завершает тренировку.

**Input**

**Output — `200 OK`**

```json
{
  "id": "uuid",
  "status": "completed",
  "ended_at": "2026-01-01T12:10:00Z"
}
```

---

# WebSocket API

## `WS /ws/v1/engine/analysis`

Позволяет в реальном времени получать анализ, обновляющийся во время партии.

Клиент устанавливает WebSocket соединение и отправляет позиции для анализа. Engine service с помощью движка Стокфиш стримит лучшие ходы позиции.

### Client → Server

```json
{
  "moves": ["e2e4", "e7e5", "g1f3"]
}
```

### Server → Client

Анализ позиции обновляется с течением времени.

```json
{
  "depth": 13,
  "multipv": 1,
  "score_cp": 43,
  "mate": null,
  "pv": [
    "f1b5",
    "a7a6",
    "b5a4"
  ]
}
```

Для матовой комбинации:

```json
{
  "depth": 13,
  "multipv": 1,
  "score_cp": null,
  "mate": 3,
  "pv": [
    "..."
  ]
}
```

Соединение остается открытым, пока пользователь запрашивает анализ позиции. Сервер может закрыть соединение, когда пользователь прекращает анализ.

---

# Common HTTP Responses

Защищенные урлы могут вернуть:

### `401 Unauthorized`

Access токен итёк, недоступен или подделан.

### `403 Forbidden`

У аутентифицированного пользователя нет доступа к ресурсу.

### `404 Not Found`

Запрашиваемый ресурс не существует.

### `409 Conflict`

Запрашиваемые операции конфликтуют с текущим состоянием.

### `422 Unprocessable Entity`

Тело запроса не прошло валидацию.

### `500 Internal Server Error`

Неожиданная ошибка на стороне сервера.
