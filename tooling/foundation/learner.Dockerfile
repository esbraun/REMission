FROM remission-foundation-runtime:candidate
COPY contracts/domain/__init__.py contracts/domain/common.py contracts/domain/entities.py contracts/domain/boundaries.py contracts/domain/estimands.py /app/contracts/domain/
COPY contracts/runs/__init__.py contracts/runs/common.py contracts/runs/observed.py contracts/runs/admission.py contracts/runs/bindings-v1.json /app/contracts/runs/
COPY services/learner/worker.py /app/services/learner/worker.py
COPY services/learner/export_observed.py /app/services/learner/export_observed.py
COPY tooling/foundation/consumer_probe.py /app/boundary_probe.py
USER 10002:10002
CMD ["python","-m","services.learner.worker"]
