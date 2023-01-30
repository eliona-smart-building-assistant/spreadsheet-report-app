import os
import traceback
import json
import time
from enum import Enum
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
import base64
from enums import ReportState
import utils.logger as log
from eliona_modules.api.core.eliona_core import ElionaApiHandler, ConStat

LOGGER_NAME = "mail"
LOGGER_LEVEL = log.LOG_LEVEL_DEBUG

class Mail:
	"""
	Handle the mail delivery.

	Will convert the attachments to base64 based file strings and send to the recipients.
	"""

	logger = None #log.createLogger(LOGGER_NAME, loglevel=LOGGER_LEVEL)
	state = ReportState.IDLE
	mailId = ""
	sendDate = datetime(1990,1,1)

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

	def sendMail(self, connection:dict, subject:str, content:str, receiver:list, blindCopyReceiver:list=None, attachments:list=None, reports:list=None) -> bool:
		"""
		Sending mail with the api V" to connect the 

		Param
		-----
		connection:dict		= Connection data for the eliona handler
		subject:str			= Subject for the mail
		content:str			= Content of the mail
		receiver:list		= List with all recipients
		attachments:list	= List with all attachments
		reports:list		= List with all reports

		Return
		------
		-> bool				= Will return true if mail was send successfully, false if not
		"""

		#set the local variables
		_mailSendSuccessfully = False
		
		try:

			#Set up the attachments
			_attachments = None
			if attachments != None:
				_attachments = self._readAttachments(attachments=attachments)
			elif reports != None:
				_attachmentsList = []
				#Iterate through all reports
				for _report in reports:

					#Add the Attachments
					_attachment = {}
					_attachment["path"] = _report["tempPath"]
					_attachment["name"] = str(_report["tempPath"]).split("/")[-1]	
					_attachmentsList.append(_attachment)

				_attachments = self._readAttachments(attachments=_attachmentsList)

			#Check the receivers
			for _receiver in receiver:
				validate_email(_receiver)


			self.logger.debug("--------connect--------")
			self.logger.debug("Host: " + str(connection["host"]))

			#Connect to the eliona instance
			eliona = ElionaApiHandler(settings=connection, logger=LOGGER_NAME)
			eliona.check_connection() 

			#Check if the connection is established
			if eliona.connection == ConStat.CONNECTED:

				#Send the mail
				self.logger.info(f"Send mail with Subject: {subject}")

				self.state = ReportState.SENDING
				_response, errMsg = eliona.send_mail(	subject=subject, 
														content=content, 
														recipients=receiver, 
														attachments=_attachments, 
														blind_copy_recipients=blindCopyReceiver)


				#Wait till the mail was send 		
				self.mailId = str(_response["id"])
				_checkCount = 0	


				while self.state != ReportState.SEND_SUCCESSFULLY:

					_response, errMsg = eliona.get_mail_state(self.mailId)

					if (_response["status"] == "scheduled"):

						self.logger.info(f"Scheduled mail with mail-ID: {self.mailId}")
						self.state = ReportState.SENDING

					elif (_response["status"] == "sent") :

						self.logger.info(f"Successfully send mail with mail-ID: {self.mailId}")
						self.state = ReportState.SEND_SUCCESSFULLY
						self.sendDate = datetime.now().date()
						_mailSendSuccessfully = True
						break

					#Escape the loop and set the state to canceled
					if _checkCount > 30:
						self.state = ReportState.CANCELED
						break

					time.sleep(20)

			else:
				self.logger.info("Connection not possible. Will try again.")

		except EmailNotValidError as err:
			self.logger.error("Invalid email\n" + err) #Print the error
			self.logger.error(traceback.format_exc())

		except Exception as err:
			self.logger.error(err) #Print the error
			self.logger.error(traceback.format_exc())

		return _mailSendSuccessfully

	def getMailState(self, connection:dict, mailId:int)->tuple[ReportState|str]:
		"""
		Get the mail state
		
		Params
		----
		mailId:int		= Id of the mail to be checked


		Return
		----
		tuple[ReportState|str]		= Status of the last mail from the eliona as ReportState and string response  
		
		"""

		self.logger.debug("--------connect--------")
		self.logger.debug("Host: " + str(connection["host"]))

		#Connect to the eliona instance
		_eliona = ElionaApiHandler(settings=connection, logger=LOGGER_NAME)
		_eliona.check_connection() 

		#Check if the connection is established
		if _eliona.connection == ConStat.CONNECTED:

			_response, errMsg = _eliona.get_mail_state(str(mailId))
			
			if (_response["status"] == "scheduled"):

				_state = ReportState.SENDING

			elif (_response["status"] == "sent") :

				_state = ReportState.SEND_SUCCESSFULLY

			else:
				_state = ReportState.UNKNOWN

		return _state, _response["status"]

	def _readAttachments(self, attachments:list)->list:
		"""
		Read the attachments and transform them to an base64 based string

		Param
		-----
		attachments:list = Attachments as a dict with: _["path"], _["name], _["contentType], _["content"] _["tempPath"]

		Return
		-----
		->list = List of the attachments with the base64 based string like: _["name], _["contentType], _["content"] = base64 String

		"""

		_attachmentBase64 = attachments

		#Iterate through all attachments and try to convert them to a base64 string 
		for _attachment in _attachmentBase64:
			
			_filePath = str(_attachment["path"])

			#Get the File and mime type
			_fileType = _filePath.split(".")[-1]
			if _fileType == "xlsx":
				_attachment["content_type"] = "application/vnd.openxmlformats-officedocument. spreadsheetml.sheet"
			elif _fileType == "xls":
				_attachment["content_type"] = "application/msexcel"
			elif _fileType == "csv":
				_attachment["content_type"] = "text/csv"
			elif _fileType == "txt":
				_attachment["content_type"] = "text/plain"
			else:
				raise TypeError

			#Get the base64 file
			with(open(file=_filePath, mode="rb") as _attachmentFile):

				if _attachmentFile != None:

					_binaryFileData = _attachmentFile.read()
					_base64EncodedData = base64.b64encode(_binaryFileData)
					_base64Message = _base64EncodedData.decode('utf-8')

					_attachment["encoding"] = "base64"
					_attachment["content"] = _base64Message


				else:
					raise FileNotFoundError("Attachment not found")

				del _attachment["path"]

			#_attachment["encoding"] = "base64"
		return _attachmentBase64


if __name__ == "__main__":
	"""
	Testing call of the class
	"""

	#Read settings File
	_settingsPath = "./testing/mailTestConfig.json"
	if os.path.isfile(_settingsPath):

		#Read the configuration file 
		with open(_settingsPath, "r") as settingsFile:
			_settings = json.load(settingsFile)

	_mailHandler = Mail()

	_content = "Hallo User, <br> das hier ist eine Testnachricht <br><br> App Version: 1.0.0"
	_receiverList = []
	_attachmentsList = []

	#Iterate through all reports
	for _report in _settings["reports"]:

		# Add the receivers
		for _receiver in _report["receiver"]:
			_receiverList.append(_receiver["msgEndpoint"])

		#Add the Attachments
		_attachment = {}
		_attachment["path"] = _report["reportPath"]
		_attachment["name"] = str(_report["reportPath"]).split("/")[-1]	
		_attachmentsList.append(_attachment)

	emptyList = []
	#Send the test mail
	_mailHandler.sendMail(	connection=_settings["eliona_handler"], 
							subject="Eliona APIv2 SpreadsheetApp Testmail Variante 1", 
							content=_content, 
							receiver=_receiverList, 
							attachments=None,
							blindCopyReceiver=_attachmentsList)

	#Send the test mail
	#_mailHandler.sendMail(	connection=_settings["eliona_handler"], 
	#						subject="Eliona APIv2 SpreadsheetApp Testmail Variante 2", 
	#						content=_content, 
	#						receiver=_receiverList, 
	#						reports=_settings["reports"])
