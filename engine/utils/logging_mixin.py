#  Copyright 2022 SkyAPM org
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


import logging
import logging.config
from typing import Optional

LOGGING_LEVEL = logging.INFO  # TODO change to config file entry
LOG_TARGET_FOLDER = 'logs'  # TODO change to config file entry

CONFIGURATION = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'engine': {
            'format': '%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s',
        }
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'engine',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'engine',
            'filename': 'engine.log',
            'maxBytes': 100 * 1024 * 1024,
            'backupCount': 5,
            # 'target_folder': os.path.expanduser(LOG_TARGET_FOLDER),  # this is where you find the logs
        }
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': LOGGING_LEVEL,
    },

}

logging.config.dictConfig(CONFIGURATION)


class LoggingMixin:
    """
    Classes with need for logging should multi-inherit this class
    """
    _logger: Optional[logging.Logger] = None

    # todo try lazy initialization
    @property
    def logger(self) -> logging.Logger:
        if not self._logger:
            self._logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')
            self._logger.info('Logger for class %s initialized', self.__class__.__name__)

        return self._logger


if __name__ == '__main__':
    class Test(LoggingMixin):
        def __init__(self):
            self.logger.info('test info level log')
            self.logger.debug('test debug level log')


    t = Test()
