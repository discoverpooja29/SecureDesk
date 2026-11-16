from fastapi import FastAPI, HTTPException, status
from .api.routes.auth import router as auth_router
from .api.routes.tickets import router as tickets_router
from .api.routes.users import router as users_router

app = FastAPI(
    title="SecureDesk API",
    version="0.2.0"
)

app.include_router(auth_router)
app.include_router(tickets_router)
app.include_router(users_router)

@app.get("/health/live")
def liveness():
    return { "status": "healthy - live" }
