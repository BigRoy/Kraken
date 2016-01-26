import sys
import logging
from logging import NullHandler
from widget_handler import WidgetHandler

def getLogger(name=None, level=logging.DEBUG):

    if name == None:
        name = 'Kraken'
    else:
        name = 'Kraken.' + name

    print __name__

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(NullHandler())

    streamHandler = WidgetHandler() #logging.StreamHandler()
    formatter = logging.Formatter('%(name)s [%(levelname)s]: %(message)s')
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)

    return logger

if __name__ == "__main__":
    logger = getLogger(name='bob')
    logger.debug('blah')
    logger.debug('blah2')

    sys.exit()
