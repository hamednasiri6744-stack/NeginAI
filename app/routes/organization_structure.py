from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.organization_structure_service import (
    list_proposals, list_structure, require_admin, review_proposal, seed_confirmed_rules, update_rule,
)
from app.routes.dependencies import require_user_or_local
from app.control_service import permission_keys_for_user

router = APIRouter(prefix="/organization-structure", tags=["organization structure"], dependencies=[Depends(require_user_or_local)])


def _admin(request: Request) -> str:
    username = str(getattr(request.state, "username", "") or "")
    try:
        require_admin(request.app.state.settings, username)
    except PermissionError as exc:
        if "organization.manage" not in permission_keys_for_user(
            request.app.state.settings, username
        ):
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    return username


class ProposalDecision(BaseModel):
    decision: str


class TeamRuleUpdate(BaseModel):
    team_split: str
    brand_portfolio: list[str] = []
    notes: str = ""


@router.get("")
def get_structure(request: Request):
    _admin(request)
    seed_confirmed_rules(request.app.state.settings)
    return {"rules": list_structure(request.app.state.settings), "external_person_ids": [7, 137, 192, 510]}


@router.get("/proposals")
def get_proposals(request: Request, status: str = "pending"):
    _admin(request)
    return {"proposals": list_proposals(request.app.state.settings, status)}


@router.patch("/rules/{rule_id}")
def patch_rule(rule_id: int, payload: TeamRuleUpdate, request: Request):
    _admin(request)
    try:
        return update_rule(
            request.app.state.settings, rule_id, team_split=payload.team_split,
            brand_portfolio=payload.brand_portfolio, notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/proposals/{proposal_id}/decision")
def decide_proposal(proposal_id: int, payload: ProposalDecision, request: Request):
    username = _admin(request)
    if payload.decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="decision must be approved or rejected")
    try:
        return review_proposal(request.app.state.settings, proposal_id, payload.decision, username)  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
