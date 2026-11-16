from sqlalchemy import select

from ..db.session import SessionLocal
from ..models.role import Role

ROLE_DEFINITIONS = {
    "customer": "Create and view their own support tickets",
    "agent": "Handles support tickets",
    "admin": "Administers SecureDesk"
}

def main() -> None:
    with SessionLocal.begin() as db:
        for name, description in ROLE_DEFINITIONS.items():
            existing_role = db.scalar(
                select(Role).where(Role.name == name)
            )
            
            if existing_role is None:
                db.add(
                    Role(name = name,
                         description = description
                    )
                )
                print(f"Adding role: {name}")
            else:
                print(f"Role already exists: {name}")
                
    print("Role seeding completed")
    
    
if __name__ == "__main__":
    main()