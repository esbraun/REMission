# Host custody verifies this tag against retained actual Monitor image4ca2.
ARG DIAGNOSIS_BASE=remission-pa3-sol261022-numba-base-f0:candidate
FROM ${DIAGNOSIS_BASE}
COPY tooling/foundation/pa3_compile_probe.py /app/pa3_compile_probe.py
COPY tooling/foundation/pa3_monitor.py /app/pa3_monitor.py
COPY tooling/foundation/pa3-numba-policy.json /app/pa3-numba-policy.json
# Controls use the same copied probe/helper and host-runner bytes, no models.
COPY tooling/foundation/run_pa3_compile.py tooling/foundation/capture.py /app/tooling/foundation/
COPY tooling/foundation/pa3-numba-policy.json /app/tooling/foundation/pa3-numba-policy.json
COPY tests/methods/test_pa3_numba.py /app/tests/methods/test_pa3_numba.py
ENV PYTHONPATH=/app:/app/tooling/foundation
USER 10002:10002
ENTRYPOINT ["python","/app/pa3_compile_probe.py"]
