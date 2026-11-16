import argparse

from sqlalchemy import select

from ..db.session import SessionLocal
from ..models.tenant import Tenant
from ..models.user import User


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    parser.add_argument("tenant_slug")
    args = parser.parse_args()

    with SessionLocal.begin() as db:
        user = db.scalar(
            select(User).where(User.email == args.email.lower())
        )
        tenant = db.scalar(
            select(Tenant).where(Tenant.slug == args.tenant_slug)
        )

        if user is None:
            raise ValueError("User not found")

        if tenant is None:
            raise ValueError("Tenant not found")

        if user.tenant_id == tenant.id:
            print("User already belongs to this tenant")
        elif user.tenant_id is not None:
            raise ValueError(
                "User already belongs to a different tenant"
            )
        else:
            user.tenant = tenant
            print(f"Assigning user to tenant: {tenant.slug}")

    print("Tenant assignment completed.")


if __name__ == "__main__":
    main()