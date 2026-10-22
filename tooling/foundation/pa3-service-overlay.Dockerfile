# The preparation helper verifies this local tag's immutable engine ID first.
ARG SERVICE_BASE
FROM ${SERVICE_BASE}
COPY services/foundation/analysis.py services/foundation/analysis_cli.py /app/services/foundation/
COPY contracts/domain/borrow_runtime.py /app/contracts/domain/
