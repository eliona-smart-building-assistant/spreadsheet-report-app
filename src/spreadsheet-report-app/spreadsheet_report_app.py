import argparse
import os
import traceback
import sys
import json
import time
from typing import Tuple
import jsonschema
from datetime import datetime
from enums import ReportState
from reporting import User, Report
import utils.logger as log


SETTINGS_PATH = "./tmp_reports/Cust_Config/config.json"
LOGGER_NAME = "Scheduler"
LOGGER_LEVEL = log.LOG_LEVEL_DEBUG
SLEEP_TILL_NEXT_REQUEST = 1
TESTING_ENABLED = True
TEMP_ATTACHMENT_PATH = "./tmp_reports/send/"

class Spreadsheet_report_app:

	SETTINGS_SCHEME	= {
			"eliona_handler": {
				"host": {"type": "string"},
				"api": {"type": "string"},
				"projectId": {"type": "number"},
				"apiKey": {"type": "string"}
			},

			"reports": [
				{
					"name": {"type": "string"},
					"schedule": {"type": "string"},
					"type": {"type": "string"},
					"templateFile": {"type": "string"},
					"sheet": {"type": "string"},
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

	logger = log.createLogger(applicationName=LOGGER_NAME, loglevel=LOGGER_LEVEL)
	settings = {}
	settingsPath = ""
	storagePath = "./state.json"
	testing = True	
	timeTable = []
	timeIndex = 0
	users:dict[str, User] = {}
	reports:dict[str, Report] = {}

	def __init__(self, settingsPath:str) -> None:
		"""
		Initialize the class
		"""
		#logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
		#self.logger = logging.getLogger(f'{self.logger}.{__name__}')
		self.logger.info("--------Init--------")

		self.settingsPath = settingsPath

		if TESTING_ENABLED:
		
			dateTimeStrFormat =  "%d-%m-%Y %H:%M:%S"
			
			#Initialize the timetable
			with open("./testing/timetable.txt") as fp:
				lines = fp.readlines()

				for line in lines:

					if line.strip() != "":
						self.timeTable.append(datetime.strptime(line.replace("\n", ""), dateTimeStrFormat))

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

		self.logger.info("--------run--------")



		#Loop constantly through the settings
		while True:

			#Reset temp variables
			_storeNewData = False

			#Read the Settings file and validate it
			self.logger.info("--------read the settings--------")
			self.settings, _settingsAreValid = self._readJSonFile(self.settingsPath, self.SETTINGS_SCHEME)

			#If Settings are valid we will read them and perform the actions
			if _settingsAreValid:

				#Check if the report based reports are available
				if "reports" in self.settings:

					#Get through all the reports
					for _report in self.settings["reports"]:
						
						_reportName = _report["name"]

						if not(_reportName in self.reports):
							#Create the report object if not already created
							self.reports[_reportName] = Report(name=_reportName, tempFilePath=TEMP_ATTACHMENT_PATH, logLevel=LOGGER_LEVEL)

						_reportObj = self.reports[_reportName]

						self.logger.debug(f"State of report {_reportName} : {self.reports[_reportName].state}")

						#Only update the configuration if we are in idle
						if self.reports[_reportName].state == ReportState.IDLE:
							
							self.reports[_reportName].configure(elionaConfig=self.settings["eliona_handler"], reportConfig=_report)

							_now = self._now()
							self.logger.debug(f"current Timestamp: {_now}")
							_reportWasSend = self.reports[_reportName].wasReportSend(_now)
							
							self.logger.debug(f"Report {_reportName} was already send : {_reportWasSend}")
							if not _reportWasSend:
								self.reports[_reportName].sendReport(year=_now.year, month=_now.month, sendAsync=False)


				#Check if user based reports are available
				if "users" in self.settings:

					#Get through all the users
					for _user in self.settings["users"]:

						_userName = _user["name"]

						if not(_userName in self.users):
							#Create the report object if not already created
							self.users[_userName] = User(name=_userName, tempFilePath=TEMP_ATTACHMENT_PATH, logLevel=LOGGER_LEVEL)

						_userObj = self.users[_userName]

						#Only update the configuration if we are in idle					
						if _userObj.state == ReportState.IDLE:

							_userObj.configure(elionaConfig=self.settings["eliona_handler"], userConfig=_user)

							_now = self._now()
							self.logger.debug(f"current Timestamp: {_now}")
							_reportWasSend = _userObj.wasReportSend(_now)
							
							self.logger.debug(f"Reports  for user: {_userName} was already send : {_reportWasSend}")
							if not _reportWasSend:
								_userObj.sendReport(year=_now.year, month=_now.month, sendAsync=False)

			else:

				self.logger.error("Skipped the Create report process due to errors in the settings")

			#Check for files to delete
			self._deleteOldTempFiles(path=TEMP_ATTACHMENT_PATH)


			self.logger.debug(f"Sleep for {SLEEP_TILL_NEXT_REQUEST} seconds")
			time.sleep(SLEEP_TILL_NEXT_REQUEST)

	def _readJSonFile(self, settingsPath : str, settingsScheme:dict) -> Tuple[dict, bool]:
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
			_settingIsValid = self._validateJson(settingsFile, settingsScheme)

			if _settingIsValid:
				self.logger.debug(f"File: {settingsPath} read data's are valid.")			
			else:
				self.logger.error(f"File: {settingsPath} read data's are invalid")

		return settingsJson, _settingIsValid
	
	def _validateJson(self, jsonData:dict, jsonScheme:dict) -> bool:
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

	def _now(self)->datetime:
		"""
		Returns the current timestamp

		Return
		------
		->dateTime 	= Will return the current datetime unless self.testing is active. There fore the return value is defined in a time table 
		"""

		if self.testing:
			_timeStamp = self._backToTheFuture()
			
			for _reportKey in self.reports:
				self.reports[_reportKey].testing = True
				self.reports[_reportKey].currentTestTime = _timeStamp

			for _userKey in self.users:
				self.users[_userKey].testing = True
				self.users[_userKey].currentTestTime = _timeStamp

			return _timeStamp
		else:
			return datetime.now()		

	def _backToTheFuture(self)->datetime:
		"""
		Will handle Timing for test purposes

		For each Tick will return an different Timestamp to handle past time reports

		Return
		------
		->dateTime 	= Will return the current datetime unless self.testing is active. There fore the return value is defined in a time table 

		"""

		if self.timeIndex >= len(self.timeTable):
			self.timeIndex = len(self.timeTable) -1
			
		_lastSendTimeStamp = self.timeTable[self.timeIndex]

		self.timeIndex += 1
		return _lastSendTimeStamp

	def _deleteOldTempFiles(self, path:str):
		"""
		Delete the old Template files by a given path

		Param
		----
		path:str 	= Path of the files to be deleted.

		"""

		current_time = datetime.now()
		
		#Get all files
		for file in os.listdir(path):

			try:
				file_path = os.path.join(path, file)

				#Check if file is older then one year
				if os.path.getctime(file_path) < current_time.timestamp() - (10 * 60): #365 * 24 * 60 * 60
					
					#Remove the file
					os.remove(file_path)

			except Exception as err:

				self.logger.exception(f"Failed to delete file: {file_path}" + str(err) + "\n" + traceback.format_exc())

	def _singleExport(self, arguments):

		#Try to get the arguments
		try:
			_reportName = arguments.report
			_userName = arguments.user
			_date = datetime.strptime(arguments.date, "%d.%m.%Y").date()
			_configPath = arguments.config
			_outputPath = arguments.output

		except Exception as err:
			print("Error occurred reading the arguments. Enter -h or --help to get a help for the arguments.")
			print(str(err))
			exit()


		#Set the config path
		if _configPath == None:
			_configPath = SETTINGS_PATH

		#Read the settings file
		_settingsJson = {}
		if os.path.isfile(_configPath):

			#Read the configuration file 
			with open(_configPath, "r") as settingsFile:
				_settingsJson = json.load(settingsFile)

		#Set the Output path
		if _outputPath == None:
			_outputPath = "./tmp_reports/manual_created/"


		#Get the reports
		if _userName != None:

			#Get the requested user			
			for _user in _settingsJson["users"]:

				if _userName == _user["name"]: 				

					_userObj = User(name=_userName, tempFilePath=_outputPath, logLevel=LOGGER_LEVEL)
					_userObj.configure(elionaConfig=_settingsJson["eliona_handler"], userConfig=_user)
					_userObj.sendReport(year=_date.year, month=_date.month, createOnly=True, sendAsync=False)


		elif _reportName != None:

			#Get the requested report
			for _report in self.settings["reports"]:
				
				if _reportName == _report["name"]:

					_reportObj = Report(name=_reportName, tempFilePath=TEMP_ATTACHMENT_PATH, logLevel=LOGGER_LEVEL)
					_reportObj.configure(elionaConfig=self.settings["eliona_handler"], reportConfig=_report)
					_reportObj.sendReport(year=_date.year, month=_date.month, createOnly=True, sendAsync=False)




if __name__ == "__main__":
	"""
	Main entry point

	Params
	-----
	args*
	startDate:datetime.fromisoformat	= Start time in Isoformat. For Example: "2022-10-02T00:00:00+02:00"
	endDate:datetime.fromisoformat		= End time in Isoformat. For Example: "2022-10-02T00:00:00+02:00"
	settingsPath 						= Path of the current Settings. Example: "./tmp_reports/Cust_Config/config.json"
	reportName							= Name of the requested report
	reportExportPath					= [Optional] Set the output path of the created report.

	"""
	#parse the arguments
	_argumentParser = argparse.ArgumentParser()
	_argumentParser.add_argument("-d", "--date", type=str, required=False, help="Date in the format: dd.mm.yyyy")
	_argumentParser.add_argument("-c", "--config", type=str, required=False, help="Path to the used configuration file. For Example: \"./config/config.json\"")
	_argumentParser.add_argument("-u", "--user", type=str, required=False, help="User name that's requested. Name can be read from config.json file.")
	_argumentParser.add_argument("-r", "--report", type=str, required=False, help="Report name that's requested. Name can be read from config.json file.")
	_argumentParser.add_argument("-o", "--output", type=str, required=False, help="Export file path. If empty will be stored under \"./temp/file_name\"")
	_args = _argumentParser.parse_args()

	if len(sys.argv) <= 1:
		mainApp = Spreadsheet_report_app( SETTINGS_PATH)
		mainApp.run(sys.argv)
	else:
		mainApp = Spreadsheet_report_app( SETTINGS_PATH)
		mainApp._singleExport(_args)
		
