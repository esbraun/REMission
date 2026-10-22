FROM remission-foundation-runtime:candidate
ENV PYTENSOR_FLAGS=base_compiledir=/tmp/pytensor,floatX=float64 MPLCONFIGDIR=/tmp/matplotlib
COPY contracts/domain/__init__.py contracts/domain/common.py contracts/domain/entities.py contracts/domain/boundaries.py contracts/domain/estimands.py /app/contracts/domain/
COPY contracts/runs/__init__.py contracts/runs/common.py contracts/runs/observed.py contracts/runs/admission.py contracts/runs/bindings-v1.json /app/contracts/runs/
COPY contracts/domain/observed_v2.py contracts/domain/evidence_v2.py /app/contracts/domain/
COPY contracts/runs/observed_v2.py contracts/runs/coverage_v2.py contracts/runs/admission_v2.py contracts/runs/bindings-v2.json /app/contracts/runs/
COPY contracts/service/__init__.py contracts/service/live_hold.py contracts/service/live_safety.py contracts/service/live_safety_admission.py contracts/service/bindings-v1.json contracts/service/spec-v1.json /app/contracts/service/
COPY services/learner/worker.py /app/services/learner/worker.py
COPY services/learner/export_observed.py /app/services/learner/export_observed.py
COPY services/learner/live_product.py /app/services/learner/live_product.py
COPY contracts/domain/analysis.py contracts/domain/borrowing.py /app/contracts/domain/
COPY contracts/domain/borrow_runtime.py /app/contracts/domain/
COPY contracts/domain/cohort.py contracts/domain/cohort_runtime.py /app/contracts/domain/
COPY contracts/domain/protocol.py contracts/domain/protocol_analysis.py contracts/domain/protocol_request.py /app/contracts/domain/
COPY methods/visit/ /app/methods/visit/
COPY methods/measurement.py /app/methods/measurement.py
COPY services/learner/analysis_worker.py /app/services/learner/
COPY services/learner/cohort_worker.py /app/services/learner/
COPY tooling/foundation/consumer_probe.py /app/boundary_probe.py
COPY tooling/foundation/observed_v2_probe.py /app/observed_v2_probe.py
USER 10002:10002
CMD ["python","-m","services.learner.worker"]
