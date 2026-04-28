from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..dependencies import get_membership_or_403
from ..models import AuditLog, SavingsGoal, Transaction, User
from ..schemas import SavingsGoalRequest, SavingsGoalResponse

router = APIRouter(prefix="/goals", tags=["goals"])


def compute_balance(db: Session, family_id: int, account_type: str) -> float:
    txs = (
        db.query(Transaction)
        .filter(Transaction.family_id == family_id, Transaction.account_type == account_type)
        .all()
    )
    total_income = sum(t.amount for t in txs if t.type == "income")
    total_expense = sum(t.amount for t in txs if t.type == "expense")
    return total_income - total_expense


@router.post("", response_model=SavingsGoalResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_goal(
    payload: SavingsGoalRequest,
    family_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = get_membership_or_403(db, family_id, current_user)
    if membership.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только владелец может управлять целью")

    goal = db.query(SavingsGoal).filter(SavingsGoal.family_id == family_id).first()
    if goal:
        goal.title = payload.title
        goal.target_amount = payload.target_amount
        goal.deadline_year = payload.deadline_year
        goal.deadline_month = payload.deadline_month
        goal.account_type = payload.account_type
        action = "goal_updated"
    else:
        goal = SavingsGoal(
            family_id=family_id,
            title=payload.title,
            target_amount=payload.target_amount,
            deadline_year=payload.deadline_year,
            deadline_month=payload.deadline_month,
            account_type=payload.account_type,
        )
        db.add(goal)
        action = "goal_created"

    db.add(
        AuditLog(
            family_id=family_id,
            actor_user_id=current_user.id,
            action=action,
            details=f"Цель: {payload.title}, {payload.target_amount:.0f} ₽",
        )
    )
    db.commit()
    db.refresh(goal)

    balance = compute_balance(db, family_id, goal.account_type)
    progress = min(100, int((balance / goal.target_amount) * 100)) if goal.target_amount else 0
    remaining = max(0.0, goal.target_amount - balance)
    return {
        "title": goal.title,
        "target_amount": goal.target_amount,
        "deadline_year": goal.deadline_year,
        "deadline_month": goal.deadline_month,
        "account_type": goal.account_type,
        "current_balance": balance,
        "progress_percent": max(0, progress),
        "remaining_amount": remaining,
        "achieved": balance >= goal.target_amount,
    }


@router.get("/current", response_model=SavingsGoalResponse | None)
def get_goal(
    family_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_membership_or_403(db, family_id, current_user)
    goal = db.query(SavingsGoal).filter(SavingsGoal.family_id == family_id).first()
    if not goal:
        return None
    balance = compute_balance(db, family_id, goal.account_type)
    progress = min(100, int((balance / goal.target_amount) * 100)) if goal.target_amount else 0
    remaining = max(0.0, goal.target_amount - balance)
    return {
        "title": goal.title,
        "target_amount": goal.target_amount,
        "deadline_year": goal.deadline_year,
        "deadline_month": goal.deadline_month,
        "account_type": goal.account_type,
        "current_balance": balance,
        "progress_percent": max(0, progress),
        "remaining_amount": remaining,
        "achieved": balance >= goal.target_amount,
    }
