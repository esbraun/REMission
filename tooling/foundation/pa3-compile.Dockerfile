# The host verifies this local tag resolves to the retained b295 engine ID.
# Docker FROM resolves an engine-ID-shaped argument as a registry repository.
ARG TEST_BASE=remission-pa3-sol261022-compile-base-b295:candidate
FROM ${TEST_BASE}
COPY contracts/domain/analysis.py contracts/domain/borrowing.py /app/contracts/domain/
COPY methods/visit/ /app/methods/visit/
COPY tooling/foundation/pa3_compile_probe.py /app/pa3_compile_probe.py
USER 10002:10002
ENTRYPOINT ["python","/app/pa3_compile_probe.py"]
