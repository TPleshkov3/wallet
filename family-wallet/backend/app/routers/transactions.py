import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..dependencies import get_membership_or_403, is_family_owner
from ..models import Account, AuditLog, FamilyPermission, RecurringPayment, Transaction, User
from ..schemas import (
    MessageResponse,
    RecurringPaymentResponse,
    RecurringPaymentUpdateRequest,
    TransactionCreateRequest,
    TransactionResponse,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def write_log(db: Session, family_id: int, actor_user_id: int, action: str, details: str):
    db.add(AuditLog(family_id=family_id, actor_user_id=actor_user_id, action=action, details=details))


def generate_recurring_if_due(db: Session, family_id: int):
    today = dt.date.today()
    templates = (
        db.query(RecurringPayment)
        .filter(RecurringPayment.family_id == family_id, RecurringPayment.active.is_(True))
        .all()
    )
    for tpl in templates:
        if tpl.day_of_month != today.day:
            continue
        if tpl.last_generated_on == today:
            continue
        tx = Transaction(
            type="expense",
            amount=tpl.amount,
            category=tpl.category,
            description=tpl.description,
            account_type=tpl.account_type,
            user_id=tpl.user_id,
            family_id=tpl.family_id,
            is_recurring_generated=True,
            date=today,
        )
        db.add(tx)
        tpl.last_generated_on = today
        write_log(
            db,
            tpl.family_id,
            tpl.user_id,
            "recurring_generated",
            f"Автосписание {tpl.amount:.0f} ₽ ({tpl.category})",
        )
    db.commit()


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_membership_or_403(db, payload.family_id, current_user)
    account = db.query(Account).filter(Account.family_id == payload.family_id, Account.name == payload.account_type).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Счет не найден")

    transaction = Transaction(
        type=payload.type,
        amount=payload.amount,
        category=payload.category,
        description=payload.description,
        account_type=payload.account_type,
        user_id=current_user.id,
        family_id=payload.family_id,
    )
    db.add(transaction)
    write_log(
        db,
        payload.family_id,
        current_user.id,
        "transaction_created",
        f"Добавил {payload.type} {payload.amount:.0f} ₽ ({payload.category})",
    )

    if payload.recurring_monthly:
        if payload.type != "expense":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Регулярные доступны только для расхода")
        recurring = RecurringPayment(
            family_id=payload.family_id,
            user_id=current_user.id,
            amount=payload.amount,
            category=payload.category,
            description=payload.description,
            account_type=payload.account_type,
            day_of_month=payload.recurring_day,
            active=True,
        )
        db.add(recurring)
        write_log(
            db,
            payload.family_id,
            current_user.id,
            "recurring_created",
            f"Создал регулярный платеж {payload.amount:.0f} ₽ ({payload.category})",
        )

    db.commit()
    db.refresh(transaction)

    return {
        "id": transaction.id,
        "type": transaction.type,
        "amount": transaction.amount,
        "category": transaction.category,
        "description": transaction.description,
        "account_type": transaction.account_type,
        "date": transaction.date,
        "user_name": current_user.name,
        "is_recurring_generated": transaction.is_recurring_generated,
    }


@router.get("", response_model=list[TransactionResponse])
def get_transactions(
    family_id: int = Query(...),
    account_type: str | None = Query(None, pattern="^(main|savings)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_membership_or_403(db, family_id, current_user)
    generate_recurring_if_due(db, family_id)

    query = db.query(Transaction).filter(Transaction.family_id == family_id)
    if account_type:
        query = query.filter(Transaction.account_type == account_type)

    transactions = query.order_by(Transaction.date.desc(), Transaction.id.desc()).all()

    result = []
    for tx in transactions:
        user = db.query(User).filter(User.id == tx.user_id).first()
        result.append(
            {
                "id": tx.id,
                "type": tx.type,
                "amount": tx.amount,
                "category": tx.category,
                "description": tx.description,
                "account_type": tx.account_type,
                "date": tx.date,
                "user_name": user.name if user else "Unknown",
                "is_recurring_generated": tx.is_recurring_generated,
            }
        )
    return result


@router.delete("/{transaction_id}", response_model=MessageResponse)
def delete_transaction(
    transaction_id: int,
    family_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_membership_or_403(db, family_id, current_user)

    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.family_id == family_id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Транзакция не найдена")

    is_owner = is_family_owner(db, family_id, current_user.id)
    permission = (
        db.query(FamilyPermission)
        .filter(FamilyPermission.family_id == family_id, FamilyPermission.user_id == current_user.id)
        .first()
    )
    can_delete_any = bool(permission and permission.can_delete_any_transactions)
    if transaction.user_id != current_user.id and not is_owner and not can_delete_any:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    write_log(
        db,
        family_id,
        current_user.id,
        "transaction_deleted",
        f"Удалил {transaction.type} {transaction.amount:.0f} ₽ ({transaction.category})",
    )
    db.delete(transaction)
    db.commit()
    return {"message": "Удалено"}


@router.get("/recurring", response_model=list[RecurringPaymentResponse])
def get_recurring_payments(
    family_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_membership_or_403(db, family_id, current_user)
    rows = (
        db.query(RecurringPayment)
        .filter(RecurringPayment.family_id == family_id, RecurringPayment.active.is_(True))
        .order_by(RecurringPayment.id.desc())
        .all()
    )
    return rows


@router.delete("/recurring/{recurring_id}", response_model=MessageResponse)
def delete_recurring_payment(
    recurring_id: int,
    family_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = get_membership_or_403(db, family_id, current_user)
    recurring = (
        db.query(RecurringPayment)
        .filter(RecurringPayment.id == recurring_id, RecurringPayment.family_id == family_id)
        .first()
    )
    if not recurring:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Регулярный платеж не найден")

    if recurring.user_id != current_user.id and membership.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    recurring.active = False
    write_log(
        db,
        family_id,
        current_user.id,
        "recurring_deleted",
        f"Отключил регулярный платеж {recurring.amount:.0f} ₽ ({recurring.category})",
    )
    db.commit()
    return {"message": "Удалено"}


@router.put("/recurring/{recurring_id}", response_model=RecurringPaymentResponse)
def update_recurring_payment(
    recurring_id: int,
    payload: RecurringPaymentUpdateRequest,
    family_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = get_membership_or_403(db, family_id, current_user)
    recurring = (
        db.query(RecurringPayment)
        .filter(
            RecurringPayment.id == recurring_id,
            RecurringPayment.family_id == family_id,
            RecurringPayment.active.is_(True),
        )
        .first()
    )
    if not recurring:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Регулярный платеж не найден")

    if recurring.user_id != current_user.id and membership.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    recurring.amount = payload.amount
    recurring.category = payload.category
    recurring.description = payload.description
    recurring.account_type = payload.account_type
    recurring.day_of_month = payload.day_of_month
    write_log(
        db,
        family_id,
        current_user.id,
        "recurring_updated",
        f"Изменил регулярный платеж {payload.amount:.0f} ₽ ({payload.category})",
    )
    db.commit()
    db.refresh(recurring)
    return recurring


@router.get("/audit-log")
def get_audit_log(
    family_id: int = Query(...),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_membership_or_403(db, family_id, current_user)
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.family_id == family_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.actor_user_id).first()
        result.append(
            {
                "id": log.id,
                "actor_name": user.name if user else "Unknown",
                "action": log.action,
                "details": log.details,
                "created_at": log.created_at,
            }
        )
    return result
