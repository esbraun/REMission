FROM remission-foundation-runtime:candidate
COPY services/generator/ /app/services/generator/
COPY contracts/domain/__init__.py contracts/domain/common.py contracts/domain/entities.py contracts/domain/boundaries.py contracts/domain/estimands.py contracts/domain/evaluation.py contracts/domain/analysis.py contracts/domain/temporal.py contracts/domain/temporal-v2.json /app/contracts/domain/
COPY contracts/dgp/__init__.py contracts/dgp/calibration.py contracts/dgp/parameters.py contracts/dgp/scenarios.py contracts/dgp/timing.py contracts/dgp/truth.py /app/contracts/dgp/
COPY contracts/runs/__init__.py contracts/runs/common.py contracts/runs/private.py contracts/runs/observed.py contracts/runs/bindings-v1.json contracts/runs/restricted-profile-v1.json /app/contracts/runs/
USER 20000:20000
CMD ["python","-m","services.generator.server"]
