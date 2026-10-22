ARG SERVICE_BASE
ARG LEARNER_BASE
ARG CONTROLS_BASE
FROM ${SERVICE_BASE} AS service
COPY services/foundation/protocol.py /app/services/foundation/
COPY contracts/domain/protocol_analysis.py /app/contracts/domain/
FROM ${LEARNER_BASE} AS learner
COPY contracts/domain/protocol_analysis.py /app/contracts/domain/
FROM ${CONTROLS_BASE} AS controls
COPY services/foundation/protocol.py /app/services/foundation/
COPY contracts/domain/protocol_analysis.py /app/contracts/domain/
COPY tests/protocol_fixtures.py /app/tests/
COPY tests/contracts/test_protocol_boundary.py /app/tests/contracts/
