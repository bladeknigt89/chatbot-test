from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.models import Agent, Document
from app.schemas import AgentCreate, AgentOut, AgentUpdate
from app.workers.queue import enqueue_job

router = APIRouter(tags=["Agents"])


def _to_out(agent: Agent, document_count: int = 0) -> AgentOut:
    data = AgentOut.model_validate(agent)
    data.document_count = document_count
    return data


@router.post(
    "/agents",
    response_model=AgentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Agent létrehozása",
)
def create_agent(
    payload: AgentCreate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    agent = Agent(**payload.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    write_audit(
        db,
        user=auth.actor,
        action="AGENT_CREATED",
        resource_type="agent",
        resource_id=agent.id,
        details=agent.name,
        request=request,
    )
    return _to_out(agent)


@router.get("/agents", response_model=list[AgentOut], summary="Agentek listázása")
def list_agents(db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    agents = db.query(Agent).order_by(Agent.created_at.desc()).all()
    result = []
    for agent in agents:
        count = db.query(Document).filter(Document.agent_id == agent.id).count()
        result.append(_to_out(agent, count))
    return result


@router.get("/agents/{agent_id}", response_model=AgentOut, summary="Agent lekérése")
def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Az agent nem található.")
    count = db.query(Document).filter(Document.agent_id == agent.id).count()
    return _to_out(agent, count)


@router.put("/agents/{agent_id}", response_model=AgentOut, summary="Agent módosítása")
def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Az agent nem található.")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(agent, key, value)
    db.commit()
    db.refresh(agent)
    write_audit(
        db,
        user=auth.actor,
        action="AGENT_UPDATED",
        resource_type="agent",
        resource_id=agent.id,
        details=agent.name,
        request=request,
    )
    count = db.query(Document).filter(Document.agent_id == agent.id).count()
    return _to_out(agent, count)


@router.delete("/agents/{agent_id}", status_code=202, summary="Agent törlése")
def delete_agent(
    agent_id: str,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Az agent nem található.")
    write_audit(
        db,
        user=auth.actor,
        action="AGENT_DELETED",
        resource_type="agent",
        resource_id=agent.id,
        details=agent.name,
        request=request,
    )
    enqueue_job(db, "DELETE_AGENT", {"agent_id": agent.id})
    return {"ok": True, "status": "deleting"}
