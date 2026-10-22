FROM remission-p1-native-sol-434306c-controls:candidate
COPY tests/contracts/test_protocol_boundary.py /app/tests/contracts/test_protocol_boundary.py
COPY services/learner/export_observed.py services/learner/worker.py /app/services/learner/
