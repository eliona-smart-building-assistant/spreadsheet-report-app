from calendar import month
import os
import sys
import json
import logging
import time
from typing import Tuple
import jsonschema
from spreadsheetCreator import SpreadsheetCreator
from mail import Mail
from datetime import datetime, timedelta, date, timezone
import pytz

logging.basicConfig(filename="log.log", encoding="utf-8")
LOGGER_NAME = "Scheduler"
LOGGER = logging.getLogger(LOGGER_NAME)
HANDLER = logging.StreamHandler()
HANDLER.setLevel(logging.DEBUG)
LOGGER.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter(fmt="%(asctime)s: %(name)s: %(levelname)s: %(lineno)d: %(message)s", datefmt="%d-%m-%y %H:%M:%S")
HANDLER.setFormatter(FORMATTER)
LOGGER.addHandler(HANDLER)

class Spreadsheet_report_app:


	SETTINGS_SCHEME	= {
			"eliona_handler": {
				"host": {"type": "string"},
				"api": {"type": "string"},
				"projectId": {"type": "number"},
				"apiKey": {"type": "string"}
			},

			"mail": {
				"sender" : {"type", "string"},
				"template": {
					"path" : {"type", "string"},
					"MimeType" : {"type", "string"}
				}
			},

			"reports": [
				{
					"name": {"type": "string"},
					"schedule": {"type": "string"},
					"type": {"type": "string"},
					"templateFile": {"type": "string"},
					"sheet": {"type": "string"},
					"fileType": {"type": "string"},
					"mimeType": {"type": "string"},
					"separator":{"type": "string"},
					"firstRow": {"type": "string"},
					"fromTemplate": {"type": "boolean"},
					"reportPath": {"type": "string"},
					"receiver": [
						{
							"name": {"type": "string"},
							"msgType": {"type": "string"},
							"msgEndpoint": {"type": "string"}
						}
            		]
				}
			]
		}
	"""
	Scheme definition of the application settings
	"""

	PERSISTENT_STORAGE_SCHEME = {
			"reports": [
				{
					"name": {"type": "string"},
					"lastSend": {"type": "string"}
				}]}

	def __init__(self, settingsPath:str) -> None:
		"""
		Initialize the class
		
		"""
		#logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
		#self.logger = logging.getLogger(f'{LOGGER}.{__name__}')
		LOGGER.info("--------Init--------")

		self.settings = dict()
		self.settingsPath = settingsPath
		self.storagePath = "./state.json"
		self.mailHandler = Mail()
		
	def run(self, args) -> None:
		"""
		Main method 

		Params
		-------
		settingsPath: 

		Return values
		----
		-> None
		"""

		_reportLastSend = {}

		LOGGER.info("--------run--------")

		#Loop constantly through the settings
		while True:

			#Reset temp variables
			_storeNewData = False

			#Read the Settings file and validate it
			LOGGER.info("--------read the settings--------")
			self.settings, _settingsAreValid = self.__readJSonFile(self.settingsPath, self.SETTINGS_SCHEME)

			#Read the stored data file and validate it
			LOGGER.info("--------read the tempFIle--------")
			_reportLastSend, _storageValid = self.__readJSonFile(self.storagePath, self.PERSISTENT_STORAGE_SCHEME)

			#Remove the settings file if not valid
			if not _storageValid:
				if os.path.isfile(self.storagePath):
					os.remove(self.storagePath)
				_reportLastSend["reports"] = {}

			#If Settings are valid we will read them and perform the actions
			if _settingsAreValid:

				#Get through all the reports
				for _report in self.settings["reports"]:

					_sendReport = False
					_scheduleSetting = _report["schedule"]
					_reportName = _report["name"]

					if _storageValid:

						#Check if the report has been send once
						if _reportName in _reportLastSend["reports"]:

							#Get the data from the storage 
							dateTimeStrFormat = "%Y-%m-%d"
							_lastSendTimeStamp = datetime.strptime(_reportLastSend["reports"][_reportName], dateTimeStrFormat)

							#Check if the report needed to be send
							_sendReport = self.__checkIfReportNeedToBeSend(_reportName, _lastSendTimeStamp, _scheduleSetting)

						else:
							_sendReport = True
					else:
						_sendReport = True


					#Send the Data if needed
					if _sendReport:

						_reportCreated = self.__createReport(connection=self.settings["eliona_handler"], report=_report)

						# If report was created successfully we well try to send the data to the receivers 
						if _reportCreated:
							_storeNewData = self.__sendReport(connection=self.settings["eliona_handler"], mailSettings=self.settings["mail"],  report=_report)

						# Only save the timestamp if the file was written and send to the receivers
						#if _storeNewData:
						#	#Save the timestamp and store it after all reports are done
						#	_reportLastSend["reports"][_reportName] = datetime.now().date() 

			else:
				LOGGER.error("Skipped the Create report process due to errors in the settings")

			#If we send the Data we will save the current changes
			if _storeNewData:
				jsonString = json.dumps(_reportLastSend, default=str)
				jsonFile = open(self.storagePath, "w")
				jsonFile.write(jsonString)
				jsonFile.close()

			time.sleep(40)

	def __getReportTimeSpan(self, schedule:str, utcDelta:int) -> Tuple:
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


		if schedule == "yearly":

			_startTime = datetime(year=(date.today().year -1), month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=_timeZone)
			_endTime = datetime(year=(date.today().year), month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=_timeZone)

		elif schedule == "monthly":

			if (date.today().month == 1):

				_startTime = datetime(year=(date.today().year - 1), month=12, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=_timeZone)
				_endTime = datetime(year=(date.today().year), month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=_timeZone)

			else:
				_startTime = datetime(year=(date.today().year), month=(date.today().month - 1), day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=_timeZone)
				_endTime = datetime(year=(date.today().year), month=(date.today().month), day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=_timeZone)

		elif schedule == "weekly":

			pass

		elif schedule == "daily":

			pass

		else:
			LOGGER.error("Could define time span for schedule: {schedule}")

		return (_startTime, _endTime)

	def __getLastCalendarWeek(self, year):
		"""
		Get the last week of the given year.
		"""
		return datetime.date(year, 12, 28).isocalendar()[1]

	def __checkIfReportNeedToBeSend(self, reportName:str, lastSendDateTime :datetime, schedule: str) -> bool:
		"""
		Check if we need to send the report
		We will send reports only after 6

		"""

		_retVal = False

		#We will not send any report before 6 
		if (datetime.now().hour < 6):
			return False

		if schedule == "yearly":
			if (lastSendDateTime.year != datetime.now().date().year):
				_retVal = True
		elif schedule == "monthly":
			if (lastSendDateTime.month != datetime.now().date().month) \
				or (lastSendDateTime.year != datetime.now().date().year):
				_retVal = True
		elif schedule == "weekly":
			if (lastSendDateTime.isocalendar().week != datetime.now().isocalendar().week) \
				or (lastSendDateTime.month != datetime.now().date().month) \
				or (lastSendDateTime.year != datetime.now().date().year):
				_retVal = True
		elif schedule == "daily":
			if (lastSendDateTime.day != datetime.now().date().day)\
				or (lastSendDateTime.month != datetime.now().date().month) \
				or (lastSendDateTime.year != datetime.now().date().year):
				_retVal = True
		else:
			LOGGER.error("Could not send report: {reportName} do to invalid schedule")


		return _retVal

	def __createReport(self, connection:dict, report:dict) -> bool:
		"""
		Call the reporter object with the requested settings and TimeSpan

		connection:dict = Settings of the eliona connection as dictionary
		report:dict = Settings of the report as dictionary

		Return: bool -> Will return true if report was successfully created
		"""
		_reportName = report["name"]

		#Get the timestamp of the start and the end for the report
		_startTimeStamp, _endTimeStamp = self.__getReportTimeSpan(report["schedule"], connection["dbTimeZone"])


		LOGGER.info(f"Call the reporting function wit start {_startTimeStamp} and end timestamp {_endTimeStamp}")

		#Call the reporting function
		_reporter = SpreadsheetCreator()
		_reportSendFeedBack = _reporter.createReport(startDt=_startTimeStamp, endDt=_endTimeStamp, connectionSettings=connection, reportSettings=report)


		LOGGER.info(f"Report: {_reportName} was send successfully: {_reportSendFeedBack}")

		return _reportSendFeedBack

	def __sendReport(self, connection:dict, mailSettings:dict, report:dict) -> bool:
		"""
		Send the created reports to the configured receivers
		
		Params
		-----
		report:dict = Report settings as a dictionary

		Return Values
		-----
		-> bool = Will return True if all emails where send. False if not.

		"""

		_retVal = True

		#_mailHandler.sendMail()


		return _retVal

	def __readJSonFile(self, settingsPath : str, settingsScheme:dict) -> tuple[dict, bool]:
		"""
		# read the settings and store them in the class variables

		This method will read a json file to an dictionary

		- settingsPath : str = Settings source path as string
		"""

		settingsJson = {}
		_settingIsValid = False

		if os.path.isfile(settingsPath):

			#Read the configuration file 
			with open(settingsPath, "r") as settingsFile:
				settingsJson = json.load(settingsFile)

			#Check if validate
			_settingIsValid = self.__validateJson(settingsFile, settingsScheme)

			if _settingIsValid:
				LOGGER.debug(f"File: {settingsPath} read data's are valid.")			
			else:
				LOGGER.error(f"File: {settingsPath} read data's are invalid")

		return settingsJson, _settingIsValid
	
	def __validateJson(self, jsonData:dict, jsonScheme:dict) -> bool:
		"""
		Validate the json file.Will be checked with a given scheme
		WIll check if attributes with correct types are available

		Param
		-----
		jsonData:dict = Real Json data as an Dictionary
		jsonScheme:dict = Json scheme to verify the data as an dictionary

		Return
		-----
		bool -> True if valid // False if not valid
		"""
		_retVal = False

		try:
			jsonschema.validate(instance=jsonData, schema=jsonScheme)
			_retVal = True
		except jsonschema.exceptions.ValidationError as err:
			_retVal = False
		except jsonschema.exceptions.SchemaError as err:
			_retVal = False

		return _retVal

if __name__ == "__main__":
	"""
	Main entry point
	"""

	 #from_date="2022-07-01T00:00:00+02:00", to_date="2022-07-01T01:00:00+02:00"
	_settingsPath = "./tmp_reports/Cust_Config/config.json"
	

	mainApp = Spreadsheet_report_app( _settingsPath)
	mainApp.run(sys.argv)
	