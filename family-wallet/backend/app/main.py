from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import Base, engine
from .models import User
from .routers import auth, families, goals, reports, transactions
from .schemas import CurrentUserResponse

Base.metadata.create_all(bind=engine)


def run_sqlite_migrations():
    with engine.begin() as conn:
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(transactions)")).fetchall()}
        if "account_type" not in columns:
            conn.execute(
                text("ALTER TABLE transactions ADD COLUMN account_type VARCHAR(20) NOT NULL DEFAULT 'main'")
            )
        if "is_recurring_generated" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE transactions "
                    "ADD COLUMN is_recurring_generated BOOLEAN NOT NULL DEFAULT 0"
                )
            )
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS family_permissions ("
                "id INTEGER PRIMARY KEY, "
                "user_id INTEGER NOT NULL, "
                "family_id INTEGER NOT NULL, "
                "can_manage_accounts BOOLEAN NOT NULL DEFAULT 0, "
                "can_delete_any_transactions BOOLEAN NOT NULL DEFAULT 0)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS accounts ("
                "id INTEGER PRIMARY KEY, "
                "family_id INTEGER NOT NULL, "
                "name VARCHAR(100) NOT NULL, "
                "is_default BOOLEAN NOT NULL DEFAULT 0, "
                "created_by_user_id INTEGER NOT NULL)"
            )
        )


def backfill_permissions_and_accounts():
    db = Session(bind=engine)
    try:
        members = db.execute(text("SELECT user_id, family_id, role FROM memberships")).fetchall()
        for user_id, family_id, role in members:
            exists = db.execute(
                text("SELECT 1 FROM family_permissions WHERE user_id=:u AND family_id=:f"),
                {"u": user_id, "f": family_id},
            ).fetchone()
            if not exists:
                db.execute(
                    text(
                        "INSERT INTO family_permissions(user_id, family_id, can_manage_accounts, can_delete_any_transactions) "
                        "VALUES (:u, :f, :m, :d)"
                    ),
                    {"u": user_id, "f": family_id, "m": 1 if role == "owner" else 0, "d": 1 if role == "owner" else 0},
                )
        families = db.execute(text("SELECT id, owner_id FROM families")).fetchall()
        for family_id, owner_id in families:
            has_main = db.execute(
                text("SELECT 1 FROM accounts WHERE family_id=:f AND name='main'"),
                {"f": family_id},
            ).fetchone()
            if not has_main:
                db.execute(
                    text(
                        "INSERT INTO accounts(family_id, name, is_default, created_by_user_id) "
                        "VALUES (:f, 'main', 1, :u)"
                    ),
                    {"f": family_id, "u": owner_id},
                )
        db.commit()
    finally:
        db.close()


run_sqlite_migrations()
backfill_permissions_and_accounts()

app = FastAPI(title="Family Wallet")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(families.router)
app.include_router(transactions.router)
app.include_router(reports.router)
app.include_router(goals.router)


@app.get("/me", response_model=CurrentUserResponse)
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "name": current_user.name}
