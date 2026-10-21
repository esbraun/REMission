FROM python:3.13.7-slim-bookworm@sha256:adafcc17694d715c905b4c7bebd96907a1fd5cf183395f0ebc4d3428bd22d92d
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    PYTENSOR_FLAGS=floatX=float64
RUN apt-get update && apt-get install -y --no-install-recommends g++ make libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY tooling/library/requirements.lock /workspace/tooling/library/requirements.lock
RUN python -m pip install --require-hashes --report /opt/python-install-report.json -r tooling/library/requirements.lock && python -m pip check
