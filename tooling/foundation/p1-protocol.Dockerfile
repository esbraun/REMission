ARG SERVICE_BASE
ARG LEARNER_BASE
ARG GENERATOR_BASE
# Caller verifies each local base tag's exact immutable engine ID before build.
FROM ${SERVICE_BASE} AS service
COPY contracts/domain/protocol.py contracts/domain/protocol_analysis.py contracts/domain/protocol_request.py contracts/domain/borrowing.py /app/contracts/domain/
COPY services/foundation/ /app/services/foundation/

FROM ${LEARNER_BASE} AS learner
COPY contracts/domain/protocol.py contracts/domain/protocol_analysis.py contracts/domain/protocol_request.py contracts/domain/borrowing.py /app/contracts/domain/
COPY services/learner/analysis_worker.py services/learner/export_observed.py services/learner/worker.py /app/services/learner/
COPY tooling/foundation/protocol_probe.py /app/protocol_probe.py

FROM ${GENERATOR_BASE} AS generator
COPY services/generator/restricted.py services/generator/restricted_v2.py services/generator/server.py /app/services/generator/

FROM service AS controls
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app:/app/tests:/app/tests/contracts:/app/tests/integration/replay:/app/tests/generator
COPY tests/protocol_fixtures.py /app/tests/
COPY tests/contracts/test_protocol_boundary.py /app/tests/contracts/
COPY tests/generator/ /app/tests/generator/
COPY tests/integration/replay/ /app/tests/integration/replay/
COPY tests/run_contracts/observed_v2_fixtures.py /app/tests/run_contracts/
COPY services/generator/ /app/services/generator/
COPY services/learner/analysis_worker.py services/learner/export_observed.py services/learner/worker.py /app/services/learner/
COPY methods/visit/ /app/methods/visit/
COPY tooling/foundation/analysis_dispatcher.py tooling/foundation/analysis_lifecycle.py /app/
COPY tooling/foundation/run_p1_controls.py /app/run_p1_controls.py
