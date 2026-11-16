from sqlalchemy import select

from ..db.session import SessionLocal
from ..models.tenant import Tenant


TENANT_DEFINITIONS = {
    "acme": "Acme Corporation",
    "globex": "Globex Corporation",
}


def main() -> None:
    with SessionLocal.begin() as db:
        for slug, name in TENANT_DEFINITIONS.items():
            tenant = db.scalar(
                select(Tenant).where(Tenant.slug == slug)
            )

            if tenant is None:
                db.add(Tenant(name=name, slug=slug))
                print(f"Adding tenant: {slug}")
            else:
                print(f"Tenant already exists: {slug}")

    print("Tenant seeding completed.")


if __name__ == "__main__":
    main()