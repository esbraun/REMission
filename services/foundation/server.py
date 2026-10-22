from .app import create_app
from .configuration import environment_settings

app=create_app(environment_settings())
