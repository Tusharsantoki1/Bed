"""Seed the database: create tables, the first super admin, and sample plans.

Run from the Bed/ directory:  python -m src.seed
"""

from __future__ import annotations

from sqlalchemy import select

from .config import settings
from .database import SessionLocal, create_all_tables
from .models.enums import PlanCycle, UserRole
from .models.subscription import Plan
from .models.user import User
from .utils.security import hash_password

SAMPLE_PLANS = [
    ("Monthly", PlanCycle.monthly, 299),
    ("Quarterly", PlanCycle.quarterly, 799),
    ("Half-Yearly", PlanCycle.half_yearly, 1499),
    ("Yearly", PlanCycle.yearly, 2799),
]


def seed() -> None:
    create_all_tables()
    db = SessionLocal()
    try:
        # Super admin
        existing = db.execute(
            select(User).where(User.email == settings.SUPER_ADMIN_EMAIL.lower())
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                User(
                    email=settings.SUPER_ADMIN_EMAIL.lower(),
                    password_hash=hash_password(settings.SUPER_ADMIN_PASSWORD),
                    full_name=settings.SUPER_ADMIN_NAME,
                    role=UserRole.super_admin,
                    is_active=True,
                )
            )
            print(f"Created super admin: {settings.SUPER_ADMIN_EMAIL}")
        else:
            print("Super admin already exists, skipping.")

        # Sample plans
        if db.execute(select(Plan).limit(1)).first() is None:
            for name, cycle, price in SAMPLE_PLANS:
                db.add(Plan(name=name, cycle=cycle, price=price, is_active=True))
            print(f"Created {len(SAMPLE_PLANS)} sample plans.")
        else:
            print("Plans already exist, skipping.")

        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
