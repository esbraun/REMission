FROM remission-foundation-runtime:candidate AS public-contracts
COPY contracts/domain/ /app/contracts/domain/

FROM public-contracts AS study-preparation
COPY services/generator/ /app/services/generator/
USER 20000:20000
ENTRYPOINT ["python","-m","services.generator.studies"]

FROM public-contracts AS bridge-qualification
ENV PYTENSOR_FLAGS=base_compiledir=/tmp/pytensor,floatX=float64 MPLCONFIGDIR=/tmp/matplotlib OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
COPY methods/visit/ /app/methods/visit/
COPY tests/methods/ /app/tests/methods/
COPY tooling/foundation/qualify_pa3_bridge.py /app/qualify_pa3_bridge.py
USER 10002:10002
ENTRYPOINT ["python","/app/qualify_pa3_bridge.py"]

FROM bridge-qualification AS pa3-tests
COPY services/generator/ /app/services/generator/
COPY tests/generator/ /app/tests/generator/
COPY tooling/foundation/capture.py /app/capture.py
COPY tooling/foundation/run_pa3_prefit.py /app/run_pa3_prefit.py
ENTRYPOINT ["python","-m","unittest"]
