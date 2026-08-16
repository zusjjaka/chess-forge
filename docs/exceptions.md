[← README](../README.md)

# Exceptions

## HTTP Statuses

### `400 Bad Request`

Запрос некорректен и не может быть обработан сервером. Нарушение правил или бизнес логики.

### `401 Unauthorized`

Access токен отсутствует, недействителен или истёк.

### `403 Forbidden`

У аутентифицированного пользователя нет доступа к ресурсу.

### `404 Not Found`

Запрашиваемый ресурс не существует.

### `405 Method Not Allowed`

HTTP-Метод не существует для данного endpoint.

### `409 Conflict`

Запрашиваемые операции конфликтуют с текущим состоянием.

### `415 Unsopported Media Type`

Неправильный формат передаваемого тела.

### `422 Unprocessable Entity`

Тело запроса не прошло валидацию.

### `429 Too Mant Requests`

Слишком много запросов. Ограничение с rate limiting.

### `500 Internal Server Error`

Неожиданная ошибка на стороне сервера.

## Python Custom Exceptions

### ...will be updated in future...
