""" Copyright (c) 2020 LEICOM iTEC AG. All Rights Reserved.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF
    ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
    TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
    PARTICULAR PURPOSE AND NONINFRINGEMENT.
    IN NO EVENT SHALL LEICOM BE LIABLE FOR ANY
    CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
    OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
    IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

    author: Christian Stauffer <christian.stauffer@itec-products.ch>
    date:   Winterthur, 07.12.2020
    file:   logger.py
"""
import os
import logging
from logging.handlers import TimedRotatingFileHandler

LOG_LEVEL         = logging.INFO

LOG_LEVEL_DEBUG   = logging.DEBUG
LOG_LEVEL_INFO    = logging.INFO
LOG_LEVEL_WARNING = logging.WARNING
LOG_LEVEL_ERROR   = logging.ERROR


LOG_DEFAULT_FORMAT = '%(asctime)s ; %(levelname)s ; %(name)s ; %(message)s'

def createLogger(applicationName, customLogFormat = None, loglevel = LOG_LEVEL, logFile = "./storage/logs/app.log"):
    """ Create a logger using std out and a specific format.

        the returned logger from module logging can used like:
            logger.debug('')
                .info('')
                .warning('')
                .error('')
                .critical('')

        @param[in] applicationName : name of the application should used in logging
        @param[in] customLogFormat : modify the LOG_DEFAULT_FORMAT
        @param[in] loglevel        : overwrites the default log level LOG_LEVEL

        @retval initialized instance of logging
    """
    
    logger = logging.getLogger(applicationName)

    logger.setLevel(loglevel)

    if customLogFormat == None:
        formatter = logging.Formatter(LOG_DEFAULT_FORMAT)
    else:
        formatter = logging.Formatter(customLogFormat)


    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(loglevel)
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)



    if not os.path.exists(os.path.dirname(logFile)):
        os.makedirs(os.path.dirname(logFile))
    formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(name)s;\"%(message)s\"')
    # Konfiguriere Handler, der die Logdatei rotiert und neue erstellt, wenn sie älter als 1 Tag ist
    fileHandler = TimedRotatingFileHandler(logFile, when='midnight', interval=1, backupCount=15)
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)
    




    return logger
