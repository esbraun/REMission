"""Fresh isolated control fixture, no imported DB or model outputs."""
from pathlib import Path
from live_helpers import fresh_store
from services.foundation.cli import seed

store=fresh_store(Path('/data/remission.sqlite'))
seed(store)
Path('/fixtures/bundle.json').write_text(store.installed.model_dump_json(),encoding='utf-8')
print('Fresh synthetic control fixture seeded; no analysis attempts or posterior outputs.')
