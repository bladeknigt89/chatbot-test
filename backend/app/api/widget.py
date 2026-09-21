from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent
from app.schemas import WidgetConfigOut

router = APIRouter(tags=["Widget"])


@router.get(
    "/widget/{agent_id}/config",
    response_model=WidgetConfigOut,
    summary="Nyilvános widget konfiguráció",
)
def widget_config(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Az agent nem található.")
    title = agent.widget_title.strip() or agent.name
    return WidgetConfigOut(
        agent_id=agent.id,
        agent_name=agent.name,
        status=agent.status,
        primary_color=agent.widget_primary_color,
        title=title,
        position=agent.widget_position,
        welcome_message=agent.widget_welcome_message,
    )
