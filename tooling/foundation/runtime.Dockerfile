# Build entrypoint verifies this local tag is the exact accepted image ID
# be4bbf...; a Docker image config ID is not a registry manifest reference.
FROM remission-python-locked:20261020
COPY tooling/foundation/requirements.in /opt/foundation/requirements.in
COPY tooling/library/requirements.lock /opt/foundation/numerical.lock
RUN python -c "from pathlib import Path;p=Path('/opt/foundation');p.joinpath('constraints.txt').write_text(''.join(line.split(' --hash=')[0]+'\n' for line in p.joinpath('numerical.lock').read_text().splitlines() if line and not line.startswith('#')))" \
 && python -m pip install --no-cache-dir --report /opt/foundation/install-report.json -c /opt/foundation/constraints.txt -r /opt/foundation/requirements.in \
 && python -m pip check
# Use the standard Python sqlite3 driver with an independently pinned current
# upstream library. The original numerical image/locks are never modified.
RUN python -c "import urllib.request,hashlib,zipfile,io;raw=urllib.request.urlopen('https://www.sqlite.org/2026/sqlite-amalgamation-3540100.zip').read();assert hashlib.sha3_256(raw).hexdigest()=='92281c86e2957f9b9305890f9ac04204caa7b677cc868dc326d942689df28e30';zipfile.ZipFile(io.BytesIO(raw)).extractall('/tmp/sqlite-source')" \
 && mkdir -p /opt/foundation/sqlite \
 && gcc -shared -fPIC -O2 -DSQLITE_THREADSAFE=1 -DSQLITE_ENABLE_FTS5 -DSQLITE_ENABLE_RTREE /tmp/sqlite-source/sqlite-amalgamation-3540100/sqlite3.c -o /opt/foundation/sqlite/libsqlite3.so.0 -ldl -lpthread -lm \
 && rm -rf /tmp/sqlite-source
ENV LD_LIBRARY_PATH=/opt/foundation/sqlite PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN python -c "import sqlite3;assert sqlite3.sqlite_version=='3.54.1'"
