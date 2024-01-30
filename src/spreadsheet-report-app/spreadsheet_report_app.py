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



LOGGER_NAME = "Scheduler"
SLEEP_TILL_NEXT_REQUEST = 3600


DEFAULT_SETTINGS_PATH = "./storage/config/config.json"
DEFAULT_OUTPUT_PATH = "./storage/debug/"

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

	loggerLevel = log.LOG_LEVEL_DEBUG
	logger = log.createLogger(applicationName=LOGGER_NAME, loglevel=log.LOG_LEVEL_INFO)

	settings = {}
	settingsPath = ""
	sendTmpPath = ""
	storagePath = ""
	testing = True	
	timeTable = []
	timeIndex = 0
	users:dict[str, User] = {}
	reports:dict[str, Report] = {}

	def __init__(self, settingsPath:str, storagePath:str, testingEnable:bool, loggingLevel:str) -> None:
		"""
		Initialize the class
		"""
		# Init the logger
		if loggingLevel  == "DEBUG":
			self.loggerLevel = log.LOG_LEVEL_DEBUG
		elif loggingLevel  == "ERROR":
			self.loggerLevel = log.LOG_LEVEL_ERROR
		elif loggingLevel  == "WARNING":
			self.loggerLevel = log.LOG_LEVEL_WARNING
		elif loggingLevel  == "INFO":
			self.loggerLevel = log.LOG_LEVEL_INFO

		self.logger.setLevel(self.loggerLevel)

		self.logger.info("--------Init--------")

		# Set the settings path
		self.settingsPath = settingsPath

		self.storagePath = storagePath
		self.sendTmpPath = storagePath + "send/"
		self._dirHandling(path=self.sendTmpPath)

		#Initially delete the temp files after start up. 
		self._deleteOldTempFiles(path=self.sendTmpPath, force=True)

		self.testing = testingEnable
		if self.testing:
		
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

		self.logger.info("--------run--------")

		#Loop constantly through the settings
		while True:

			#Reset temp variables
			_storeNewData = False

			#Read the Settings file and validate it
			self.logger.info("--------read the settings--------")
			self.settings, _settingsAreValid = self._readSettings(self.settingsPath, self.SETTINGS_SCHEME)

			#If Settings are valid we will read them and perform the actions
			if _settingsAreValid:

				#Check if the report based reports are available
				if "reports" in self.settings:

					#Get through all the reports
					for _report in self.settings["reports"]:
						
						_reportName = _report["name"]

						if not(_reportName in self.reports):
							#Create the report object if not already created
							self.reports[_reportName] = Report(name=_reportName, tempFilePath=self.sendTmpPath, logLevel=self.loggerLevel, testing=self.testing)

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
							self.users[_userName] = User(name=_userName, tempFilePath=self.sendTmpPath, logLevel=self.loggerLevel, testing=self.testing)

						_userObj = self.users[_userName]

						#Only update the configuration if we are in idle					
						if _userObj.state == ReportState.IDLE:

							_userObj.configure(elionaConfig=self.settings["eliona_handler"], userConfig=_user, reportConfig=self.settings["reportConfig"])

							_now = self._now()
							_reportWasSend = _userObj.wasReportSend(_now)
							
							self.logger.debug(f"Reports  for user: {_userName} was already send : {_reportWasSend}")
							if not _reportWasSend:
								_userObj.sendReport(year=_now.year, month=_now.month, sendAsync=False)

			else:

				self.logger.error("Skipped the Create report process due to errors in the settings")

			#Check for files to delete
			self._deleteOldTempFiles(path=self.sendTmpPath)


			self.logger.debug(f"Sleep for {SLEEP_TILL_NEXT_REQUEST} seconds")
			time.sleep(SLEEP_TILL_NEXT_REQUEST)

	def _readSettings(self, settingsPath : str, settingsScheme:dict) -> Tuple[dict, bool]:
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


			#Get the environments variables if the values are not available or empty
			settingsJson["eliona_handler"]["host"] = settingsJson["eliona_handler"].get("host", os.environ.get("HOST_DOMAIN")) 
			settingsJson["eliona_handler"]["api"] = settingsJson["eliona_handler"].get("api", os.environ.get("API_ENDPOINT"))
			settingsJson["eliona_handler"]["apiKey"] = settingsJson["eliona_handler"].get("apiKey", os.environ.get("API_TOKEN"))
			settingsJson["eliona_handler"]["dbTimeZone"] = settingsJson["eliona_handler"].get("dbTimeZone", os.environ.get("TZ"))
			settingsJson["eliona_handler"]["sslVerify"] = settingsJson["eliona_handler"].get("sslVerify", json.loads(os.environ.get("SSL_VERIFY", "false").lower()))	#Take the way with json to convert the data to boolean

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

	def _deleteOldTempFiles(self, path:str, force:bool=False):
		"""
		Delete the old Template files by a given path

		Param
		----
		path:str 	= Path of the files to be deleted.
		force:bool	= True = Force to delete the files. Without considering the timestamp // False/None = Only delete the files if pld enough
		"""

		current_time = datetime.now()
		
		#Get all files
		for file in os.listdir(path):

			file_path = ""
			try:
				file_path = os.path.join(path, file)

				if file_path.lower().endswith(".json"):
					# Do not delete the configuration files
					pass

				elif os.path.isfile(file_path):

					#Check if file is older then one year
					if os.path.getctime(file_path) < current_time.timestamp() - (4 * (60 * 60)): #365 * 24 * 60 * 60
						
						#Remove the file
						os.remove(file_path)

					elif force:
						#Remove the file if it is been forced
						os.remove(file_path)
				elif os.path.isdir(file_path):
					self._deleteOldTempFiles(file_path, False)


			except Exception as err:

				self.logger.exception(f"Failed to delete file: {file_path}" + str(err) + "\n" + traceback.format_exc())

	def _singleExport(self, reportDate:str, reportName:str="", userName:str=""):
		"""
		Create an report for a single timestamp by user or report

		Params
		-----
		reportDate:str			Date of the report
		reportName:str			[Optional] Report name
		userName:str			[Optional] User name

		Return
		-----
		- No return Value
		"""

		#Read the settings file
		_settingsJson = {}
		if os.path.isfile(self.settingsPath):

			#Read the configuration file 
			with open(self.settingsPath, "r") as settingsFile:
				_settingsJson = json.load(settingsFile)

		#Set the Output path
		_outputPath = self.storagePath +"manual_created/"


		#Get the reports
		if userName != None:

			#Get the requested user			
			for _user in _settingsJson["users"]:

				if userName == _user["name"]: 				

					_userObj = User(name=userName, tempFilePath=_outputPath, logLevel=self.loggerLevel, testing=self.testing)
					_userObj.configure(elionaConfig=_settingsJson["eliona_handler"], userConfig=_user)
					_userObj.sendReport(year=reportDate.year, month=reportDate.month, createOnly=True, sendAsync=False)


		elif reportName != None:

			#Get the requested report
			for _report in self.settings["reports"]:
				
				if reportName == _report["name"]:

					_reportObj = Report(name=reportName, tempFilePath=_outputPath, logLevel=self.loggerLevel, testing=self.testing)
					_reportObj.configure(elionaConfig=self.settings["eliona_handler"], reportConfig=_report)
					_reportObj.sendReport(year=reportDate.year, month=reportDate.month, createOnly=True, sendAsync=False)

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
	_argumentParser.add_argument("-m", "--mode", type=str, required=False, help="Operation mode. possible values 'single' or 'runtime'")
	_argumentParser.add_argument("-c", "--config", type=str, required=False, help="Path to the used configuration file. For Example: \"./config/config.json\"")
	_argumentParser.add_argument("-s", "--storage", type=str, required=False, help="Storage file path")
	_argumentParser.add_argument("-l", "--logging", type=str, required=False, help="Logging mode. Possible values: 'DEBUG', 'INFO', 'ERROR', 'WARNING'")
	_argumentParser.add_argument("-t", "--testing", type=str, required=False, help="'Runtime Mode only': True: will enable the Testing with a given timetable under STORAGE_PATH/testing/timetable.txt")
	_argumentParser.add_argument("-r", "--report", type=str, required=False, help="'Single Mode only': Report name that's requested. Name can be read from config.json file.")
	_argumentParser.add_argument("-u", "--user", type=str, required=False, help="'Single Mode only': User name that's requested. Name can be read from config.json file.")
	_argumentParser.add_argument("-d", "--date", type=str, required=False, help="'Single Mode only': Date in the format: dd.mm.yyyy")
	_args = _argumentParser.parse_args()


	# No arguments received. We will use the .env file	
	if len(sys.argv) <= 1:

		_envDict = {} #Create the environment dict with all params

		mainApp = Spreadsheet_report_app(settingsPath=DEFAULT_SETTINGS_PATH, storagePath=DEFAULT_OUTPUT_PATH, testingEnable=False, loggingLevel="DEBUG")
		mainApp.run(sys.argv)

	else:
		_argDict = {}

		#Try to get the arguments
		try:

			_argDict["mode"] = _args.mode.strip()
			
			if _args.config:
				_argDict["config"] = _args.config
			else:
				_argDict["config"] = os.environ.get("SETTINGS_PATH") 

			if _args.storage:
				_argDict["storage"] = _args.storage
			else:
				_argDict["storage"] = os.environ.get("STORAGE_PATH")

			if _args.testing:
				_argDict["testing"] = json.loads(_args.testing.lower())
			else:
				_argDict["testing"] = json.loads(os.environ.get("TESTING_ENABLED", "false").lower()) 

			if _args.logging:
				_argDict["logging"] = _args.logging		
			else:
				_argDict["logging"] = os.environ.get("LOG_LEVEL")


			# Get the single specific params 
			if _argDict["mode"] == "single":
				_argDict["date"] = datetime.strptime(_args.date, "%d.%m.%Y").date()
				_argDict["user"] = _args.user
				_argDict["report"] = _args.report
				_argDict["testing"] = False

		except Exception as err:
			print("Error occurred reading the arguments. Enter -h or --help to get a help for the arguments.")
			print(str(err))
			exit()


		# Create the object wit al required information
		mainApp = Spreadsheet_report_app(	settingsPath=_argDict.get("config"), 
				   							storagePath=_argDict.get("storage"), 
											testingEnable=_argDict.get("testing"), 
											loggingLevel=_argDict.get("logging"))

		if _argDict["mode"] == "runtime":
			mainApp.run(_args)
		elif _argDict["mode"] == "single":
			mainApp._singleExport(_args)
