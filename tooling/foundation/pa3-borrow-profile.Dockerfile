# Host must verify this locator against actual production learner9d2e601f...
ARG BORROW_BASE=remission-pa3-sol261022-borrow-4a:learner
FROM ${BORROW_BASE}
COPY tooling/foundation/pa3_compile_probe.py /app/pa3_compile_probe.py
COPY tooling/foundation/pa3_monitor.py /app/pa3_monitor.py
COPY tooling/foundation/pa3-borrow-profile-policy.json /app/pa3-borrow-profile-policy.json
COPY tooling/foundation/run_pa3_compile.py tooling/foundation/capture.py /app/tooling/foundation/
COPY tooling/foundation/pa3-borrow-profile-policy.json /app/tooling/foundation/pa3-borrow-profile-policy.json
COPY tests/methods/test_pa3_borrow_profile.py /app/tests/methods/
COPY tests/methods/test_pa3_numba.py tests/methods/test_pa3_cvm.py /app/tests/methods/
COPY tooling/foundation/pa3-numba-policy.json tooling/foundation/pa3-cvm-policy.json /app/tooling/foundation/
ENV PYTHONPATH=/app:/app/tooling/foundation:/app/tests/methods
USER 10002:10002
ENTRYPOINT ["python","/app/pa3_compile_probe.py"]
