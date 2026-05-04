# Локальная разработка

## Требования

- Python 3.11+
- SQLite


## Фронтэнд
```bash
cd frontend
python -m http.server 5174
```

## Бэкенд
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # или .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
## Тестирование
```bash
cd backend
source .venv/bin/activate
pytest -q
```

## Структура

family-wallet/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── database.py
│   │   ├── auth.py
│   │   ├── dependencies.py
│   │   └── routers/
│   │       ├── auth.py
│   │       ├── families.py
│   │       ├── transactions.py
│   │       ├── reports.py
│   │       └── goals.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── README.md
