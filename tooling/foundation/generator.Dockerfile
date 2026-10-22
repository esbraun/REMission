FROM remission-foundation-runtime:candidate
COPY services/generator/ /app/services/generator/
USER 20000:20000
CMD ["python","-m","services.generator.server"]
