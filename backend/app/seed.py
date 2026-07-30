from __future__ import annotations

import logging

from app.core.security import hash_password
from app.db.models.domain import (
    Material,
    Plant,
    Vendor,
    VendorMaterial,
)
from app.db.models.user import RoleEnum, User, UserRole
from app.db.session import SessionLocal
from app.services.sap.mock import MockSAPAdapter

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

        # 2. Sync domain data from SAP Mock Adapter
        sap_adapter = MockSAPAdapter()
        counts = sap_adapter.sync_to_database(db)
        logger.info("Synced SAP mock data: %s", counts)

        # 3. Ensure Primary VendorMaterial Relationships
        plant_1000 = db.query(Plant).filter(Plant.code == "PLANT-1000").first()
        plant_2000 = db.query(Plant).filter(Plant.code == "PLANT-2000").first()
        mat_1001 = db.query(Material).filter(Material.code == "MAT-1001").first()
        mat_2002 = db.query(Material).filter(Material.code == "MAT-2002").first()
        vend_5001 = db.query(Vendor).filter(Vendor.code == "VEND-5001").first()
        vend_5002 = db.query(Vendor).filter(Vendor.code == "VEND-5002").first()

        vm_relationships = [
            (vend_5001, mat_1001, plant_1000, 7.0, 100.0),
            (vend_5002, mat_2002, plant_2000, 5.0, 200.0),
        ]

        for v, m, p, lead_time, min_qty in vm_relationships:
            if v and m and p:
                vm = (
                    db.query(VendorMaterial)
                    .filter(
                        VendorMaterial.vendor_id == v.id,
                        VendorMaterial.material_id == m.id,
                        VendorMaterial.plant_id == p.id,
                    )
                    .first()
                )
                if not vm:
                    vm = VendorMaterial(
                        vendor_id=v.id,
                        material_id=m.id,
                        plant_id=p.id,
                        is_primary=True,
                        vendor_lead_time_days=lead_time,
                        min_order_qty=min_qty,
                    )
                    db.add(vm)
                    logger.info(
                        "Created VendorMaterial relationship: %s / %s / %s",
                        v.code,
                        m.code,
                        p.code,
                    )

        db.commit()
        logger.info("Database seeding completed successfully.")
    except Exception:
        db.rollback()
        logger.exception("Database seeding failed.")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
