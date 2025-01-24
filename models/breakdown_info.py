from pydantic import BaseModel
from .execution_plan_stats import ExecutionPlanStats
from .proposed_tickets import ProposedTickets

class BreakdownInfo(BaseModel):
    execution_plan: ExecutionPlanStats
    proposed_tickets: ProposedTickets 