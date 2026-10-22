ARG SERVICE_BASE
FROM ${SERVICE_BASE}
# Test-only imports and genuine legacy fixtures; absent from the service image.
COPY tests/integration/replay/ /app/tests/integration/replay/
COPY tests/run_contracts/observed_v2_fixtures.py /app/tests/run_contracts/
COPY methods/visit/ /app/methods/visit/
COPY services/learner/worker.py services/learner/export_observed.py services/learner/live_product.py services/learner/analysis_worker.py /app/services/learner/
ENV PYTHONPATH=/app:/app/tests/integration/replay
ENV PYTENSOR_FLAGS=base_compiledir=/tmp/pytensor,floatX=float64 MPLCONFIGDIR=/tmp/matplotlib
