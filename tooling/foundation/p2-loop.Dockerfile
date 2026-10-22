ARG SERVICE_BASE
ARG CONTROLS_BASE
# Caller verifies the exact immutable local parent IDs before COPY-only build.
FROM ${SERVICE_BASE} AS service
COPY services/foundation/app.py services/foundation/simulation.py services/foundation/workflow.py services/foundation/nof1.py services/foundation/nof1_clock.py /app/services/foundation/
COPY web/dist/ /app/web/dist/

FROM ${CONTROLS_BASE} AS controls
COPY services/foundation/app.py services/foundation/simulation.py services/foundation/workflow.py services/foundation/nof1.py services/foundation/nof1_clock.py /app/services/foundation/
COPY tests/generator/test_nof1_loop.py /app/tests/generator/
COPY tests/contracts/test_nof1_clock.py /app/tests/contracts/
