"""
Module to handle Report and User Based reportings
"""

import os
import json
from mail import Mail
from spreadsheet import Spreadsheet
from threading import Thread
from datetime import datetime, timedelta, timezone
import pytz
from enums import Schedule, ReportState
from typing import Tuple
import unicodedata
import re
import utils.logger as log


LOGGER_LEVEL = log.LOG_LEVEL_DEBUG

class BasicReport:
	"""
	Base class for the sender classes

	will contain all the basic methods and variables
	"""

	name=""

	loggerLevel = log.LOG_LEVEL_INFO
	"""
	Logger level fall dependencies
	"""

	logger = log.createLogger("BASE Send class", loglevel=LOGGER_LEVEL)
	"""
	Logger fo the sending class
	"""

	state = ReportState.IDLE
	"""
	Current state of the report:
		- IDLE = 0
		- CREATING = 1
		- SENDING = 30
		- SEND_SUCCESSFULLY = 50
		- CANCELED  = 100
		- UNKNOWN = 500
	"""

	lastSend:datetime = datetime(1979, 1, 1)
	"""
	Date of the last send message. Will be 1979.1.1 if never send
	"""

	storePath = "./tmp_reports/"
	"""
	Path to save the temp files to 
	"""

	elionaConfig = {}
	"""
	Eliona connection settings
	"""

	recipients = []
	"""
	List of the recipients to send the mail to.
	"""

	blindCopyRecipients = []
	"""
	List of the blind copy recipients to send the mail to.
	"""

	reports = []
	"""
	List of the reports to be send
	report is an dictionary with these required key's
		- "name": "Name of the report",
		- "reportPath": "Path of the Report file",
	"""

	mailHandler = None
	"""
	Handler to send mails and check the mail state
	"""

	reportSchedule = Schedule.MONTHLY
	"""
	Schedule of the report:
		- YEARLY = 0,
		- MONTHLY = 1,
		- WEEKLY = 2,
		- DAILY = 3
	"""

	tempFilePath = ""
	"""
	Filepath for temporary created spreadsheet files
	"""

	testing = True
	currentTestTime:datetime

	def __init__(self, name:str, tempFilePath:str, logLevel:int, testing:bool) -> None:
		"""
		Init the class

		Param
		-----
		Return
		-----
		-> None
		"""

		self.testing = testing
		self.name = name
		_fileName = self._slugify(value=name)

		#Set the Log Level 
		self.loggerLevel = logLevel

		#Update the log handler
		self.logger.setLevel(self.loggerLevel)
		self.logger.name = self.name

		self.mailHandler = Mail(logLevel=self.loggerLevel)

		#Set the temp storage
		_storePath = tempFilePath + "lastSend/"
		self._dirHandling(_storePath)
		self.storePath = f"{_storePath}{_fileName}.json"
		self.readStorage()
		
		self.tempFilePath = tempFilePath

	def wasReportSend(self, timestamp:datetime)->bool:
		"""
		Will check if the requested report was already send

		Params
		------
		timestamp:datetime	= Timestamp to check

		Return
		------
		->bool				= Will return true if report was already send. False if not
		"""
				
		_reportWasSend = False
		
		if self.reportSchedule == Schedule.MONTHLY:
			
			if (timestamp.month == self.lastSend.month) and (timestamp.year == self.lastSend.year):
				_reportWasSend = True

		elif self.reportSchedule == Schedule.YEARLY:

			if (timestamp.year != self.lastSend.year):
				_reportWasSend = True

		return _reportWasSend 

	def readStorage(self)->bool:
		"""
		read the own storage

		Params
		------
		
		Return
		------
		->bool	= Will return true if data was successfully read
		"""

		_readStorageSuccessfully = False

		try:
			if os.path.isfile(self.storePath):

				#Read the configuration file 
				with open(self.storePath, "r") as settingsFile:
					_storageJson = json.load(settingsFile)

					#Get the data from the storage 
					_dateTimeStrFormat = "%Y-%m-%d"
					self.lastSend = datetime.strptime(_storageJson["LastSend"], _dateTimeStrFormat)
					_readStorageSuccessfully = True
			else:
				with open(self.storePath, "w") as settingsFile:
					_data = {}
					_data["LastSend"] = self.lastSend.date().isoformat()
					json.dump(_data, settingsFile)

		except Exception as err:
			self.logger.warning(err)
			_readStorageSuccessfully = False		

		return _readStorageSuccessfully

	def configure(self, elionaConfig:dict)->bool:
		"""
		Configure the object

		Params
		------
		config:dict			= Dictionary of the configuration
		elionaConfig:dict	= Dictionary with the eliona configuration {"host", "api", "projectId", "apiKey", "dbTimeZone"}
		Return
		------
		->bool			= Will Return True if configuration is valid // False if not

		"""

		_configState = False

		# Configure the object		
		self.elionaConfig = elionaConfig
		_configState = True

		return _configState

	def sendReport(self, year:int, month:int=0, createOnly:bool=False, sendAsync:bool=True, subject:str="", content:str="") -> None:
		"""
		Create and send the report.

		Params
		------
		subject:str			= Subject of the mail
		content				= Content of the mail
		year:int			= Year of the requested report
		month:int			= Month of the requested report. If 0 => Yearly report will be created
		sendAsync:bool		= Set to True if you want to send it asynchronous
									to False if you want to send it now and wait for it to be send

		Return
		------
		->None				= No returns 											
		"""

		#Define the report name's wit start and end time
		_reportName = ""
		for _report in self.reports:

			#Define the report name
			if _reportName == "":
				_reportName = _report["name"]
			else:
				_reportName = _reportName + " " + _report["name"]

		#Define the subject
		if subject == "":
			_subject = f"Report ({_reportName}) vom {month}.{year}"
		else:
			_subject = subject

		#Define the content
		if content == "":
			_content = f"Hallo liebe user, <br><br>im Anhang befindet sich der Report ({_reportName}) für den Zeitraum vom {month}.{year}.<br>"
			_content = _content + "Alle weiteren Informationen sind in den Reports enthalten."
		else:
			_content = content


		self.state = ReportState.CREATING
		_thread = Thread(target=self._process, args=(year, month, _subject, _content, createOnly))
		_thread.start()

		if not sendAsync:
			
			#if not send async wait till done
			_thread.join()

	def _process(self, year:int, month:int, subject:str, content:str, createOnly:bool):
		"""
		Thread to create and send the Report
		"""
		_reports = []
		_created = False

		#Create the report
		for _report in self.reports:
			_created = self._create(report=_report, year=year, month=month)

			#Add the reports to the send list if created
			if _created:
				_reports.append(_report)

		#Send the mail
		if not createOnly: 
			self._send(subject=subject, content=content, reports=_reports)

	def _create(self, report:dict, year:int, month:int) -> bool:
		"""
		Call the reporter object with the requested settings and TimeSpan

		report:dict 			= Settings of the report as dictionary
		year:int				= Year create the report from
		month:int				= Month to create the report from

		Return: bool -> Will return true if report was successfully created
		"""

		#get the start and stop date
		if report["schedule"] == "yearly":
			_reportSchedule = Schedule.YEARLY
		else:
			_reportSchedule = Schedule.MONTHLY

		self.state = ReportState.CREATING
		_reportName = report["name"]


		#Get the start and stop time
		_startStamp, _stopStamp = self._getReportTimeSpan(schedule=_reportSchedule, timeZone=self.elionaConfig["dbTimeZone"], year=year, month=month)

		_dayDelta = timedelta(days=1)
		report["tempPath"] = self.tempFilePath + str(report["reportPath"]).split(".")[0] + "_" + _startStamp.date().isoformat() + "_" + (_stopStamp.date() - _dayDelta).isoformat() + "." + str(report["reportPath"]).split(".")[-1]

		self.logger.info(f"Call the reporting function for report: '{_reportName}' with start: '{_startStamp}' and end timestamp '{_stopStamp}'")

		#Call the reporting function
		_reporter = Spreadsheet(logLevel=self.loggerLevel)
		_reportSendFeedBack = _reporter.createReport(startDt=_startStamp, endDt=_stopStamp, connectionSettings=self.elionaConfig, reportSettings=report)

		self.logger.info(f"Report: {_reportName} was send successfully created: {_reportSendFeedBack}")


		return _reportSendFeedBack

	def _send(self, subject:str, content:str, reports:list):
		"""
		Send the created reports to the configured receivers
		
		Params
		-----
		subject:str		= Subject of the mail
		content:str		= content of the mail in html format
		
		"""

		self.state = ReportState.SENDING
		_mailState = self.mailHandler.sendMail(	connection=self.elionaConfig, 
												subject=subject, 
												content=content, 
												receiver=self.recipients,
												blindCopyReceiver=self.blindCopyRecipients,
												reports=reports)

		if _mailState:

			#Store the current time stamp that we have send the Data			

			if self.testing:
				self.lastSend = self.currentTestTime
			else:
				self.lastSend = datetime.now()
	
			self.state = ReportState.IDLE
			
			#update the storage 
			with open(self.storePath, "r+") as jsonFile:
				_data = json.load(jsonFile)

				_data["LastSend"] = self.lastSend.date().isoformat()

				jsonFile.seek(0)  # rewind
				json.dump(_data, jsonFile)
				jsonFile.truncate() # remove the "old" overlapping data
		else:
			self.state = ReportState.CANCELED

	def _getReportTimeSpan(self, schedule:Schedule, timeZone:str, year:int, month:int=1) -> Tuple[datetime, datetime]:
		"""
		Will return the last time span depending on the schedule settings

		Params
		-----
		schedule:str = Schedule setting as a string can be: "yearly", "monthly", "weekly" (Not Implemented), "daily" (Not implemented)

		Return Values
		-----
		-> Tuple [StartTimeStamp:datetime = Start time of the report,
					EndTimeStamp:datetime = End time of the report]

		"""

		_startTime = datetime(1979, 1, 1)
		_endTime = datetime(1979, 1, 1)
		_timeZone = pytz.timezone(timeZone)


		if schedule == Schedule.YEARLY:

			_startTime = datetime(year=(year -1), month=1, day=1)
			_endTime = datetime(year=(year-1), month=12, day=31)

		elif schedule == Schedule.MONTHLY:

			if (month == 1):

				_startTime = datetime(year=(year - 1), month=12, day=1)
				_endTime = datetime(year=(year), month=1, day=1)

			else:
				_startTime = datetime(year=(year), month=(month - 1), day=1)
				_endTime = datetime(year=(year), month=(month), day=1)

		elif schedule == Schedule.WEEKLY:

			pass

		elif schedule == Schedule.DAILY:

			pass

		else:
			self.logger.error("Could define time span for schedule: {schedule}")


		_startTime = _startTime.astimezone(_timeZone)
		_endTime = _endTime.astimezone(_timeZone)


		return (_startTime, _endTime)

	def _slugify(self, value, allow_unicode=False):
		"""
		Taken from https://github.com/django/django/blob/master/django/utils/text.py
		Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
		dashes to single dashes. Remove characters that aren't alphanumerics,
		underscores, or hyphens. Convert to lowercase. Also strip leading and
		trailing whitespace, dashes, and underscores.
		"""
		value = str(value)
		if allow_unicode:
			value = unicodedata.normalize('NFKC', value)
		else:
			value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
		value = re.sub(r'[^\w\s-]', '', value.lower())
		return re.sub(r'[-\s]+', '-', value).strip('-_')

	def _dirHandling(self, path) -> bool:
		"""
		Check if path exists otherwise try to create it

		Params
		-----
		path:str	= Path to check / create
		Return
		-----
		Will Return True if Path is available // Will return False if Path is not available
		"""
		_retVal = False
		
		if not os.path.exists(path):

			try:
				os.makedirs(path)
				_retVal = True
			except:
				self.logger.error("Could not create directory. Please check permissions")

		return _retVal



class User(BasicReport):
	"""
	Object to handle all reports for one user
	"""

	
	def __init__(self, name:str, tempFilePath:str, logLevel:int, testing:bool) -> None:
		"""
		Initialise the object
		"""
		super().__init__(name, tempFilePath, logLevel, testing)
		self.logger.debug("Init the user object")

	def configure(self, elionaConfig:dict, userConfig:dict={}, reportConfig:dict={})->bool:

		_reports = []

		#Add the reports to the list
		for _ReportName in userConfig["reports"]:

			for _reportConfig in reportConfig:
				
				if _reportConfig["name"] == _ReportName:

					_reports.append(_reportConfig)

		#Add the reports
		self.reports = _reports

		#Add the user to the list
		self.blindCopyRecipients = None
		self.recipients = []
		self.recipients.append(userConfig["msgEndpoint"])

		return super().configure(elionaConfig=elionaConfig)

	def sendReport(self, year:int, month:int=0, createOnly:bool=False, sendAsync:bool=True, subject:str="", content:str="") -> None:
		"""
		Create and send the report.

		Params
		------
		subject:str			= Subject of the mail
		content				= Content of the mail
		year:int			= Year of the requested report
		month:int			= Month of the requested report. If 0 => Yearly report will be created
		sendAsync:bool		= Set to True if you want to send it asynchronous
									to False if you want to send it now and wait for it to be send

		Return
		------
		->None				= No returns
		"""

		#Remove the yearly reports if we are not in January
		for _report in self.reports:
			if (_report["schedule"] == "yearly") and (month != 1):
				self.reports.remove(_report)

		#Subject of the mail changed to the user based subject
		if subject == "":
			_monthName = datetime(year=year, month=month, day=1).strftime("%B")
			_subjectString = f"eliona Benutzerreport vom {_monthName} {year}"
		else:
			_subjectString = subject

		#Create the content for the user based reports
		if content == "":
			_htmlContentString = f"Heliona {self.name}, <br><br> hier sind die gewünschten Reports aus der Reporting App.<br><br><ul>" 
					
			for _report in self.reports:	
				_htmlContentString = _htmlContentString + "<li>" + _report["name"] + "</li>"

			_htmlContentString = _htmlContentString + "</ul>"
		else:
			_htmlContentString = content

		#Pass to the parent class
		super().sendReport(year, month, createOnly, sendAsync, _subjectString, _htmlContentString)

class Report(BasicReport):
	"""
	Object to handle all reports for one user
	"""

	def __init__(self, name:str, tempFilePath:str, logLevel:int, testing:bool) -> None:
		"""
		Initialise the object
		"""

		super().__init__(name, tempFilePath, logLevel, testing)
		self.logger.debug("Init the report object")

	def configure(self, elionaConfig:dict, reportConfig:dict)->bool:

		#Add the reports to the report list
		self.reports = []
		self.reports.append(reportConfig)

		#Add the recipients to the list
		self.recipients = []
		for _recipient in reportConfig["receiver"]:
			self.recipients.append(_recipient["msgEndpoint"]) 

		return super().configure(elionaConfig=elionaConfig)