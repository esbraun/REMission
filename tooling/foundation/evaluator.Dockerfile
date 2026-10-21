FROM remission-foundation-runtime:candidate
COPY tooling/foundation/evaluator_canary.py /app/evaluator_canary.py
USER 20000:20000
CMD ["python","/app/evaluator_canary.py","serve"]
