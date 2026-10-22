# Host custody verifies this tag is retained actual diagnostic image40d2.
ARG DIAGNOSIS_BASE=remission-pa3-sol261022-cvm-base-c204:candidate
FROM ${DIAGNOSIS_BASE}
COPY tooling/foundation/pa3_compile_probe.py /app/pa3_compile_probe.py
COPY tooling/foundation/pa3_monitor.py /app/pa3_monitor.py
COPY tooling/foundation/pa3-cvm-policy.json /app/pa3-cvm-policy.json
COPY tooling/foundation/run_pa3_compile.py /app/tooling/foundation/run_pa3_compile.py
COPY tooling/foundation/pa3-cvm-policy.json /app/tooling/foundation/pa3-cvm-policy.json
COPY tests/methods/test_pa3_cvm.py /app/tests/methods/test_pa3_cvm.py
USER 10002:10002
ENTRYPOINT ["python","/app/pa3_compile_probe.py"]
