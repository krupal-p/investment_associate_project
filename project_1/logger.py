import logging
import logging.config
from pathlib import Path

import yaml


class Logger:
    def get_logger(self) -> logging.Logger:
        log_config_path: str = "logging.yaml"

        logfile = "logs/project.log"

        if not Path("logs/").exists():
            Path("logs/").mkdir()

        if Path(log_config_path).exists():
            with Path.open(Path(log_config_path)) as f:
                config_ = yaml.safe_load(f.read())
            config_["handlers"]["info_file_handler"]["filename"] = logfile
            logging.config.dictConfig(config_)
        else:
            print("Unable to load the config using file. Using basic config")
            logging.basicConfig(level=logging.INFO)

        return logging.getLogger()


log: logging.Logger = Logger().get_logger()
