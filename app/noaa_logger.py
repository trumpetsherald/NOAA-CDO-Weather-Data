import datetime
import logging
from logging.handlers import RotatingFileHandler
import os
import sys


class MyTimeFormatter(logging.Formatter):
    converter = datetime.datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%b-%d, %H:%M:%S")
            s = "%s.%03d" % (t, record.msecs)
        return s


LOGGER = logging.getLogger('root_logger')
LOGGER.setLevel(logging.DEBUG)

DEFAULT_LOG_NAME = os.path.splitext(
    os.path.basename(sys.argv[0])
)[0]

fh = RotatingFileHandler('%s.log' % DEFAULT_LOG_NAME,
                         maxBytes=10000000,
                         backupCount=3)
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = MyTimeFormatter(fmt='%(levelname)s - %(asctime)s - %(message)s')

fh.setFormatter(formatter)
ch.setFormatter(formatter)
LOGGER.addHandler(fh)
LOGGER.addHandler(ch)
