from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import Family, Membership, User


def get_membership_or_403(db: Session, family_id: int, user: User) -> Membership:
    membership = (
        db.query(Membership)
        .filter(Membership.family_id == family_id, Membership.user_id == user.id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не являетесь участником этой семьи",
        )
    return membership


def is_family_owner(db: Session, family_id: int, user_id: int) -> bool:
    family = db.query(Family).filter(Family.id == family_id).first()
    return bool(family and family.owner_id == user_id)
