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
│       └── <a href="#get-apiv1repertoiresrepertoire_idlines">lines/</a>
│           └── <a href="#get-apiv1repertoiresrepertoire_idlinesline_id">{line_id}</a>
│
└── training/
    └── <a href="#get-apiv1trainingsessions">sessions/</a>
        └── <a href="#get-apiv1trainingsessionssession_id">{session_id}</a>
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

Репертуар содержит две независимые версии:

* `revision` — техническая ревизия состояния дерева, используемая для optimistic locking;
* `analytic_version` — версия полного состояния дерева, используемая для привязки аналитики.

`revision` изменяется при изменении дерева.

`analytic_version` изменяется только при полной замене дерева через `PUT /api/v1/repertoires/{repertoire_id}/lines`.

Изменения только метаданных репертуара не изменяют ни `revision`, ни `analytic_version`.

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
      "revision": 4,
      "analytic_version": 2,
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

Создаёт новый пустой репертуар.

Root line при создании репертуара не создаётся автоматически.

Пустой репертуар может быть инициализирован позже через `PUT /api/v1/repertoires/{repertoire_id}/lines`.

**Input**

```json
{
  "name": "White repertoire",
  "description": "My main white repertoire",
  "side": "white"
}
```

Ограничения:

* `name` — от 1 до 40 символов;
* `description` — строка;
* `side` — `white` или `black`.

Новый репертуар создаётся со следующими начальными значениями:

```text
revision = 1
analytic_version = 1
```

**Output — `201 Created`**

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "White repertoire",
  "description": "My main white repertoire",
  "side": "white",
  "revision": 1,
  "analytic_version": 1,
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
  "revision": 2,
  "analytic_version": 1,
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-01-01T12:03:33Z"
}
```

GET не изменяет ни `revision`, ни `analytic_version`.

Если репертуар не существует или принадлежит другому пользователю, возвращается `404 Not Found`.

---

### `PATCH /api/v1/repertoires/{repertoire_id}`

Обновляет метаданные репертуара.

`side` изменить через этот endpoint нельзя.

Изменение `name` и `description` не изменяет ни `revision`, ни `analytic_version`.

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

**Output — `200 OK`**

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "Updated name",
  "description": "Updated description",
  "side": "white",
  "revision": 1,
  "analytic_version": 1,
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-01-01T12:03:33Z"
}
```

---

### `DELETE /api/v1/repertoires/{repertoire_id}`

Удаляет репертуар вместе со всеми его линиями.

Операция не изменяет версии: после удаления репертуар больше не существует.

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

Пустой репертуар не имеет root line.

Первая root line создаётся через:

```text
PUT /api/v1/repertoires/{repertoire_id}/lines
```

После инициализации репертуар содержит ровно одну root line.

Root line:

* не имеет `parent_id`;
* имеет непустой `moves`;
* не может быть создан отдельно через `POST`;
* не может быть удалён;
* сохраняет свой `id` при замене дерева через `PUT /lines`.

`moves` содержит последовательность ходов, специфичную для данной линии.

Каждая линия должна содержать хотя бы один ход.

Leaf определяется отсутствием дочерних линий.

Каждая линия имеет собственную `analytic_version`.

Она относится только к версии `moves` конкретной линии:

* создание линии → `analytic_version = 1`;
* изменение только `tag` → версия не изменяется;
* изменение `moves` → `analytic_version += 1`.

---

### `GET /api/v1/repertoires/{repertoire_id}/lines`

Возвращает дерево репертуара, начиная с root line.

Если репертуар ещё не инициализирован и root line отсутствует, возвращается `404 Not Found`.

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
  "analytic_version": 1,
  "children": [
    {
      "id": "uuid",
      "tag": "main-line",
      "moves": [
        "e7e5",
        "g1f3"
      ],
      "analytic_version": 1,
      "children": [
        {
          "id": "uuid",
          "tag": "giuoco-piano",
          "moves": [
            "b8c6",
            "f1c4"
          ],
          "analytic_version": 1,
          "children": []
        }
      ]
    }
  ]
}
```

---

### `PATCH /api/v1/repertoires/{repertoire_id}/lines`

Атомарно изменяет дерево репертуара.

Позволяет одновременно создавать, изменять и удалять линии в рамках одной операции.

Для защиты от перезаписи изменений другого клиента используется optimistic locking через `revision`.

**Input**

```json
{
  "revision": 4,
  "create": [
    {
      "line_id": "uuid",
      "parent_id": "uuid",
      "tag": "sicilian-dragon",
      "moves": [
        "e7e5",
        "g1f3"
      ]
    }
  ],
  "update": [
    {
      "line_id": "uuid",
      "tag": "main-line",
      "moves": [
        "b8c6",
        "f1c4"
      ]
    }
  ],
  "delete": [
    "uuid"
  ]
}
```

* `revision` — целое число не меньше `1`;
* `create` — список новых линий;
* `update` — список изменяемых линий;
* `delete` — список удаляемых линий.

Каждая создаваемая или изменяемая линия должна иметь непустой `moves`.

`moves` должны содержать легальные UCI-ходы относительно полной позиции ancestry.

Для `update` изменение `moves` линии с дочерними линиями запрещено.

Удаление линии удаляет её поддерево.

Root line не может быть удалена.

**Output — `204 No Content`**

```json
{
  "revision": 5
}
```

Если переданный `revision` устарел, возвращается `409 Conflict`.

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
  "analytic_version": 2,
  "children": [
    {
      "id": "uuid",
      "tag": "giuoco-piano",
      "moves": [
        "b8c6",
        "f1c4"
      ],
      "analytic_version": 1,
      "children": []
    }
  ]
}
```

GET не изменяет версии.

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
* для non-root линии длина `moves` должна быть чётной;
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
  "analytic_version": 1,
  "children": []
}
```

После успешной операции:

```text
repertoire.revision += 1
```

`repertoire.analytic_version` не изменяется.

Существующие линии не получают новых аналитических версий.

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

При этом `tag` родительской линии изменять можно:

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

**Влияние на версии**

Изменение только `tag`:

```text
repertoire.revision += 1
line.analytic_version не изменяется
repertoire.analytic_version не изменяется
```

Изменение `moves`:

```text
repertoire.revision += 1
line.analytic_version += 1
repertoire.analytic_version не изменяется
```

Если переданы одновременно `tag` и `moves`, `revision` и `line.analytic_version` увеличиваются только один раз.

**Output — `200 OK`**

```json
{
  "id": "uuid",
  "tag": "new-tag",
  "moves": [
    "e7e5",
    "g1f3"
  ],
  "analytic_version": 3,
  "children": []
}
```

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

После успешной операции:

```text
repertoire.revision += 1
```

`repertoire.analytic_version` не изменяется.

`Line.analytic_version` существующих линий также не изменяется.

Аналитика удалённых линий больше не относится к существующему дереву, поскольку соответствующие `line_id` удаляются.

Попытка удалить root line возвращает:

```text
400 Bad Request
```

Если линия не существует или не принадлежит указанному репертуару:

```text
404 Not Found
```

---

# Analytics Versioning

Аналитика привязывается к двум независимым значениям:

```text
repertoire.analytic_version
line.analytic_version
```

Для текущего анализа линии необходимо, чтобы оба значения соответствовали значениям, с которыми был построен анализ.

`repertoire.revision` для проверки валидности аналитики не используется.

`repertoire.revision` предназначен исключительно для optimistic locking и предотвращения конкурентной перезаписи дерева.

При изменении `moves` конкретной линии её `Line.analytic_version` увеличивается, поэтому аналитика этой линии становится устаревшей, не затрагивая аналитики других линий.

При полном `PUT /lines` увеличивается `Repertoire.analytic_version`, поэтому аналитика предыдущего поколения полного дерева больше не соответствует текущему поколению.

---

# Training

Тренировочная сессия — это попытка пользователя пройти выбранную последовательность ходов из репертуара.

При создании сессии Training Service получает дерево через gRPC от Repertoire Service, выбирает путь с учётом накопленной статистики и сохраняет выбранную последовательность ходов в сессии.

Статусы сессии:

* `active` — тренировка продолжается;
* `passed` — все выбранные ходы пройдены правильно;
* `failed` — пользователь допустил ошибку;
* `invalidated` — репертуар изменился после создания сессии.

---

### `GET /api/v1/training/sessions`

Возвращает список тренировочных сессий текущего пользователя.

**Input**

Опциональные параметры запроса:

```text
?page=1&status=active
```

`page` начинается с `1`.

Размер страницы — `20`.

`status` может принимать значения:

```text
active
passed
failed
invalidated
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

Создаёт тренировочную сессию.

**Input**

```json
{
  "repertoire_id": "uuid",
  "line_id": "uuid"
}
```

`line_id` является необязательным. Если он передан, он используется как начальная линия при запросе дерева у Repertoire Service.

Training Service получает дерево и текущую `revision` репертуара через gRPC.

На основе дерева и статистики пользователя выбирается последовательность линий и ходов. Выбранная последовательность сохраняется в сессии и не изменяется при последующих запросах.

**Output — `201 Created`**

```json
{
  "id": "uuid",
  "repertoire_id": "uuid",
  "line_id": "uuid",
  "status": "active",
  "repertoire_version": 1,
  "current_ply": 0,
  "created_at": "2026-01-01T12:00:00Z",
  "ended_at": null,
  "error_line_id": null,
  "error_ply": null
}
```

---

### `GET /api/v1/training/sessions/{session_id}`

Возвращает состояние тренировочной сессии.

**Input**

Параметр пути:

```text
session_id: UUID
```

**Output — `200 OK`**

```json
{
  "id": "uuid",
  "repertoire_id": "uuid",
  "line_id": "uuid",
  "status": "active",
  "repertoire_version": 7,
  "current_ply": 6,
  "created_at": "2026-01-01T12:00:00Z",
  "ended_at": null,
  "error_line_id": null,
  "error_ply": null
}
```

`current_ply` — индекс следующего ожидаемого хода в выбранной последовательности.

`repertoire_version` — ревизия репертуара, сохранённая при создании сессии.

---

### `POST /api/v1/training/sessions/{session_id}/moves`

Проверяет ход пользователя.

**Input**

Параметр пути:

```text
session_id: UUID
```

```json
{
  "move": "e2e4"
}
```

**Output — `200 OK`**

При правильном ходе:

```json
{
  "correct": true,
  "current_ply": 1,
  "status": "active"
}
```

Если это был последний правильный ход:

```json
{
  "correct": true,
  "current_ply": 7,
  "status": "passed"
}
```

При неправильном ходе:

```json
{
  "correct": false,
  "current_ply": 3,
  "status": "failed"
}
```

При каждом ходе Training Service сначала проверяет, что `repertoire_revision` не изменился.

Если текущая ревизия репертуара отличается от сохранённой в сессии, сессия становится `invalidated`, а endpoint возвращает:

```text
409 Conflict
```

Для уже завершённых (`passed`, `failed`, `invalidated`) сессий выполнение хода невозможно:

```text
409 Conflict
```

При неправильном ходе текущая сессия становится `failed`. Для линии, на которой произошла ошибка, записывается неудачная попытка. Для предыдущих успешно пройденных линий записываются успешные попытки.

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

Если репертуар не инициализирован и root line отсутствует, `GET /repertoires/{repertoire_id}/lines` также возвращает `404 Not Found`.

### `405 Method Not Allowed`

HTTP-метод не существует для данного endpoint.

### `409 Conflict`

Запрашиваемая операция конфликтует с текущим состоянием ресурса.

Для операций с Training Service:

* попытка сделать ход в неактивной сессии;
* изменение `revision` репертуара во время активной тренировочной сессии.

Для `PUT /api/v1/repertoires/{repertoire_id}/lines` используется при конфликте `revision` репертуара.

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
* `revision < 1`.

### `429 Too Many Requests`

Слишком много запросов. Ограничение с rate limiting.

### `500 Internal Server Error`

Неожиданная ошибка на стороне сервера.
