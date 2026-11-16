from sqlalchemy import select

from ..db.session import SessionLocal
from ..models.permission import Permission


PERMISSION_DEFINITIONS = {
    "tickets:read": "Read support tickets",
    "tickets:create": "Create support tickets",
    "tickets:assign": "Assign support tickets to agents",
    "tickets:close": "Close support tickets",
    "users:manage": "Manage user accounts",
    "tickets:read:tenant": "Read any support ticket within the current tenant",
}


def main() -> None:
    with SessionLocal.begin() as db:
        for name, description in PERMISSION_DEFINITIONS.items():
            existing_permission = db.scalar(
                select(Permission).where(Permission.name == name)
            )

            if existing_permission is None:
                db.add(
                    Permission(
                        name=name,
                        description=description,
                    )
                )
                print(f"Adding permission: {name}")
            else:
                print(f"Permission already exists: {name}")

    print("Permission seeding completed.")


if __name__ == "__main__":
    main()