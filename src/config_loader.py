import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# This resolves reliably: src/config_loader.py -> parent(src) -> parent(root) -> config/agent_config.yaml
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "agent_config.yaml"

def get_config():
    """Loads and returns the dictionary representation of agent_config.yaml safely."""
    if not CONFIG_PATH.exists():
        logger.error(f"Configuration file missing critically at {CONFIG_PATH}")
        raise FileNotFoundError(f"Missing configuration file at {CONFIG_PATH}")
    
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

