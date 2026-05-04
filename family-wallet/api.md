# REST API

Базовый URL: `http://localhost:8000`. Документация: `/docs`.

## Авторизация

`POST /auth/login` → `{"token": "<JWT>"}`

Заголовок: `Authorization: Bearer <JWT>`

## Пользователи

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/auth/register` | `email`, `password`, `name` |
| `POST` | `/auth/login` | `email`, `password` → токен |
| `GET` | `/me` | Текущий пользователь |

## Семьи

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/families` | Создать (`name`) |
| `POST` | `/families/join` | Вступить (`code`) |
| `GET` | `/families/me` | Моя семья |
| `GET` | `/families/{id}/invite` | Код (только `owner`) |
| `GET` | `/families/{id}/members` | Участники |
| `PUT` | `/families/{id}/permissions` | Права (`user_id`, `can_manage_accounts`, `can_delete_any_transactions`) |

## Счета

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/families/{id}/accounts` | Список |
| `POST` | `/families/{id}/accounts` | Создать (`name`) |

## Транзакции

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/transactions` | Создать |
| `GET` | `/transactions?family_id=1&account_type=main` | Список |
| `DELETE` | `/transactions/{id}?family_id=1` | Удалить |

`POST /transactions` тело:

```json
{
  "family_id": 1,
  "type": "income",
  "amount": 10000,
  "category": "Зарплата",
  "description": "Аванс",
  "account_type": "main",
  "recurring_monthly": false,
  "recurring_day": 1
}