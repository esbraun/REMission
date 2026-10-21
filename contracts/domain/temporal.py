"""Machine-readable structural parent/order checks, with no numerical DGP choices."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .common import Identifier, Name, PositiveInt, StrictModel, Versioned
from .estimands import EstimandID


class Parent(StrictModel):
    variable: Identifier
    day_offset: Annotated[int, Field(le=0)]


class Variable(StrictModel):
    id: Identifier
    phase: Annotated[int, Field(ge=0)]
    unit: Name
    visibility: Literal["observed", "evaluator_only", "administrative"]
    parents: list[Parent]
    role_by_estimand: dict[EstimandID, Literal["covariate", "treatment", "mediator", "outcome", "observation_indicator", "intercurrent_event", "administrative"]]
    postassignment_role_by_estimand: dict[EstimandID, Literal["covariate", "treatment", "mediator", "outcome", "observation_indicator", "intercurrent_event", "administrative"]]
    source_locator: Name


class TemporalContract(Versioned):
    kind: Literal["temporal_contract"]
    id: Literal["TIME-01"]
    version: Literal["1.0.0"]
    timestamp_rule: Literal["timezone_aware_utc_order_local_calendar_preserved"]
    learner_cutoff_rule: Literal["event_at_lte_cutoff_recorded_and_available_strictly_before"]
    tie_rule: Literal["phase_then_stable_record_id_known_holds_and_withdrawals_before_draw"]
    daily_factorization: Annotated[list[Name], Field(min_length=1)]
    initial_distribution: Literal["must_be_versioned_by_G0_DGP_before_generation"]
    irregular_visit_process: Literal["must_be_versioned_by_G0_DGP_before_generation"]
    variables: Annotated[list[Variable], Field(min_length=1)]
    pending_numerical_decisions: Annotated[list[Name], Field(min_length=1)]

    @model_validator(mode="after")
    def no_future_or_same_phase_cycle(self):
        variables = {v.id: v for v in self.variables}
        if len(variables) != len(self.variables):
            raise ValueError("duplicate structural variable")
        for variable in self.variables:
            if not variable.role_by_estimand or variable.role_by_estimand.keys() != variable.postassignment_role_by_estimand.keys():
                raise ValueError("each variable requires estimand-specific role declarations")
            for parent in variable.parents:
                if parent.variable not in variables:
                    raise ValueError("unknown structural parent")
                if parent.day_offset == 0 and variables[parent.variable].phase >= variable.phase:
                    raise ValueError("same-day parent must precede child, preventing cycles/future leakage")
        return self
