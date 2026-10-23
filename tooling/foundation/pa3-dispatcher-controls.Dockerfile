ARG CONTROLS_BASE
FROM ${CONTROLS_BASE}
COPY tooling/foundation/analysis_dispatcher.py tooling/foundation/analysis_lifecycle.py /app/
COPY tests/integration/replay/test_borrowing_dispatcher.py /app/tests/integration/replay/
