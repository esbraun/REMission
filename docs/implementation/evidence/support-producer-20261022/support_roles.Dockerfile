# Caller verifies the configured local RUNTIME_BASE resolves to immutable
# ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa.
# No dependency installation, broad source COPY or private learner code.
ARG RUNTIME_BASE
FROM ${RUNTIME_BASE} AS shared
COPY contracts/domain/__init__.py contracts/domain/common.py contracts/domain/entities.py contracts/domain/estimands.py contracts/domain/analysis.py contracts/domain/boundaries.py contracts/domain/observed_v2.py contracts/domain/evidence_v2.py contracts/domain/protocol.py contracts/domain/protocol_analysis.py contracts/domain/protocol_request.py /app/contracts/domain/
COPY contracts/runs/__init__.py contracts/runs/common.py contracts/runs/restricted-profile-v1.json contracts/runs/coverage_v2.py contracts/runs/support_research.py /app/contracts/runs/
COPY docs/implementation/evidence/support-producer-20261022/probe_roles.py /app/probe_roles.py
ENV PYTHONPATH=/app PYTHONSAFEPATH=1 PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
WORKDIR /app

FROM shared AS generator
COPY services/foundation/protocol.py /app/services/foundation/
COPY services/generator/restricted.py services/generator/restricted_v2.py services/generator/research_support.py /app/services/generator/
USER 10002:10002
CMD ["python","-m","services.generator.research_support"]

FROM shared AS learner
COPY methods/support/data.py methods/support/wcls.py /app/methods/support/
COPY docs/implementation/evidence/support-producer-20261022/run_support_once.py /app/run_support_once.py
USER 10002:10002
CMD ["python","/app/run_support_once.py"]
