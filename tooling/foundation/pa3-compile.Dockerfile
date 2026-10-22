# The build command supplies the retained, actual b295 copied-test engine ID.
ARG TEST_BASE
FROM ${TEST_BASE}
COPY contracts/domain/analysis.py contracts/domain/borrowing.py /app/contracts/domain/
COPY methods/visit/ /app/methods/visit/
COPY tooling/foundation/pa3_compile_probe.py /app/pa3_compile_probe.py
USER 10002:10002
ENTRYPOINT ["python","/app/pa3_compile_probe.py"]
