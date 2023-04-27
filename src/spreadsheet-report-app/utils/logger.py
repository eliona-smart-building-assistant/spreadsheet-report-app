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
import logging

LOG_LEVEL         = logging.INFO

LOG_LEVEL_DEBUG   = logging.DEBUG
LOG_LEVEL_INFO    = logging.INFO
LOG_LEVEL_WARNING = logging.WARNING
LOG_LEVEL_ERROR   = logging.ERROR


LOG_DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

#For debug purposes only
#logging.basicConfig(filename="log.log", encoding="utf-8", format=LOG_DEFAULT_FORMAT)
logging.basicConfig(encoding="utf-8", format=LOG_DEFAULT_FORMAT)

def createLogger(applicationName, customLogFormat = None, loglevel = LOG_LEVEL):
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
    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(loglevel)

    if customLogFormat == None:
        formatter = logging.Formatter(LOG_DEFAULT_FORMAT)
    else:
        formatter = logging.Formatter(customLogFormat)

    consoleHandler.setFormatter(formatter)

    logger.addHandler(consoleHandler)

    return logger
