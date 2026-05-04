# Модель данных (текущая реализация)

БД — **SQLite**. Описание соответствует SQLAlchemy-моделям в `backend/app/models.py`. Таблицы создаются при старте приложения (`create_all`), плюс миграции в `main.py`.

## Диаграмма связей (упрощённо)

```mermaid
erDiagram
    users ||--o{ memberships : ""
    families ||--o{ memberships : ""
    users ||--o{ transactions : ""
    families ||--o{ transactions : ""
    families ||--o{ accounts : ""
    families ||--o{ savings_goals : ""
    families ||--o{ recurring_payments : ""
    families ||--o{ audit_logs : ""
    users ||--o{ recurring_payments : ""

    users {
        int id PK
        string email UK
        string password_hash
        string name
    }

    families {
        int id PK
        string name
        string invite_code UK
        int owner_id FK
    }

    memberships {
        int id PK
        int user_id FK
        int family_id FK
        string role
    }

    family_permissions {
        int id PK
        int user_id FK
        int family_id FK
        bool can_manage_accounts
        bool can_delete_any_transactions
    }

    accounts {
        int id PK
        int family_id FK
        string name
        bool is_default
        int created_by_user_id FK
    }

    transactions {
        int id PK
        string type
        float amount
        string category
        string description
        string account_type
        bool is_recurring_generated
        date date
        datetime created_at
        int user_id FK
        int family_id FK
    }

    savings_goals {
        int id PK
        int family_id FK
        string title
        float target_amount
        int deadline_year
        int deadline_month
        string account_type
    }

    recurring_payments {
        int id PK
        int family_id FK
        int user_id FK
        float amount
        string category
        string description
        string account_type
        int day_of_month
        bool active
        date last_generated_on
    }

    audit_logs {
        int id PK
        int family_id FK
        int actor_user_id FK
        string action
        string details
        datetime created_at
    }