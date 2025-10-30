# libs/config.py

# Load all static + dynamic configuration from .env, config_data.py
# along with config_loader.py
from config_data import config as static_config
from config_loader import load_config

_config = None

def get_config():
    global _config
    if _config is None:
        _config = {**static_config, **load_config()}
    return _config

config = get_config()
