import logging
import os
import sys
import json
from enum import Enum
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
import base64
from enums import ReportState
import utils.logger as log
from eliona_modules.api.core.eliona_core import ElionaApiHandler, ConStat
from eliona.api_client.model.message import Message


LOGGER_NAME = "mail"

class Mail:
	"""
	Handle the mail delivery.
	Will check for mail send after scheuled time reached.

	Will async report about the state
	"""

	logger = None
	state = ReportState.IDLE
	sendDate = datetime(1990,1,1)
	config = {}
	messageData = None

	def __init__(self, logLevel:int=log.LOG_LEVEL_DEBUG) -> None:
		"""
		Init the class

		Param
		-----
		Return
		-----
		-> None
		"""
		self.logger = log.createLogger(LOGGER_NAME, loglevel=logLevel)


	def configure(self, senderConfig:dict, receiver:list, attachments:list, mailData:dict)->bool:
		"""
		Configure the mail handler

		Param
		-----
		configuration:dict = Configuration of mail sender 

		Return
		-----
		->bool = Will return true if configuration ist valid // Will return false if configuration is not valid
		"""
		_retVal = True

		#Set the message object
		

		try:

			#Set up the sender configuration
			self.config["sender"] = {}

			#Setup the sender config
			self.config["sender"]["mail"] = validate_email(senderConfig["sender"])

			#Try to open the file path.
			_filePath = senderConfig["template"]["path"]
			with(open(file=_filePath, mode="r") as templateFile):
				if templateFile == None:
					_retVal = False

			self.config["sender"]["templatePath"] = _filePath
			self.config["sender"]["templateType"] = senderConfig["template"]["MimeType"]


			#Set up the attachments
			self.config["Attachments"] = self._readAttachments(attachments=attachments)


			#Set up the receivers
			self.config["receiver"] = []

			for _receiver in receiver:
				self.config["receiver"].append(validate_email(_receiver))


			#Set up the "html mail body
			#self.config["messageBody"] = self._createHtmlBody(htmlTemplate=senderConfig["template"]["path"], data=mailData)
			_content = mailData["REPORT_HEADER"] + "<br>" + mailData["REPORT_BODY"] + "<br>" + mailData["APP_VERSION"]

			#Set up the message data
			self.messageData = Message(recipients=self.config["receiver"], content=_content, sender=self.config["sender"]["mail"])


		except EmailNotValidError as e:

			self.logger.error("Invalid email\n" + e) #Print the error

		except:

			e = sys.exc_info()[0] #Get the error
			self.logger.error(e) #Print the error
			_retVal = False

		return _retVal


	def sendMail(self, connection:dict, sender:dict, reports:list ) -> None:
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

		self.logger.info("--------connect--------")
		self.logger.debug("Host: " + str(connection["host"]))

		#Connect to the eliona instance
		#eliona = ElionaApiHandler(settings=connection, logger=LOGGER_NAME)
		#eliona.check_connection() 

		#Check if the connection is established
		if True: #eliona.connection == ConStat.CONNECTED:

			#Send the mail
			self.logger.debug("Send mail")
			
		else:
			self.logger.info("Connection not possible. Will try again.")

		return _mailSendSuccessfully


	def _readAttachments(self, attachments:list)->list:
		"""
		Read the attachments and transform them to an base64 based string

		Param
		-----
		attachments:list = Attachments paths as a list

		Return
		-----
		->list = List of the attachments as a base64 based string in the same order

		"""

		_attachmentBase64 = []

		#Iterate through all attachments and try to convert them to a base64 string 
		for _attachment in attachments:
			
			with(open(file=_attachment, mode="rb") as _attachmentFile):

				if _attachmentFile != None:

					_binaryFileData = _attachmentFile.read()
					_base64EncodedData = base64.b64encode(_binaryFileData)
					_base64Message = _base64EncodedData.decode('utf-8')

					_attachmentBase64.append(_base64Message)

				else:
					raise FileNotFoundError("Attachment not found")


		return _attachmentBase64

		pass


	def _createHtmlBody(self, htmlTemplate:str, data:dict)->str:
		"""
		Create the HTML Body for the mail to be send.
		
		Param
		----
		config:dict = configuration with the path of the template and the data for the placeholders
	
		Return
		----
		->str = Will return the html body as string
		"""

		_htmlBody = ""

		with(open(file=htmlTemplate, mode="r") as templateFile):
			if templateFile != None:
				_retVal = False

				#Read the html body
				_htmlBody = templateFile.read()

				#Read the data 
				for _dataKey in data:
					_htmlBody.replace(_dataKey, data[_dataKey])

			else:
				_htmlBody = ""
				raise FileNotFoundError("HTML Body template not found")

		#Return the html body
		return _htmlBody
		


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


	_htmlBody = {}

	_htmlBody["APP_VERSION"] = "1.0.0"
	_htmlBody["REPORT_HEADER"] = "Reports from 01.01.2022 to 31.01.2022"
	_htmlBody["REPORT_BODY"] = "Reports:  \n"


	_mailHandler = Mail()

	_receiverList = []
	_attachmentsList = []

	#Iterate through all reports
	for _report in _settings["reports"]:

		_htmlBody["REPORT_BODY"] = _htmlBody["REPORT_BODY"] + "	- " + _report["name"]

		# Add the receivers
		for _receiver in _report["receiver"]:
			_receiverList.append(_receiver["msgEndpoint"])


		#Add the Attachments
		_attachmentsList.append(_report["reportPath"])


	_senderConfigValid = _mailHandler.configure(senderConfig=_settings["mail"], receiver=_receiverList, attachments=_attachmentsList, mailData=_htmlBody)

	print(f"Sender config is valid: {_senderConfigValid}")
	_mailHandler.sendMail(connection=_settings["eliona_handler"], sender=_settings["mail"], report=_settings["reports"][0])
