from sqlalchemy import select

from ..db.session import SessionLocal
from ..models.role import Role
from ..models.permission import Permission

ROLE_PERMISSION_MAP = {
    "customer": {
        "tickets:read",
        "tickets:create",
    },
    "agent": {
        "tickets:read",
        "tickets:create",
        "tickets:assign",
        "tickets:close",
        "tickets:read:tenant"
    },
    "admin": {
        "tickets:read",
        "tickets:create",
        "tickets:assign",
        "tickets:close",
        "tickets:read:tenant",
        "users:manage"
    },
}

def main() -> None:
    with SessionLocal.begin() as db:
        for role_name, permission_names in ROLE_PERMISSION_MAP.items():
            role = db.scalar(
                select(Role).where(Role.name == role_name)
            )

            if role is None:
                raise ValueError(f"Role not found: {role_name}")

            assigned_names = {
                permission.name for permission in role.permissions
            }

            for permission_name in sorted(permission_names):
                permission = db.scalar(
                    select(Permission).where(
                        Permission.name == permission_name
                    )
                )

                if permission is None:
                    raise ValueError(
                        f"Permission not found: {permission_name}"
                    )

                if permission_name in assigned_names:
                    print(f"Already granted: {role_name} → {permission_name}")
                    continue

                role.permissions.append(permission)
                assigned_names.add(permission_name)
                print(f"Granting: {role_name} → {permission_name}")

    print("Role permission seeding completed.")


if __name__ == "__main__":
    main()