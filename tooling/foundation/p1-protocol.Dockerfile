FROM sha256:bad33f377d97f52572e182d0973b1f1f56dbc3f1c413de48f20b0458e0906fb7 AS service
COPY contracts/domain/protocol.py contracts/domain/protocol_analysis.py contracts/domain/protocol_request.py contracts/domain/borrowing.py /app/contracts/domain/
COPY services/foundation/ /app/services/foundation/

FROM sha256:9d2e601f926ae644a041903b076fdb33ff3885be1a0f390137bc61ff461584e1 AS learner
COPY contracts/domain/protocol.py contracts/domain/protocol_analysis.py contracts/domain/protocol_request.py contracts/domain/borrowing.py /app/contracts/domain/
COPY services/learner/analysis_worker.py services/learner/export_observed.py services/learner/worker.py /app/services/learner/
COPY tooling/foundation/protocol_probe.py /app/protocol_probe.py

FROM sha256:5d546abd1448e46d5d45ac4a3d98c31899631f968f93d21b163797ff0674ded9 AS generator
COPY services/generator/restricted.py services/generator/restricted_v2.py services/generator/server.py /app/services/generator/

FROM service AS controls
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app:/app/tests:/app/tests/contracts:/app/tests/integration/replay:/app/tests/generator
COPY tests/protocol_fixtures.py /app/tests/
COPY tests/contracts/test_protocol_boundary.py /app/tests/contracts/
COPY tests/generator/ /app/tests/generator/
COPY tests/integration/replay/ /app/tests/integration/replay/
COPY tests/run_contracts/observed_v2_fixtures.py /app/tests/run_contracts/
COPY services/generator/ /app/services/generator/
COPY services/learner/analysis_worker.py /app/services/learner/
COPY methods/visit/ /app/methods/visit/
COPY tooling/foundation/analysis_dispatcher.py /app/analysis_dispatcher.py
COPY tooling/foundation/run_p1_controls.py /app/run_p1_controls.py
