ARG CONTROLS_BASE
FROM ${CONTROLS_BASE}
COPY tooling/foundation/analysis_dispatcher.py /app/analysis_dispatcher.py
COPY tests/integration/replay/test_borrowing_dispatcher.py /app/tests/integration/replay/
