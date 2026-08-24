import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.stats_logic import MetricsService
from pydantic import BaseModel
from typing import Any

router = APIRouter(prefix="/ws", tags=["WebSockets"])

# Define a simple response wrapper for websocket responses to match ApiResponse structure
class WSResponse(BaseModel):
    success: bool = True
    data: Any

@router.websocket("/dashboard")
async def websocket_dashboard(websocket: WebSocket, session: AsyncSession = Depends(get_db)):
    await websocket.accept()
    try:
        while True:
            # Fetch overview stats
            overview = await MetricsService.get_overview_metrics(session)
            resp = WSResponse(data=overview)
            await websocket.send_json(resp.model_dump(mode="json"))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
