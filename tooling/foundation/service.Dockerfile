FROM node:24.22.1-bookworm-slim@sha256:1681862882da07ee5476fee047bcf34138833f1df42633bb25bcb0f438d5bf3d AS client
WORKDIR /client
COPY web/package.json web/package-lock.json ./
RUN npm ci --ignore-scripts
COPY web/ ./
RUN npm run typecheck && npm run test && npm run build

# build.py verifies this tag's exact qualified ID before invoking this build.
FROM remission-foundation-runtime:candidate AS service
COPY contracts/domain/__init__.py contracts/domain/common.py contracts/domain/entities.py contracts/domain/boundaries.py contracts/domain/estimands.py /app/contracts/domain/
COPY contracts/runs/__init__.py contracts/runs/common.py contracts/runs/observed.py contracts/runs/admission.py contracts/runs/bindings-v1.json /app/contracts/runs/
COPY contracts/runs/restricted-profile-v1.json /app/contracts/runs/
COPY contracts/runs/support_research.py /app/contracts/runs/
COPY contracts/domain/observed_v2.py contracts/domain/evidence_v2.py /app/contracts/domain/
COPY contracts/runs/observed_v2.py contracts/runs/coverage_v2.py contracts/runs/admission_v2.py contracts/runs/bindings-v2.json /app/contracts/runs/
COPY contracts/service/__init__.py contracts/service/live_hold.py contracts/service/live_safety.py contracts/service/live_safety_admission.py contracts/service/bindings-v1.json contracts/service/spec-v1.json /app/contracts/service/
COPY services/foundation/ /app/services/foundation/
COPY contracts/domain/analysis.py contracts/domain/borrowing.py /app/contracts/domain/
COPY contracts/domain/borrow_runtime.py /app/contracts/domain/
COPY contracts/domain/cohort.py contracts/domain/cohort_runtime.py /app/contracts/domain/
COPY contracts/domain/protocol.py contracts/domain/protocol_analysis.py contracts/domain/protocol_request.py contracts/domain/support_s1.py /app/contracts/domain/
COPY contracts/domain/nof1_app.py contracts/domain/nof1_config.py /app/contracts/domain/
COPY tooling/foundation/consumer_probe.py /app/boundary_probe.py
COPY tooling/foundation/observed_v2_probe.py /app/observed_v2_probe.py
COPY --from=client /client/dist/ /app/web/dist/
RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001
EXPOSE 8765
CMD ["python","-m","uvicorn","services.foundation.server:app","--host","0.0.0.0","--port","8765","--no-access-log"]

FROM service AS integration-tests
ENV PYTENSOR_FLAGS=base_compiledir=/tmp/pytensor,floatX=float64 MPLCONFIGDIR=/tmp/matplotlib
COPY tests/integration/replay/ /app/tests/integration/replay/
COPY tests/support_s1_fixtures.py /app/tests/
COPY tests/run_contracts/observed_v2_fixtures.py /app/tests/run_contracts/
COPY services/learner/worker.py services/learner/export_observed.py services/learner/live_product.py /app/services/learner/
COPY methods/visit/ /app/methods/visit/
COPY services/learner/analysis_worker.py /app/services/learner/
COPY tooling/foundation/analysis_dispatcher.py /app/analysis_dispatcher.py
COPY tooling/foundation/analysis_lifecycle.py /app/analysis_lifecycle.py
CMD ["python","-m","unittest","discover","-s","tests/integration/replay","-v"]
