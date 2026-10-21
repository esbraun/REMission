import os
from pathlib import Path
from .app import Settings, create_app

app=create_app(Settings(database=Path(os.environ.get("REMISSION_DATABASE","/data/remission.sqlite")),
                        origin=os.environ.get("REMISSION_ORIGIN","http://127.0.0.1:8765"),
                        web_root=Path(os.environ.get("REMISSION_WEB_ROOT","/app/web/dist"))))
