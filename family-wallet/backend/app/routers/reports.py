import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy import extract
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..dependencies import get_membership_or_403
from ..models import Transaction, User
from ..schemas import ReportResponse

router = APIRouter(tags=["report"])


@router.get("/report", response_model=ReportResponse)
def get_report(
    family_id: int = Query(...),
    year: int = Query(..., ge=2000, le=3000),
    month: int = Query(..., ge=1, le=12),
    date_from: dt.date | None = Query(None),
    date_to: dt.date | None = Query(None),
    tx_type: str | None = Query(None, pattern="^(income|expense)$"),
    category: str | None = Query(None),
    account_type: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_membership_or_403(db, family_id, current_user)

    query = db.query(Transaction).filter(
        Transaction.family_id == family_id,
        extract("year", Transaction.date) == year,
        extract("month", Transaction.date) == month,
    )
    if date_from:
        query = query.filter(Transaction.date >= date_from)
    if date_to:
        query = query.filter(Transaction.date <= date_to)
    if tx_type:
        query = query.filter(Transaction.type == tx_type)
    if category:
        query = query.filter(Transaction.category == category)
    if account_type:
        query = query.filter(Transaction.account_type == account_type)

    txs = query.all()

    total_income = sum(tx.amount for tx in txs if tx.type == "income")
    total_expense = sum(tx.amount for tx in txs if tx.type == "expense")

    by_category: dict[str, float] = {}
    by_user: dict[str, float] = {}

    for tx in txs:
        if tx.type == "expense":
            by_category[tx.category] = by_category.get(tx.category, 0.0) + tx.amount
            user = db.query(User).filter(User.id == tx.user_id).first()
            name = user.name if user else "Unknown"
            by_user[name] = by_user.get(name, 0.0) + tx.amount

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": total_income - total_expense,
        "by_category": by_category,
        "by_user": by_user,
    }
