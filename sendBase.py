
import os
import json
from mail import Mail
from spreadsheet import Spreadsheet
from threading import Thread
from enum import Enum
from logging import Logger
from datetime import datetime, timedelta, date, timezone
from enums import Schedule, ReportState
from typing import Tuple
import unicodedata
import re
import utils.logger as log

TEMP_ATTACHMENT_PATH = "./tmp_reports/send/"
LOGGER_LEVEL = log.LOG_LEVEL_DEBUG

class SendBase:
	"""
	Base class for the sender classes

	will contain all the basic methods and variables
	"""

	name=""

	logger = log.createLogger("BASE Send class", loglevel=LOGGER_LEVEL)
	state = ReportState.IDLE
	lastSend:datetime = datetime(1979, 1, 1)

	storePath = "./tmp_reports/"

	reportConfig = {}
	elionaConfig = {} #Eliona connection settings
	mailConfig = {}
	userConfig = {}

	messageData = None
	mailHandler = Mail()

	reports = [] #List of the reports to be send


	def __init__(self, name:str, logLevel:int) -> None:
		"""
		Init the class

		Param
		-----
		Return
		-----
		-> None
		"""

		self.name = name
		_fileName = self._slugify(name)

		self.logger = log.createLogger(applicationName=self.name, loglevel=logLevel)
		self.mailHandler = Mail(logLevel=logLevel)

		self.storePath = f"./tmp_reports/{_fileName}.json"
		self.readStorage()

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

		_reportWasSend = False

		try:
			if os.path.isfile(self.storePath):

				#Read the configuration file 
				with open(self.storePath, "r") as settingsFile:
					_storageJson = json.load(settingsFile)

					#Get the data from the storage 
					_dateTimeStrFormat = "%Y-%m-%d"
					self.lastSend = datetime.strptime(_storageJson["LastSend"], _dateTimeStrFormat)
					_reportWasSend = True

		except Exception as err:
			self.logger.warning(err)
			_reportWasSend = False		

		return _reportWasSend

	def configure(self, elionaConfig:dict, mailConfig:dict)->bool:
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
		self.mailConfig = mailConfig
		_configState = True

		return _configState

	def sendReport(self, year:int, month:int=0, sendAsync:bool=True) -> None:
		"""
		Create and send the report.

		Params
		------
		sendAsync:bool		= Set to True if you want to send it asynchronous
									to False if you want to send it now and wait for it to be send

		Return
		------
		->None				= No returns 											
		"""

		#get the start and stop date
		if month == 0:
			_schedule = Schedule.YEARLY
			month = 1
		else:
			_schedule = Schedule.MONTHLY

		#Get the start and stop time
		startStamp, stopStamp = self._getReportTimeSpan(schedule=_schedule, utcDelta=self.elionaConfig["dbTimeZone"], year=year, month=month)

		_thread = Thread(target=self._process, args=(startStamp, stopStamp))
		_thread.start()

		if not sendAsync:
			
			#if not send async wait till done
			_thread.join()

	def _process(self, startStamp:datetime, stopStamp:datetime):
		"""
		Thread to create and send the Report
		"""

		#Create the report
		for _report in self.reports:
			self._createReport(report=_report, startStamp=startStamp, stopStamp=stopStamp)

		#Send the mail
		_feedback = self._sendReport(self,mailConfig=self.mailConfig, reports=self.reports)

	def _createReport(self, report:dict, startStamp:datetime, stopStamp:datetime) -> bool:
		"""
		Call the reporter object with the requested settings and TimeSpan

		startStamp:datetime 	= Start time stamp of the report
		stopStamp:datetime		= End time of the report
		report:dict 			= Settings of the report as dictionary

		Return: bool -> Will return true if report was successfully created
		"""

		self.state = ReportState.CREATING
		_reportName = report["name"]

		self.logger.info(f"Call the reporting function with start {startStamp} and end timestamp {stopStamp}")

		_reportFileAndPath = TEMP_ATTACHMENT_PATH + report["reportPath"] + "_" + startStamp.date().isoformat() + "_" + stopStamp.date().isoformat() + "." + report["fileType"]


		#Call the reporting function
		_reporter = Spreadsheet()
		_reportSendFeedBack = _reporter.createReport(startDt=startStamp, endDt=stopStamp, connectionSettings=self.elionaConfig, reportSettings=report, reportFilePath=_reportFileAndPath)


		self.logger.info(f"Report: {_reportName} was send successfully created: {_reportSendFeedBack}")

		return _reportSendFeedBack

	def _sendReport(self, mailConfig:dict, reports:list):
		"""
		Send the created reports to the configured receivers
		
		Params
		-----
		report:dict = Report settings as a dictionary

		Return Values
		-----
		-> bool = Will return True if all emails where send. False if not.
		
		"""

		self.state = ReportState.SENDING
		_mailState = self.mailHandler.sendMail(connection=self.elionaConfig, sender=mailConfig["sender"], reports=reports)

		if _mailState:

			#Store the current time stamp that we have send the Data			
			self.lastSend = datetime.now()
			self.state = ReportState.IDLE
			
			#update the storage 
			with open(self.storePath, "r+") as jsonFile:
				_data = json.load(jsonFile)

				_data["LastSend"] = datetime.now().date() 

				jsonFile.seek(0)  # rewind
				json.dump(_data, jsonFile)
				jsonFile.truncate() # remove the "old" overlapping data
		else:
			self.state = ReportState.CANCELED
				
	def _getReportTimeSpan(self, schedule:Schedule, utcDelta:int, year:int, month:int=1) -> Tuple:
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

		_startTime = None
		_endTime = None
		_timeZone = timezone(timedelta(hours=utcDelta), "BER")


		if schedule == Schedule.YEARLY:

			_startTime = datetime(year=(year -1), month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=_timeZone)
			_endTime = datetime(year=(year), month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=_timeZone)

		elif schedule == Schedule.MONTHLY:

			if (month == 1):

				_startTime = datetime(year=(year - 1), month=12, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=_timeZone)
				_endTime = datetime(year=(year), month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=_timeZone)

			else:
				_startTime = datetime(year=(year), month=(month - 1), day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=_timeZone)
				_endTime = datetime(year=(year), month=(month), day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=_timeZone)

		elif schedule == Schedule.WEEKLY:

			pass

		elif schedule == Schedule.DAILY:

			pass

		else:
			self.logger.error("Could define time span for schedule: {schedule}")

		return (_startTime, _endTime)

	def _slugify(value, allow_unicode=False):
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