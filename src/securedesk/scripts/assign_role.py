import argparse

from sqlalchemy import select

from ..db.session import SessionLocal
from ..models.user import User
from ..models.role import Role


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    parser.add_argument("role")
    args = parser.parse_args()

    with SessionLocal.begin() as db:
        user = db.scalar(
            select(User).where(User.email == args.email.lower())
        )
        role = db.scalar(
            select(Role).where(Role.name == args.role)
        )

        if user is None:
            raise ValueError("User not found")

        if role is None:
            raise ValueError("Role not found")

        if role in user.roles:
            print("User already has this role")
        else:
            user.roles.append(role)

    print("Role assignment completed.")


if __name__ == "__main__":
    main()