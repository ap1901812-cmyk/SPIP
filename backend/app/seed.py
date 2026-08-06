from __future__ import annotations

import logging

from app.core.security import hash_password
from app.db.models.user import RoleEnum, User, UserRole
from app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spip.seed")


def seed_database() -> None:
    db = SessionLocal()
    try:
        logger.info("Starting SPIP database seeding...")
        default_pw = hash_password("Pass123!")

        # 1. Seed Users & Roles
        initial_users = [
            {
                "username": "admin",
                "email": "admin@spip.local",
                "name": "Aditya Pandey",
                "role": RoleEnum.ADMIN.value,
            },
            {
                "username": "planner",
                "email": "planner@spip.local",
                "name": "Rahul Sharma",
                "role": RoleEnum.PLANNER.value,
            },
            {
                "username": "manager",
                "email": "manager@spip.local",
                "name": "Amit Verma",
                "role": RoleEnum.MANAGER_APPROVER.value,
            },
            {
                "username": "readonly",
                "email": "readonly@spip.local",
                "name": "Auditor User",
                "role": RoleEnum.READ_ONLY.value,
            },
        ]

        for user_data in initial_users:
            user = (
                db.query(User)
                .filter((User.username == user_data["username"]) | (User.email == user_data["email"]))
                .first()
            )
            if not user:
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    full_name=user_data["name"],
                    hashed_password=default_pw,
                    is_active=True,
                    must_change_password=False,
                )
                db.add(user)
                db.flush()
                role = UserRole(user_id=user.id, role_name=user_data["role"])
                db.add(role)
                logger.info("Created user %s (%s) with role %s", user_data["username"], user_data["email"], user_data["role"])
            else:
                user.username = user_data["username"]
                user.full_name = user_data["name"]
                user.must_change_password = False
                db.flush()

        db.commit()
        logger.info("Database seeding completed successfully (users & roles only).")
    except Exception:
        db.rollback()
        logger.exception("Database seeding failed.")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
