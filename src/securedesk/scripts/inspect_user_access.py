import argparse

from sqlalchemy import select

from ..db.session import SessionLocal
from ..models.user import User

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    args = parser.parse_args()
    
    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(User.email == args.email.lower())
        )
        
        if user is None:
            raise SystemExit("User not found")
        
        role_names = sorted(role.name for role in user.roles)
        
        permission_names = sorted({
            permission.name
            for role in user.roles
            for permission in role.permissions
        })
        
        print("Roles: ", role_names)
        print("Permissions: ", permission_names)
        
if  __name__ == "__main__":
    main()