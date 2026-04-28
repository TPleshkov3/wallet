import random
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Account, Family, FamilyPermission, Membership, User
from ..schemas import (
    AccountCreateRequest,
    AccountResponse,
    FamilyMemberResponse,
    FamilyCreateRequest,
    FamilyJoinRequest,
    FamilyJoinResponse,
    FamilyPermissionUpdateRequest,
    FamilyResponse,
    InviteCodeResponse,
    MembershipFamilyResponse,
)

router = APIRouter(prefix="/families", tags=["families"])


def generate_invite_code(db: Session) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(alphabet, k=6))
        if not db.query(Family).filter(Family.invite_code == code).first():
            return code


@router.post("", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
def create_family(
    payload: FamilyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    family = Family(name=payload.name, invite_code=generate_invite_code(db), owner_id=current_user.id)
    db.add(family)
    db.flush()

    membership = Membership(user_id=current_user.id, family_id=family.id, role="owner")
    db.add(membership)
    db.add(
        FamilyPermission(
            user_id=current_user.id,
            family_id=family.id,
            can_manage_accounts=True,
            can_delete_any_transactions=True,
        )
    )
    db.add(Account(family_id=family.id, name="main", is_default=True, created_by_user_id=current_user.id))
    db.commit()
    db.refresh(family)
    return family


@router.post("/join", response_model=FamilyJoinResponse)
def join_family(
    payload: FamilyJoinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    family = db.query(Family).filter(Family.invite_code == payload.code.upper()).first()
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Код приглашения не найден")

    existing = (
        db.query(Membership)
        .filter(Membership.user_id == current_user.id, Membership.family_id == family.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Вы уже состоите в семье")

    db.add(Membership(user_id=current_user.id, family_id=family.id, role="member"))
    db.add(
        FamilyPermission(
            user_id=current_user.id,
            family_id=family.id,
            can_manage_accounts=False,
            can_delete_any_transactions=False,
        )
    )
    db.commit()
    return {
        "message": f"Вы вступили в семью {family.name}",
        "family_id": family.id,
        "family_name": family.name,
    }


@router.get("/me", response_model=MembershipFamilyResponse | None)
def get_my_family(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(Membership).filter(Membership.user_id == current_user.id).first()
    if not membership:
        return None

    family = db.query(Family).filter(Family.id == membership.family_id).first()
    return {
        "user_id": current_user.id,
        "family_id": family.id,
        "family_name": family.name,
        "role": membership.role,
    }


@router.get("/{family_id}/invite", response_model=InviteCodeResponse)
def get_family_invite_code(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = (
        db.query(Membership)
        .filter(Membership.family_id == family_id, Membership.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь участником этой семьи")
    if membership.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только владелец может приглашать")

    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Семья не найдена")
    return {"invite_code": family.invite_code}


@router.get("/{family_id}/members", response_model=list[FamilyMemberResponse])
def get_family_members(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = (
        db.query(Membership)
        .filter(Membership.family_id == family_id, Membership.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь участником этой семьи")

    memberships = db.query(Membership).filter(Membership.family_id == family_id).all()
    result = []
    for item in memberships:
        user = db.query(User).filter(User.id == item.user_id).first()
        if user:
            permission = (
                db.query(FamilyPermission)
                .filter(FamilyPermission.family_id == family_id, FamilyPermission.user_id == user.id)
                .first()
            )
            result.append(
                {
                    "user_id": user.id,
                    "user_name": user.name,
                    "user_email": user.email,
                    "role": item.role,
                    "can_manage_accounts": permission.can_manage_accounts if permission else False,
                    "can_delete_any_transactions": permission.can_delete_any_transactions if permission else False,
                }
            )
    return result


@router.put("/{family_id}/permissions", response_model=FamilyMemberResponse)
def update_family_permission(
    family_id: int,
    payload: FamilyPermissionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    owner_membership = (
        db.query(Membership)
        .filter(Membership.family_id == family_id, Membership.user_id == current_user.id)
        .first()
    )
    if not owner_membership or owner_membership.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только владелец может менять права")

    membership = (
        db.query(Membership)
        .filter(Membership.family_id == family_id, Membership.user_id == payload.user_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Участник не найден")
    if membership.role == "owner":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя менять права владельца")

    permission = (
        db.query(FamilyPermission)
        .filter(FamilyPermission.family_id == family_id, FamilyPermission.user_id == payload.user_id)
        .first()
    )
    if not permission:
        permission = FamilyPermission(user_id=payload.user_id, family_id=family_id)
        db.add(permission)
    permission.can_manage_accounts = payload.can_manage_accounts
    permission.can_delete_any_transactions = payload.can_delete_any_transactions
    db.commit()

    user = db.query(User).filter(User.id == payload.user_id).first()
    return {
        "user_id": user.id,
        "user_name": user.name,
        "user_email": user.email,
        "role": membership.role,
        "can_manage_accounts": permission.can_manage_accounts,
        "can_delete_any_transactions": permission.can_delete_any_transactions,
    }


@router.get("/{family_id}/accounts", response_model=list[AccountResponse])
def get_family_accounts(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = (
        db.query(Membership)
        .filter(Membership.family_id == family_id, Membership.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь участником этой семьи")
    return db.query(Account).filter(Account.family_id == family_id).order_by(Account.id.asc()).all()


@router.post("/{family_id}/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_family_account(
    family_id: int,
    payload: AccountCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = (
        db.query(Membership)
        .filter(Membership.family_id == family_id, Membership.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь участником этой семьи")
    permission = (
        db.query(FamilyPermission)
        .filter(FamilyPermission.family_id == family_id, FamilyPermission.user_id == current_user.id)
        .first()
    )
    if membership.role != "owner" and not (permission and permission.can_manage_accounts):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для управления счетами")

    existing = db.query(Account).filter(Account.family_id == family_id, Account.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Счет с таким именем уже существует")

    account = Account(family_id=family_id, name=payload.name, is_default=False, created_by_user_id=current_user.id)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account
