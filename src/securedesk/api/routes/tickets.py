from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models.tenant import Tenant
from ...models.ticket import Ticket
from ...models.user import User
from ...schemas.ticket import TicketCreate, TicketRead
from ..dependencies import get_current_tenant, require_permission

router = APIRouter(
    prefix="/tickets",
    tags=["Tickets"]
)

@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(
    data: TicketCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("tickets:create"))],
    tenant: Annotated[Tenant, Depends(get_current_tenant)]
):
    ticket = Ticket(
        title = data.title,
        description = data.description,
        tenant_id = tenant.id,
        created_by_id = current_user.id
    )
    
    db.add(ticket)
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    
    db.refresh(ticket)
    return ticket

@router.get("/{ticket_id}", response_model=TicketRead)
def read_ticket(
    ticket_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("tickets:read"))],
    tenant: Annotated[Tenant, Depends(get_current_tenant)]
):
    can_read_tenant = any(
        permission.name == "tickets:read:tenant"
        for role in current_user.roles
        for permission in role.permissions
    )
    
    statement = select(Ticket).where(
        Ticket.id == ticket_id,
        Ticket.tenant_id == tenant.id,
    )

    if not can_read_tenant:
        statement = statement.where(
            Ticket.created_by_id == current_user.id
        )

    ticket = db.scalar(statement)
    
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
        
    return ticket
    