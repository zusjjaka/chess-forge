[← README](../README.md)

# Exceptions

## HTTP Statuses

### `400 Bad Request`

Запрос некорректен и не может быть обработан сервером. Нарушены правила или бизнес-логика приложения.

### `401 Unauthorized`

Access token или refresh token отсутствует, недействителен, истёк или был повторно использован.

### `403 Forbidden`

Аутентифицированный пользователь не имеет доступа к операции.

### `404 Not Found`

Запрашиваемый ресурс не существует.

Для repertoire/line ресурсов также используется, если ресурс существует, но принадлежит другому пользователю.

### `405 Method Not Allowed`

HTTP-метод не поддерживается для данного endpoint.

### `409 Conflict`

Операция конфликтует с текущим состоянием ресурса.

Для Repertoire Service используется, в частности, при конфликте `revision` во время замены дерева.

### `415 Unsupported Media Type`

Неподдерживаемый формат передаваемого тела запроса.

### `422 Unprocessable Entity`

Тело запроса не прошло валидацию.

### `429 Too Many Requests`

Слишком много запросов. Превышен лимит rate limiting.

### `500 Internal Server Error`

Неожиданная ошибка на стороне сервера.

---

# Python Custom Exceptions — Auth service

### `UserAlreadyExistError`

Ошибка возникает при попытке создать пользователя с email, который уже существует в базе данных.

Используется для предотвращения создания нескольких пользователей с одинаковым email.

**HTTP Response — `409 Conflict`**

---

### `InvalidCredentialsError`

Ошибка возникает при передаче неверных учётных данных при аутентификации пользователя.

Используется при попытке входа с неверным email или паролем.

**HTTP Response — `401 Unauthorized`**

---

### `InvalidAccessTokenError`

Ошибка возникает при использовании недействительного access token или если пользователь, указанный в токене, не существует.

Используется для обработки ошибок аутентификации через access token.

**HTTP Response — `401 Unauthorized`**

---

### `RefreshTokenExpiredError`

Ошибка возникает при попытке использовать истёкший refresh token.

Используется для предотвращения обновления access token с помощью просроченного refresh token.

**HTTP Response — `401 Unauthorized`**

---

### `RefreshTokenReuseError`

Ошибка возникает при обнаружении повторного использования refresh token, который уже был использован.

Используется для обнаружения потенциальной компрометации refresh token.

**HTTP Response — `401 Unauthorized`**

---

### `RefreshTokenInvalidError`

Ошибка возникает при использовании недействительного refresh token.

Используется, когда refresh token отсутствует в базе данных или не может быть использован.

**HTTP Response — `401 Unauthorized`**

---

### `EmailNotConfirmedError`

Ошибка возникает, когда пользователь пытается выполнить операцию, требующую подтверждённого email, до прохождения верификации.

Используется для ограничения доступа к функциям, доступным только пользователям с подтверждённым email.

**HTTP Response — `403 Forbidden`**

---

### `VerificationCodeInvalidError`

Ошибка возникает при передаче неверного или истёкшего кода подтверждения.

Используется при подтверждении email, смене email и восстановлении пароля.

**HTTP Response — `400 Bad Request`**

---

### `PasswordInvalidError`

Ошибка возникает при передаче неверного текущего пароля.

Используется при смене пароля и смене email.

**HTTP Response — `400 Bad Request`**

---

### `EmailSameError`

Ошибка возникает при попытке изменить email на адрес, который совпадает с текущим email пользователя.

**HTTP Response — `400 Bad Request`**

---

# Python Custom Exceptions — Repertoires service

### `RepertoireNotFoundError`

Ошибка возникает, когда запрашиваемый репертуар не существует или недоступен текущему пользователю.

Используется для получения и изменения репертуара, а также при работе с его линиями.

**HTTP Response — `404 Not Found`**

---

### `LineNotFoundError`

Ошибка возникает, когда запрашиваемая линия не существует или не принадлежит указанному репертуару.

Используется при получении, изменении и удалении линии, а также при добавлении дочерней линии.

**HTTP Response — `404 Not Found`**

---

### `RootLineDeletionError`

Ошибка возникает при попытке удалить root line репертуара.

Root line создаётся при первой полной инициализации дерева через `PUT /api/v1/repertoires/{repertoire_id}/lines` и не может быть удалён отдельно.

**HTTP Response — `400 Bad Request`**

---

### `ParentLineMovesUpdateError`

Ошибка возникает при попытке изменить `moves` линии, у которой существуют дочерние линии.

Изменение `moves` родительской линии может изменить позицию, относительно которой интерпретируются все дочерние варианты. Поэтому `moves` такой линии нельзя изменять, пока существуют её children.

При этом `tag` родительской линии изменять разрешено.

После удаления всех дочерних линий `moves` линии снова можно изменить.

**HTTP Response — `400 Bad Request`**

---

### `RepertoireRevisionConflictError`

Ошибка возникает при попытке заменить дерево репертуара с использованием устаревшей `revision`.

Используется optimistic locking для:

```text
PUT /api/v1/repertoires/{repertoire_id}/lines
```

Клиент передаёт ревизию репертуара, которую он получил перед изменением:

```json
{
  "revision": 5,
  "tree": {
    "tag": null,
    "moves": [
      "e2e4"
    ],
    "children": []
  }
}
```

Если текущая ревизия репертуара уже изменилась:

```text
requested revision != current revision
```

изменения дерева не применяются.

**HTTP Response — `409 Conflict`**

```text
Repertoire revision conflict
```

---

### `InvalidLineMovesError`

Ошибка возникает, когда переданная последовательность ходов линии нарушает правила домена.

Проверяются:

* синтаксис UCI;
* легальность ходов относительно текущей позиции;
* соответствие стороне, которая делает ход;
* допустимое количество ходов для root line;
* допустимое количество ходов для non-root line.

**HTTP Response — `400 Bad Request`**

---

### `RootLineAlreadyExistsError`

Ошибка возникает при попытке создать более одной root line для одного репертуара.

Root line определяется как линия с `parent_id = NULL`.

**HTTP Response — `409 Conflict`**

---

### `InvalidLineRelationshipError`

Ошибка возникает при попытке создать дочернюю линию, у которой `parent_id` указывает на линию из другого репертуара.

Связь `repertoire_id + parent_id` защищается составным PostgreSQL Foreign Key.

**HTTP Response — `409 Conflict`**

---

### `DatabaseCheckConstraintError`

Ошибка возникает при нарушении PostgreSQL CHECK constraint.

В частности, линия не может содержать пустой список `moves`.

**HTTP Response — `422 Unprocessable Entity`**

---

### `DatabaseConnectionError`

Ошибка возникает при недоступности PostgreSQL.

**HTTP Response — `503 Service Unavailable`**

---

### `DatabaseError`

Ошибка возникает при неожиданной ошибке базы данных.

**HTTP Response — `500 Internal Server Error`**
