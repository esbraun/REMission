ARG DIAGNOSIS_BASE=remission-pa3-sol261022-monitor-base-eb4:candidate
FROM ${DIAGNOSIS_BASE}
COPY tooling/foundation/pa3_compile_probe.py /app/pa3_compile_probe.py
COPY tooling/foundation/pa3_monitor.py /app/pa3_monitor.py
COPY tooling/foundation/pa3-monitor-policy.json /app/pa3-monitor-policy.json
USER 10002:10002
ENTRYPOINT ["python","/app/pa3_compile_probe.py"]
