FROM rocker/r-ver:4.5.2@sha256:fd4ccdd3a4a6f7ef805e2daeee2a0fe3bf126bc231f36351223baecf5a595a4c
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MAKEFLAGS=-j2
RUN apt-get update && apt-get install -y --no-install-recommends libcurl4-openssl-dev libssl-dev libxml2-dev libtbb-dev && rm -rf /var/lib/apt/lists/*
COPY tooling/library/install-offline.R /opt/remission-install.R
RUN Rscript /opt/remission-install.R
WORKDIR /workspace
