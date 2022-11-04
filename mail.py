import logging
import os
import json
from enum import Enum
from datetime import datetime
#from eliona_modules.api.core.eliona_core import ElionaApiHandler, ConStat
#from eliona.api_client.model.message import Message

logging.basicConfig(filename="log.log", encoding="utf-8")
LOGGER_NAME = "mail"
LOGGER = logging.getLogger(LOGGER_NAME)
HANDLER = logging.StreamHandler()
HANDLER.setLevel(logging.DEBUG)
LOGGER.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter(fmt="%(asctime)s: %(name)s: %(levelname)s: %(lineno)d: %(message)s", datefmt="%d-%m-%y %H:%M:%S")
HANDLER.setFormatter(FORMATTER)
LOGGER.addHandler(HANDLER)

class MailState(Enum):
    """
	Mail state definition
	"""
    IDLE = 0

    CREATION = 1
    QUED = 20
    SEND = 30

    CANCELED  = 100

class Mail:
	"""
	Handle the mail delivery.
	Will check for mail send after scheuled time reached.

	Will async report about the state
	"""


	def __init__(self) -> None:
		"""
		Init the class

		Param
		-----
		Return
		-----
		-> None
		"""

		self.state = MailState.IDLE
		self.sendDate = datetime(1990,1,1)

		pass


	def sendMail(self, connection:dict, sender:dict, report:dict) -> None:
		"""
		Sending mail with the api V" to connect the 

		Param
		-----
		connection:dict		= Connection data for the eliona handler
		sender:dict			= sender information
		report:dict			= report data

		Return
		------
		-> None
		"""


		#set the local variables
		_mailSendSuccessfully = False

		LOGGER.info("--------connect--------")
		LOGGER.debug("Host: " + str(connection["host"]))

		#Connect to the eliona instance
		#eliona = ElionaApiHandler(settings=connection, logger=LOGGER_NAME)
		#eliona.check_connection() 

		#Check if the connection is established
		if True: #eliona.connection == ConStat.CONNECTED:

			#Send the mail
			LOGGER.debug("Send mail")
			
		else:
			LOGGER.info("Connection not possible. Will try again.")

		return _mailSendSuccessfully



if __name__ == "__main__":
	"""
	Main entry point for debugging the class
	"""

	#Read settings File
	_settingsPath = "./tmp_reports/Cust_Config/config.json"
	if os.path.isfile(_settingsPath):

		#Read the configuration file 
		with open(_settingsPath, "r") as settingsFile:
			_settings = json.load(settingsFile)



	_mailHandler = MailHandler()
	_mailHandler.sendMail(connection=_settings["eliona_handler"], sender=_settings["mail"], report=["reports"][0])
