import logging, sys
from logging.handlers import TimedRotatingFileHandler
from .config import get_optional_config_key

_LOG_CONFIG_KEY = 'log'
_LEVEL_CONFIG_KEY = 'level'
_PATH_CONFIG_KEY = 'path'
_DAYS_CONFIG_KEY = 'days'

def setup_log(config: dict):
    log_level = get_optional_config_key(config, lambda x: getattr(logging, str(x).upper()), 'info', None, _LOG_CONFIG_KEY, _LEVEL_CONFIG_KEY)
    log_path = get_optional_config_key(config, str, None, None, _LOG_CONFIG_KEY, _PATH_CONFIG_KEY)
    log_backup_count = get_optional_config_key(config, int, 0, None, _LOG_CONFIG_KEY, _DAYS_CONFIG_KEY)

    logger = logging.getLogger()
    logger.setLevel(log_level)
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')

    class ModuleFilter(logging.Filter):
        def filter(self, record):
            return record.name == 'root'
        
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(ModuleFilter())
    logger.addHandler(stdout_handler)

    if log_path:
        file_handler = TimedRotatingFileHandler(log_path, when="midnight", interval=1, backupCount=log_backup_count)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(ModuleFilter())
        logger.addHandler(file_handler)