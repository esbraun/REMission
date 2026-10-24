"""Non-HTTP, once-authorized UNTRUSTED qualification entrypoint.

Only the trusted operator launcher supplies the independent GO stream and receipt
path. Matching hashes identify that external authorization; they do not create it.
No app/worker route imports run_candidate, no candidate Setting exists, and no
candidate output can install qualification or enter live history/fit/serving.
"""
from dataclasses import dataclass
import json
from contracts.domain.analysis import canonical,sha
from contracts.domain.support_s2_controller import UntrustedInteractiveInvocation,ControllerCommand


@dataclass(frozen=True)
class InstalledInteractiveContext:
    binding_json: str


class UntrustedInteractiveContext:
    """Invocation-local, connection-bound lease; never module-global readiness."""
    def __init__(self, invocation, authority, receipt, clock):
        if type(invocation) is not UntrustedInteractiveInvocation:
            raise ValueError('typed_candidate_invocation_required')
        self._raw=invocation.model_dump_json();self._authority=authority
        self._receipt=receipt;self._clock=clock;self._connection=None;self._active=True

    def bind(self, db):
        if self._connection is not None or not self._active:
            raise ValueError('candidate_connection_cannot_be_reused')
        self._connection=db

    def check(self,db,patient=None):
        from .store import SupportConnection
        if (type(self) is not UntrustedInteractiveContext or not isinstance(db,SupportConnection)
                or db is not self._connection or not self._active or self._receipt.closed or self._authority.closed
                or not db.in_transaction):
            raise ValueError('active_owned_candidate_transaction_required')
        invocation=UntrustedInteractiveInvocation.model_validate_json(self._raw)
        now=self._clock()
        if not invocation.not_before<=now<invocation.expires_at:raise ValueError('candidate_authority_expired')
        self._authority.seek(0);raw=self._authority.read(65537)
        if (len(raw)>65536 or sha(json.loads(raw))!=invocation.operation_go.sha256
                or json.loads(raw)!=invocation.authority_body):
            raise ValueError('independent_SOURCE_OP_authority_changed')
        self._receipt.seek(0)
        if self._receipt.read()!=canonical(dict(consumed=invocation.reference)).encode():
            raise ValueError('candidate_once_receipt_changed')
        packet=invocation.packet
        current=db.execute('SELECT * FROM service_control WHERE singleton=1').fetchone()
        bundle,source,runtime,control=db._candidate_installation
        if (not current or not current['enabled'] or any(current[k]!=v for k,v in json.loads(control).items())
                or (current['database_instance_id'],current['authority_generation'])!=(packet.store_id,packet.authority_generation)
                or (bundle,source,json.loads(runtime))!=(packet.installed_bundle_sha256,packet.app_commit,packet.runtime.model_dump(mode='json'))):
            raise ValueError('candidate_current_Store_source_runtime_generation_changed')
        if patient is not None:
            row=db.execute('SELECT * FROM patients WHERE id=? AND owner_id=?',(patient,invocation.owner_id)).fetchone()
            state=json.loads(row['state_json']) if row else {}
            if (patient not in invocation.cases or not row or state.get('simulation',{}).get('panel_id')!=invocation.cases[patient]
                    or state.get('simulation',{}).get('research_run_id') or state.get('historical_read_only') or state.get('observed_archive')):
                raise ValueError('candidate_exact_owned_case_generation_required')
        return invocation

    def finish(self):
        self._active=False;self._connection=None


def candidate_context(db):
    from .store import SupportConnection
    context=getattr(db,'_candidate_context',None)
    if context is None:return None
    if not isinstance(db,SupportConnection) or type(context) is not UntrustedInteractiveContext:
        raise ValueError('closed_candidate_context_required')
    context.check(db)
    return context


def run_candidate(store,settings,invocation,operations,*,external_authority):
    """Trusted operator-only entry, with separately supplied exact SOURCE/OP GO.

    External launcher custody/GO is a prerequisite, not inferred from a caller's
    digest. Receipt creation consumes it once even if the transaction fails.
    This source entrypoint grants no permission to execute without that launcher.
    """
    from pathlib import Path
    from .support_s2_controller import transition,selected
    from .simulation import advance as advance_simulation
    from .workflow import _producer_history
    if type(invocation) is not UntrustedInteractiveInvocation or store.support_qualification is not None:
        raise ValueError('isolated_uninstalled_candidate_Store_required')
    # Never retain caller-owned nested mappings as authority or operation input.
    invocation=UntrustedInteractiveInvocation.model_validate_json(invocation.model_dump_json())
    operations=json.loads(canonical(operations))
    if sha(operations)!=invocation.operations_sha256 or not operations or len(operations)>128:
        raise ValueError('exact_bounded_operations_required')
    external_authority.seek(0);raw=external_authority.read(65537)
    if len(raw)>65536 or json.loads(raw)!=invocation.authority_body or sha(json.loads(raw))!=invocation.operation_go.sha256:
        raise ValueError('external_exact_SOURCE_OP_GO_required')
    now=settings.clock()
    if not invocation.not_before<=now<invocation.expires_at:raise ValueError('candidate_authority_expired')
    # Existing exclusive-receipt pattern. No retry/replay of a consumed GO.
    with Path(invocation.receipt_path).open('x+b') as receipt:
        receipt.write(canonical(dict(consumed=invocation.reference)).encode());receipt.flush()
        context=UntrustedInteractiveContext(invocation,external_authority,receipt,settings.clock)
        try:
            with store.transaction(write=True,_support_candidate=context) as db:
                for operation in operations:
                    patient_id=operation['patient_id'];context.check(db,patient_id)
                    patient=db.execute('SELECT * FROM patients WHERE id=? AND owner_id=?',(patient_id,invocation.owner_id)).fetchone()
                    if operation['action']=='advance':
                        if set(operation)!={'patient_id','action','target'} or not isinstance(operation['target'],int):
                            raise ValueError('exact_candidate_advance_required')
                        state,sim=selected(patient)
                        if not sim['day']<operation['target']<=84:raise ValueError('bounded_forward_candidate_clock_required')
                        day=sim['day'];target=operation['target']
                        mode='day' if target==day+1 else 'visit' if target==min(84,(day//14+1)*14) else None
                        if mode is None:raise ValueError('candidate_uses_existing_day_or_visit_advance')
                        advance_simulation(db,settings,patient,patient['version'],mode,now)
                    else:
                        if set(operation)!={'patient_id','action','command'}:raise ValueError('exact_candidate_command_required')
                        command=ControllerCommand.model_validate_json(canonical(operation['command']))
                        if command.action!=operation['action']:raise ValueError('candidate_command_action_changed')
                        transition(db,settings,patient,invocation.owner_id,command,now)
                outputs=[]
                for patient_id in invocation.cases:
                    row=db.execute('SELECT * FROM patients WHERE id=? AND owner_id=?',(patient_id,invocation.owner_id)).fetchone()
                    current=json.loads(db.execute('SELECT snapshot FROM decisions WHERE id=?',(row['current_decision'],)).fetchone()[0])
                    outputs.append(dict(patient_id=patient_id,records=[r.model_dump(mode='json') for r in _producer_history(db,patient_id).records],
                        current={k:row[k] for k in ('version','state_version','consent_version','eligibility_version','cutoff','current_decision')},
                        current_snapshot=current))
                proofs=[dict(row) for row in db.execute('SELECT id,patient_id,actor_id,created_at,payload FROM state_changes WHERE patient_id IN ('+
                    ','.join('?' for _ in invocation.cases)+')',tuple(invocation.cases))]
                result=dict(status='UNTRUSTED_candidate_evidence',invocation=invocation.model_dump(mode='json'),histories=outputs,proofs=proofs)
                if len(canonical(result).encode())>invocation.output_cap:raise ValueError('candidate_evidence_cap')
                context.check(db)
            return result
        finally:context.finish()
