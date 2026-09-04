[← README](../README.md)

# API

Публичное API поделено на два протокола:

<style>
  a {
    color: #94d3e7;
  }
  a:hover {
    color: #609cae;
  }
</style>

* REST API: <a href="#api">/api/v1/...</a>
* WebSocket API: <a href="#websocket-api">/ws/v1/...</a>

Аутентификация использует JWT. Защищенные HTTP endpoints требуют валидного access токена.

---

## Scheme

<pre>
/api/v1/
├── auth/
│   ├── <a href="#post-apiv1authregister">register</a>
│   ├── <a href="#post-apiv1authlogin">login</a>
│   ├── <a href="#post-apiv1authlogout">logout</a>
│   ├── <a href="#post-apiv1authlogout-all">logout-all</a>
│   ├── tokens/
│   │   └── <a href="#post-apiv1authtokensrefresh">refresh</a>
│   ├── password/
│   │   ├── <a href="#post-apiv1authpasswordresetrequest">reset/request</a>
│   │   ├── <a href="#post-apiv1authpasswordresetconfirm">reset/confirm</a>
│   │   └── <a href="#post-apiv1authpasswordchange">change</a>
│   ├── email/
│   │   ├── <a href="#post-apiv1authemailapproval">approval</a>
│   │   ├── <a href="#post-apiv1authemailchangerequest">change/request</a>
│   │   └── <a href="#post-apiv1authemailchangeconfirm">change/confirm</a>
│   └── <a href="#get-apiv1authme">me</a>
│
├── <a href="#get-apiv1repertoires">repertoires/</a>
│   └── <a href="#get-apiv1repertoiresrepertoire_id">{repertoire_id}</a>
│       ├── <a href="#get-apiv1repertoiresrepertoire_idlines">lines/</a>
│       │   └── <a href="#get-apiv1repertoiresrepertoire_idlinesline_id">{line_id}</a>
│       └── ...
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
````

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

Завершает текущую сессию пользователя.

Текущий refresh token становится неактивным и больше не может использоваться для получения новой пары токенов.

Текущий access token остаётся действительным до истечения срока действия.

**Input**

Refresh token передается серверу через HttpOnly, Secure, SameSite: Strict cookie.

**Output — `204 No Content`**

---

### `POST /api/v1/auth/logout-all`

Завершает все активные сессии пользователя.

Все refresh токены пользователя становятся неактивными и больше не могут использоваться для получения новых access токенов.

Текущий access token и другие уже выданные access токены остаются действительными до истечения срока действия.

**Input**

Refresh token передается серверу через HttpOnly, Secure, SameSite: Strict cookie.

**Output — `204 No Content`**

---

### `POST /api/v1/auth/tokens/refresh`

Запрашивает новую пару токенов.

**Input**

Refresh token передается через cookie.

**Output — `200 OK`**

```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "expires_in": 900
}
```

Refresh token устанавливается сервером в HttpOnly, Secure, SameSite: Strict cookie.

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

Сервис отправляет на почту код для подтверждения.

---

### `POST /api/v1/auth/password/reset/confirm`

Восстановление пароля для пользователя.

**Input**

```json
{
  "email": "user@example.com",
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

### `POST /api/v1/auth/email/approval`

Подтверждение почты через отправленный код.

**Input**

```json
{
  "code": "123456"
}
```

**Output — `204 No Content`**

---

### `POST /api/v1/auth/email/change/request`

Запрос на смену почты.

**Input**

```json
{
  "new_email": "new@example.com",
  "password": "string"
}
```

**Output — `202 Accepted`**

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

Нет.

**Output — `200 OK`**

```json
{
  "email": "user@example.com",
  "display_name": "string",
  "gender": "M",
  "country": "KZ",
  "birth_date": "2000-01-01",
  "bio": "string",
  "telegram_alias": "username",
  "created_at": "2026-01-01T12:00:00Z"
}
```

---

### `PATCH /api/v1/auth/me`

Изменяет данные пользователя.

**Input**

```json
{
  "display_name": "string"
}
```

Все поля опциональные.

Ограничения:

* display_name — от 1 до 25 символов;
* gender — M или F;
* country — двухбуквенный код страны в формате ISO 3166-1 alpha-2;
* birth_date — дата рождения; допускается возраст примерно от 6 до 100 лет;
* bio — от 1 до 75 символов;
* telegram_alias — от 5 до 32 символов, начинается с буквы и содержит только латинские буквы, цифры и `_`;
* `null` можно передать для очистки значения;
* если поле не передано, его значение не изменяется.

**Output — `200 OK`**

```json
{
  "email": "user@example.com",
  "display_name": "string",
  "gender": "M",
  "country": "KZ",
  "birth_date": "2000-01-01",
  "bio": "string",
  "telegram_alias": "username",
  "created_at": "2026-01-01T12:00:00Z"
}
```

---

# Repertoires

`repertoire` — коллекция дебютов и репертуаров пользователя.

Каждый репертуар принадлежит одному пользователю.

Ownership определяется по JWT. `user_id` не передаётся клиентом при создании или изменении ресурса.

`side` задаётся при создании репертуара и после этого не изменяется.

Изменения структуры линий увеличивают `version` репертуара. Изменения метаданных репертуара `version` не увеличивают.

---

### `GET /api/v1/repertoires`

Возвращает репертуары авторизованного пользователя.

**Input**

Параметр запроса:

```text
/api/v1/repertoires?page=1
```

`page` начинается с `1`.

Размер страницы — `20`.

**Output — `200 OK`**

```json
{
  "items": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "name": "White repertoire",
      "description": "My main white repertoire",
      "side": "white",
      "version": 1,
      "created_at": "2026-01-01T12:00:00Z",
      "updated_at": "2026-01-01T12:03:33Z"
    }
  ],
  "page": 1,
  "pages": 1
}
```

---

### `POST /api/v1/repertoires`

Создаёт новый репертуар.

При создании автоматически создаётся единственная root line репертуара.

Root line нельзя создать отдельно через API.

**Input**

```json
{
  "name": "White repertoire",
  "description": "My main white repertoire",
  "side": "white",
  "root_moves": [
    "e2e4"
  ]
}
```

Ограничения:

* `name` — от 1 до 40 символов;
* `description` — строка;
* `side` — `white` или `black`;
* `root_moves` — непустой список UCI ходов;
* каждый move должен соответствовать синтаксису UCI;
* каждый move должен быть легальным относительно текущей шахматной позиции;
* для `white` длина `root_moves` должна быть нечётной;
* для `black` длина `root_moves` должна быть чётной.

Root line создаётся внутри той же транзакции, что и repertoire.

**Output — `201 Created`**

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "White repertoire",
  "description": "My main white repertoire",
  "side": "white",
  "version": 1,
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-01-01T12:00:00Z"
}
```

---

### `GET /api/v1/repertoires/{repertoire_id}`

Возвращает определённый репертуар.

**Input**

Параметр пути:

```text
repertoire_id: UUID
```

**Output — `200 OK`**

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "White repertoire",
  "description": "My main white repertoire",
  "side": "white",
  "version": 2,
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-01-01T12:03:33Z"
}
```

Если репертуар не существует или принадлежит другому пользователю, возвращается `404 Not Found`.

---

### `PATCH /api/v1/repertoires/{repertoire_id}`

Обновляет метаданные репертуара.

`side` изменить через этот endpoint нельзя.

**Input**

Все поля опциональные:

```json
{
  "name": "Updated name",
  "description": "Updated description"
}
```

Поддерживаются следующие варианты:

```json
{}
```

Ничего не изменяет.

```json
{
  "name": "Updated name"
}
```

Изменяет только имя.

```json
{
  "description": null
}
```

Очищает description, устанавливая его в пустую строку.

```json
{
  "description": ""
}
```

Также очищает description.

Если поле не передано, его значение не изменяется.

Ограничения:

* `name` — от 1 до 40 символов;
* `description` — строка или `null`.

`version` при изменении метаданных не увеличивается.

**Output — `200 OK`**

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "Updated name",
  "description": "Updated description",
  "side": "white",
  "version": 1,
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-01-01T12:03:33Z"
}
```

---

### `DELETE /api/v1/repertoires/{repertoire_id}`

Удаляет репертуар вместе со всеми его линиями.

**Input**

Параметр пути:

```text
repertoire_id: UUID
```

**Output — `204 No Content`**

Если репертуар не существует или принадлежит другому пользователю, возвращается `404 Not Found`.

---

# Repertoire Lines

Линии образуют дерево внутри репертуара.

Каждый репертуар имеет ровно один root line.

Root line:

* создаётся автоматически вместе с repertoire;
* не имеет `parent_id`;
* имеет непустой `moves`;
* не может быть создан отдельно;
* не может быть удалён;
* сохраняет свой `id` при замене дерева через `PUT /lines`.

`moves` содержит последовательность ходов, специфичную для данной линии.

Каждая линия должна содержать хотя бы один ход.

Leaf определяется отсутствием дочерних линий.

Пример:

```text
root [e2e4]
├── main-line [e7e5, g1f3]
│   ├── giuoco-piano [b8c6, f1c4]
│   └── two-knights [g8f6, f3g5]
│
└── scotch [e7e5, d2d4]
    └── variation [e5d4, g1f3]
```

Для каждой линии:

* `moves` не может быть пустым;
* каждый move должен соответствовать синтаксису UCI;
* каждый move должен быть легальным относительно полной позиции ancestry;
* для `white` длина `moves` должна быть нечётной;
* для `black` длина `moves` должна быть чётной.

---

### `GET /api/v1/repertoires/{repertoire_id}/lines`

Возвращает дерево репертуара, начиная с root line.

**Input**

Параметр пути:

```text
repertoire_id: UUID
```

Query parameters отсутствуют.

**Output — `200 OK`**

```json
{
  "id": "uuid",
  "tag": null,
  "moves": [
    "e2e4"
  ],
  "children": [
    {
      "id": "uuid",
      "tag": "main-line",
      "moves": [
        "e7e5",
        "g1f3"
      ],
      "children": [
        {
          "id": "uuid",
          "tag": "giuoco-piano",
          "moves": [
            "b8c6",
            "f1c4"
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

Полностью заменяет содержимое дерева репертуара.

Root line сохраняет свой существующий `id`. Его `tag` и `moves`, а также все дочерние линии заменяются содержимым запроса.

Операция выполняется атомарно.

Для защиты от перезаписи изменений другого клиента используется optimistic locking через `version`.

**Input**

```json
{
  "version": 1,
  "tree": {
    "tag": null,
    "moves": [
      "e2e4"
    ],
    "children": [
      {
        "tag": "main-line",
        "moves": [
          "e7e5",
          "g1f3"
        ],
        "children": [
          {
            "tag": "giuoco-piano",
            "moves": [
              "b8c6",
              "f1c4"
            ],
            "children": []
          }
        ]
      }
    ]
  }
}
```

Ограничения:

* `version` — целое число не меньше `1`;
* `tree` представляет root line;
* `tree.moves` — непустой список;
* `children` может быть пустым;
* каждая линия дерева должна иметь непустой `moves`;
* каждый move должен соответствовать синтаксису UCI;
* каждый move должен быть легальным относительно полной позиции ancestry;
* для `white` длина `moves` каждой линии должна быть нечётной;
* для `black` длина `moves` каждой линии должна быть чётной.

Перед изменением базы данных всё входное дерево полностью валидируется.

После валидации сервер повторно проверяет актуальную `version` репертуара внутри транзакции.

Если переданная версия отличается от актуальной версии репертуара, дерево не изменяется.

**Output — `204 No Content`**

После успешной операции `repertoire.version` увеличивается ровно на `1`.

**Output — `409 Conflict`**

Возвращается, если переданная версия устарела.

```text
Repertoire version conflict
```

Например:

```text
Client version: 5
Current version: 6
        ↓
409 Conflict
```

В этом случае никакие изменения дерева не применяются.

---

### `GET /api/v1/repertoires/{repertoire_id}/lines/{line_id}`

Возвращает поддерево, начинающееся с указанной линии.

**Input**

Параметры пути:

```text
repertoire_id: UUID
line_id: UUID
```

**Output — `200 OK`**

```json
{
  "id": "uuid",
  "tag": "main-line",
  "moves": [
    "e7e5",
    "g1f3"
  ],
  "children": [
    {
      "id": "uuid",
      "tag": "giuoco-piano",
      "moves": [
        "b8c6",
        "f1c4"
      ],
      "children": []
    }
  ]
}
```

Если линия не существует или не принадлежит указанному репертуару, возвращается `404 Not Found`.

---

### `POST /api/v1/repertoires/{repertoire_id}/lines/{line_id}`

Добавляет дочернюю линию относительно указанного `line_id`.

Root line через этот endpoint создать нельзя.

**Input**

Параметры пути:

```text
repertoire_id: UUID
line_id: UUID
```

```json
{
  "tag": "main-line",
  "moves": [
    "e7e5",
    "g1f3"
  ]
}
```

Ограничения:

* `moves` — непустой список;
* каждый move должен соответствовать синтаксису UCI;
* каждый move должен быть легальным относительно позиции после ancestry родительской линии;
* для `white` длина `moves` должна быть нечётной;
* для `black` длина `moves` должна быть чётной;
* `tag` может быть `null`.

**Output — `201 Created`**

```json
{
  "id": "uuid",
  "tag": "main-line",
  "moves": [
    "e7e5",
    "g1f3"
  ],
  "children": []
}
```

После успешной операции `repertoire.version` увеличивается на `1`.

---

### `PATCH /api/v1/repertoires/{repertoire_id}/lines/{line_id}`

Изменяет определённую линию.

**Input**

Все поля опциональные:

```json
{
  "tag": "new-tag",
  "moves": [
    "e7e5",
    "g1f3"
  ]
}
```

Пустой PATCH допустим:

```json
{}
```

и не изменяет линию.

`tag: null` очищает tag:

```json
{
  "tag": null
}
```

`moves` при передаче должен быть непустым.

### Ограничение изменения moves

Изменение `moves` разрешено только для leaf line.

Если у линии существуют дочерние линии, её `moves` нельзя изменять.

Например:

```text
line_a [e4, e5]
└── line_b [Nf3, Nc6]
```

Пока `line_b` существует:

```json
{
  "moves": [
    "d2d4"
  ]
}
```

для `line_a` недопустим.

При этом `tag` родительской линии менять можно:

```json
{
  "tag": "new-tag"
}
```

После удаления всех дочерних линий `moves` линии снова можно изменить.

Каждый новый move должен быть:

* синтаксически корректным UCI;
* легальным относительно полной позиции ancestry;
* согласованным с parity-правилом repertoire.

**Output — `200 OK`**

```json
{
  "id": "uuid",
  "tag": "new-tag",
  "moves": [
    "e7e5",
    "g1f3"
  ],
  "children": []
}
```

После изменения линии `repertoire.version` увеличивается на `1`.

---

### `DELETE /api/v1/repertoires/{repertoire_id}/lines/{line_id}`

Удаляет указанную child line и всё её поддерево.

Root line удалить нельзя.

Удаление subtree выполняется каскадно.

**Input**

Параметры пути:

```text
repertoire_id: UUID
line_id: UUID
```

**Output — `204 No Content`**

После успешной операции `repertoire.version` увеличивается на `1`.

Попытка удалить root line возвращает:

```text
400 Bad Request
```

Если линия не существует или не принадлежит указанному репертуару:

```text
404 Not Found
```

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

Создаёт сессию тренировки.

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

`line_id` считается фиксированной линией и не может быть исключённой.

До неё берутся родительские линии, а перед ней — наугад, но не входящие в фильтры.

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
  "current_ply": 6
}
```

Версия проверяет состояние репертуара в момент создания сессии и в момент хода.

Если:

```text
repertoire.version != training_session.repertoire_version
```

сессия получает статус `invalidated`.

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

При неправильном ответе сессия становится `failed`.

---

### `POST /api/v1/training/sessions/{session_id}/finish`

Завершает тренировку.

**Input**

Нет.

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

Клиент устанавливает WebSocket соединение и отправляет позиции для анализа. Engine service с помощью движка Stockfish стримит лучшие ходы позиции.

### Client → Server

```json
{
  "moves": [
    "e2e4",
    "e7e5",
    "g1f3"
  ]
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

Соединение остаётся открытым, пока пользователь запрашивает анализ позиции. Сервер может закрыть соединение, когда пользователь прекращает анализ.

---

# Common HTTP Responses

Защищённые URL могут вернуть:

### `400 Bad Request`

Запрос некорректен или нарушает бизнес-правила.

Например:

* попытка удалить root line;
* попытка изменить `moves` линии, у которой есть children;
* попытка изменить `moves` с нарушением domain rules;
* попытка передать нелегальную шахматную последовательность.

### `401 Unauthorized`

Access токен отсутствует, недействителен или истёк.

### `403 Forbidden`

Используется только для случаев, когда ресурс существует, но политика доступа явно запрещает операцию.

Для repertoire/line ресурсов отсутствие доступа к чужому ресурсу не раскрывается и возвращается как `404 Not Found`.

### `404 Not Found`

Запрашиваемый ресурс не существует или недоступен текущему пользователю.

Для repertoire/line ресурсов это также используется, когда ресурс существует, но принадлежит другому пользователю.

### `405 Method Not Allowed`

HTTP-метод не существует для данного endpoint.

### `409 Conflict`

Запрашиваемая операция конфликтует с текущим состоянием ресурса.

Для `PUT /api/v1/repertoires/{repertoire_id}/lines` используется при конфликте версии репертуара.

### `415 Unsupported Media Type`

Неправильный формат передаваемого тела.

### `422 Unprocessable Entity`

Тело запроса не прошло Pydantic validation.

Например:

* некорректный UUID;
* неверный формат UCI move;
* пустой `moves`;
* превышена максимальная длина `tag`;
* некорректное значение `side`;
* `version < 1`.

### `429 Too Many Requests`

Слишком много запросов. Ограничение с rate limiting.

### `500 Internal Server Error`

Неожиданная ошибка на стороне сервера.
