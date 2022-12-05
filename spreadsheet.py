import json
import pandas as pd
import shutil
import utils.logger as log
from datetime import datetime, timedelta

from eliona_modules.api.core.eliona_core import ElionaApiHandler, ConStat

LOGGER_NAME = "Spreadsheet"
LOGGER_LEVEL = log.LOG_LEVEL_DEBUG

class Spreadsheet:

	logger = log.createLogger(LOGGER_NAME, loglevel=LOGGER_LEVEL)

	def __init__(self, logLevel:int=log.LOG_LEVEL_DEBUG) -> None:
		"""
		Initialize the class
		"""

		self.reportFilePath = ""
		#self.logger = log.createLogger(applicationName=LOGGER_NAME, loglevel=logLevel)

	def createReport(self, startDt:datetime, endDt:datetime, connectionSettings:dict, reportSettings:dict, reportFilePath:str) -> bool:
		"""
		Create the requested report

		Params
		------ 
		startDt:datetime			= Start time of the Report
		endDt:datetime 				= End Time of teh Report => Will include the given end time by the data point as last entry
		connectionSettings:dict 	= COnnection settings for the eliona handler
		reportSettings:dict			= Settings for the to configured report

		Return
		----
		bool -> Will return True if report was successfully created. // False if a error occurred

		"""

		self.reportFilePath = reportFilePath

		#set the local variables
		_reportCreatedSuccessfully = False

		self.logger.info("--------connect--------")
		self.logger.debug("Host: " + str(connectionSettings["host"]))

		#Connect to the eliona instance
		eliona = ElionaApiHandler(settings=connectionSettings, logger=LOGGER_NAME)
		eliona.check_connection() 

		#Check if the connection is established
		if eliona.connection == ConStat.CONNECTED:
				
			self.logger.info("--------Create Table--------")
			#Call the report creator
			if (reportSettings["type"] == "DataListSequential") or (reportSettings["type"] == "DataListParallel"):
				_reportCreatedSuccessfully = self.__createDataListReport( eliona=eliona, settings=reportSettings, startDateTime=startDt, endDateTime=endDt)
			elif reportSettings["type"] == "DataEntry":
				_reportCreatedSuccessfully = self.__createDataEntryReport(eliona=eliona, settings=reportSettings, startDateTime=startDt, endDateTime=endDt)
			
		else:
			self.logger.info("Connection not possible. Will try again.")

		return _reportCreatedSuccessfully


	def __createDataEntryReport(self, eliona:ElionaApiHandler, settings:dict, startDateTime:datetime, endDateTime:datetime) -> bool:
		"""
		Create the table report from the given template

		settings:dict = Settings dictionary 
		"""
		_reportCreated = False

		#Only copy the template if needed 
		if settings["fromTemplate"]:
			shutil.copyfile(src=settings["templateFile"], dst=self.reportFilePath)

		#Read the template 
		_dataTable = self.__readTableTemplate(settings=settings)

		for _rowIndex, _row in _dataTable.iterrows(): #iterate over rows
			for _columnIndex, _value in _row.items():

				#Search for json config
				#{"assetId":"xxx", "attribute":"yyy"}
				if type(_value) == str:

					try:
						_config = json.loads(_value)
					except:
						_config = {}
						#self.logger.exception("Config could not be loaded from cell.")

					if ("assetId" in _config) and ("attribute" in _config):

						_endTimeOffset = timedelta(seconds=1)

						#self.logger.debug("Table config found: " + str(_config))
						_data, _correctTimestamps = self.__getAggregatedDataList(	eliona=eliona, 
																					assetId=int(_config["assetId"]), 
																					attribute=str(_config["attribute"]), 
																					startDateTime=startDateTime, 
																					endDateTime=endDateTime +_endTimeOffset,
																					raster=_config["raster"],
																					mode=_config["mode"])

						self.logger.debug(_data)

						#Try to get the Data
						if endDateTime in _data:
							_dataTable.at[_rowIndex, _columnIndex] = _data[endDateTime]

		#Write the Data to the 
		if _correctTimestamps:
			_reportCreated = self.__writeDataToFile(data=_dataTable, settings=settings)

		return _reportCreated

	def __createDataListReport(self, eliona:ElionaApiHandler, settings:dict, startDateTime:datetime, endDateTime:datetime):
		"""
		Create the table report from the given template

		eliona:ElionaApiHandler = Eliona handler
		settings:dict = Settings dictionary 
		"""

		#Init the data
		_timeStampColumnName = ""
		_timeStampFormat = ""
		_reportCreated = False
		_correctTimestamps = False

		#Only copy the template if needed 
		if settings["fromTemplate"]:
			shutil.copyfile(src=settings["templateFile"], dst=self.reportFilePath)

		#Read the template 
		_dataTable = self.__readTableTemplate(settings=settings)

		#Read the configuration from the template
		_configDict = {}
		for _columnName in _dataTable.columns.values:

			_firstRow = int(settings["firstRow"])
			_cellData = _dataTable.at[_firstRow, _columnName]

			if type(_dataTable.at[_firstRow, _columnName]) == str:
				_config = json.loads(_cellData)
				_configDict[_columnName] = _config

		
		#Search for the time stamp configuration
		for _columnName in _configDict:

			if "timeStamp" in _configDict[_columnName]:
				
				_timeStampColumnName = _columnName #Save the timestamp key
				_timeStampFormat = _configDict[_columnName]["timeStamp"]

				_raster = str(_configDict[_columnName]["raster"])

				#Get the time tick 
				if _raster.startswith("H"):

					timeTick = timedelta(hours=int(_raster.removeprefix("H")))	

				elif _raster.startswith("M"):

					timeTick = timedelta(minutes=int(_raster.removeprefix("M")))	

				elif _raster.startswith("S"):

					timeTick = timedelta(seconds=int(_raster.removeprefix("S")))	
				else:
					self.logger.error("No valid time span found")
					exit()
				
				#Set the time column
				_writeTimeRow = True
				_row = _firstRow
				_count = 0
				while _writeTimeRow:
					 
					_dataTable.at[_row, _columnName] = (startDateTime + (_count * timeTick))
					_row = _row + 1
					_count = _count + 1

					if startDateTime + (_count * timeTick) > endDateTime:
						_writeTimeRow = False


			elif (("assetId" in _configDict[_columnName])  
					and ("attribute" in _configDict[_columnName]) 
					and ("mode" in _configDict[_columnName])):
				
				#self.logger.debug("Table config found: " + str(_config))
				_data, _correctTimestamps = self.__getAggregatedDataList(	eliona=eliona, 
																			assetId=int(_configDict[_columnName]["assetId"]), 
																			attribute=str(_configDict[_columnName]["attribute"]), 
																			startDateTime=startDateTime, 
																			endDateTime=endDateTime,
																			raster=_raster,
																			mode=_configDict[_columnName]["mode"])

				self.logger.debug(_data)

				for _rowIndex, _row in _dataTable.iterrows():
					
					#Search for the TimeStamp
					if _row[_timeStampColumnName] in _data:
						
						#We found the timestamp. Lets write it to the data table
						_dataTable.at[_rowIndex, _columnName] =_data[_dataTable.at[_rowIndex, _timeStampColumnName]]
					else:
						_dataTable.at[_rowIndex, _columnName] = "none"

			else:
				self.logger.error("No valid table configuration.")

		#Switch the timestamp to the correct format
		self.__formatTimeStampRow(data=_dataTable, timeStampKey=_timeStampColumnName, timeStampFormat=_timeStampFormat)

		#Write the data to file
		_reportCreated = self.__writeDataToFile(data=_dataTable, settings=settings)

		return _reportCreated

	def __formatTimeStampRow(self, data:pd.DataFrame, timeStampKey:str, timeStampFormat:str):
		"""
		Change the timestamp format 

		data:pd.DataFrame = dataset as pandas data frame
		timeStampKey:str = key of the timestamp column
		timeStampFormat:str = timestamp format to use
		"""

		self.logger.debug("Before timestamp change")
		self.logger.debug(data)

		#Change the date and time format like requested in the template
		for _rowIndex, _row in data.iterrows():		
			#_row[timeStampKey] = _row[timeStampKey].strftime(timeStampFormat)
			data.at[_rowIndex, timeStampKey] = data.at[_rowIndex, timeStampKey].strftime(timeStampFormat)


		self.logger.debug("After timestamp change:")
		self.logger.debug(data)

	def __writeDataToFile(self, data:pd.DataFrame, settings:dict)-> bool:
		"""
		Write the dataFrame to the requested file

		data:pd.DataFrame = Data to write to the table
		settings:dict = Settings with the path of the file

		->bool = Will return True if successful
		"""

		_fileWritten = False

		try:
			if (settings["fileType"] == "xlsx") or (settings["fileType"] == "xls"):

				with pd.ExcelWriter(path=(self.reportFilePath), mode="a", if_sheet_exists="overlay") as writer:
					data.to_excel(writer, sheet_name= settings["sheet"], index=False)

				# Write the file was successful
				_fileWritten = True

			elif (settings["fileType"] == "csv"):

				_mode = ""
				if settings["fromTemplate"]:
					_mode = "a"
				else:
					_mode = "w"
				
				data.to_csv(path_or_buf= (self.reportFilePath), mode=_mode, index=False, header=True, sep=settings["separator"])
				
				# Write the file was successful
				_fileWritten = True
			

		except:
			self.logger.exception("Could not write Data to File: " + self.reportFilePath)

		return _fileWritten

	def __getAggregatedDataList(self, eliona:ElionaApiHandler, assetId:int, attribute:str, startDateTime:datetime, 
								endDateTime:datetime, raster:str, mode:str) -> tuple[dict|None, bool]:
		"""
		Get an attribute value from the given time span with tick
		Will return an dictionary with time stamp as key

		Params
		------
		eliona:ElionaApiHandler	= eliona API Handler instance
		assetId:int = Asset ID to get the data from
		attribute:str = Attribute from the Asset to read the data from
		startDateTime:datetime = Start point from which we create an dictionary entry every time tick  
		endDateTime:datetime = End pint for the dictionary
		tick:timedelta = pipeline raster to search for.

		Return
		------
		-> (dict:{datetime, dataValue}|None, bool: True= keys are valid // False = at least one key timestamp is missing)	
		"""

		#Create the return value as a dictionary 
		_dataSet = {}
		_validKeys = True

		try:

			self.logger.info(	"get data from: assetId:" + str(assetId) + " attribute:" + attribute + " start date:" + 
							startDateTime.isoformat() + " end date:" + endDateTime.isoformat() )

				
			_retVal, part = eliona.get_data_aggregated(	asset_id=assetId, 
															from_date=startDateTime.isoformat(), 
															to_date=endDateTime.isoformat(), 
															data_subtype="input")

			
			# Dictionary will return True if not empty
			if _retVal:

				#Get the requested data and aquisition mode
				for _data in _retVal:

					#Logg the received data
					#self.logger.debug(_data)

					#write the info to the LOGGER
					if ((_data["asset_id"] == assetId)
						and (_data["attribute"] == attribute) 
						and (_data["raster"] == raster)
						and mode in _data ):


						_dataSet[_data["timestamp"]] = _data[mode]

						#self.logger.debug("Asset ID: " + str(assetId) + " // attribute: "+ str(attribute) 
						#			+ " // raster: " + str(raster) + " // mode: " + str(mode))
						self.logger.debug(	"Timestamp" + str(_data["timestamp"]) + " // AssetId:  " + 
								str(_data["asset_id"]) + " // Attribute: " + str(_data["attribute"]) + 
								" // Raster: " + str(_data["raster"]) + " // Value: " +str(_data[mode]))


				#Validate the Data
				_checkActive = False
				_currentTimeSpan = startDateTime
				_timeDelta = timedelta()
				_missedTimeStamps =  "AssetId: " + str(assetId) +  " // Attribute: " + attribute + " // Missed time stamps: "

				if raster.startswith("M"):
					_timeDelta = timedelta(minutes=int(raster.replace("M", "")))
					_checkActive = True

				elif raster.startswith("H"):
					_timeDelta = timedelta(hours=int(raster.replace("H", "")))
					_checkActive = True

				elif raster.startswith("S"):
					_timeDelta = timedelta(seconds=int(raster.replace("S", "")))
					_checkActive = True


				#Check the TimeStamp
				while _checkActive:

					#Check if we are in range
					if _currentTimeSpan > endDateTime:
						_checkActive = False
					
					#We are in range check if key exists
					elif not _currentTimeSpan in _dataSet:
						#Save the timestamps
						_missedTimeStamps = _missedTimeStamps + "\n	-" + str(_currentTimeSpan) 
						_validKeys = False

					#Cunt up the current time for the next round
					_currentTimeSpan = _currentTimeSpan + _timeDelta

				if not _validKeys:
					self.logger.error(_missedTimeStamps)

			# Reset valid keys if empty data was received
			else:
				_validKeys = False

		except:
			self.logger.exception("Exception getting aggregated data")
		
		#Return the values
		return (_dataSet, _validKeys)

	def __getTrendDataList(self, eliona:ElionaApiHandler, assetId:int, attribute:str, startDateTime:datetime, endDateTime:datetime, 
							tick:timedelta) -> dict|None:
		"""
		Get an attribute value from the given time span with tick
		Will return an dictionary with time stamp as key

		eliona:ElionaApiHandler	= eliona API Handler instance
		assetId:int = Asset ID to get the data from
		attribute:str = Attribute from the Asset to read the data from
		startDateTime:datetime = Start point from which we create an dictionary entry every time tick  
		endDateTime:datetime = End pint for the dictionary
		tick:timedelta = delta for each entry.

		-> dict:{datetime, dataValue}	
		"""

		#Create the return value as a dictionary 
		_retVal = {}


		try:

			#self.logger.debug("get data from: assetId:" + str(assetId) + " attribute:" + attribute + 
			# " start date:" + startDateTime.isoformat() + " end date:" + endDateTime.isoformat() + 
			# " tick:" + str(tick) )

			#get the trend data from the source
			_data, part = eliona.get_data_trends( 	asset_id=assetId, 
													from_date=startDateTime.isoformat(), 
													to_date=endDateTime.isoformat(), 
													data_subtype="input")

			_count = 0
			_timeA = startDateTime
			_timeB = self.startDateTime +  tick
			for dataEntry in _data:

				#Check for the attribute
				if attribute in dataEntry["data"]:			

					#Add entry if between time steps
					if (_timeA < dataEntry["timestamp"]) and (dataEntry["timestamp"] < _timeB):
						_retVal[_timeA] = dataEntry["data"][attribute]

						#_retVal[_timeA] = str(dataEntry["data"][attribute]).replace(".", ",")

						_timeA = _timeB
						_timeB = _timeB + tick

					#if we exceed the timespan try to find the last one
					elif (dataEntry["timestamp"] > _timeB) and not (_timeA in _retVal):

						#no entry found for the current value. In this case we will try to get an entry from the last step
						if (_timeA - tick)	>= startDateTime:
							if (_timeA - tick) in _retVal:
								_retVal[(_timeA)] = _retVal[(_timeA - tick)]


		except:
			self.logger.exception("Error ocurred during reading the trend data")
			

		#Return the values
		return _retVal

	def __readTableTemplate(self, settings:dict) -> pd.DataFrame | None:
		"""
		Read the template Data 

		settings:dict {	"path": "path of the template file",
						"sheet": "Sheet name if excel file is used",
						"type": "file type: csv, xls, xlsx"}
		returns an pandas dataFrame
		"""

		_template = None

		try:
	
			with open(settings["templateFile"], 'r') as tempfile: # OSError if file exists or is invalid

				#Read the file
				if settings["templateFile"].endswith(".csv"):

					_template = pd.read_csv(settings["templateFile"], sep=settings["separator"])

				elif settings["templateFile"].endswith(".xlsx") or settings["templateFile"].endswith(".xls"):

					_template = pd.read_excel(io=settings["templateFile"], sheet_name=settings["sheet"])
	
		except OSError:
			self.logger.exception("Template file could not be opened: " + settings["templateFile"])


		#Return the _template
		return _template


if __name__ == "__main__":
	"""
	Main entry point
	"""

	 #from_date="2022-07-01T00:00:00+02:00", to_date="2022-07-01T01:00:00+02:00"
	_start = datetime.fromisoformat("2022-10-02T00:00:00+02:00")
	_end = datetime.fromisoformat("2022-10-03T00:00:00+02:00")
	_settingsPath = "./tmp_reports/Cust_Config/config.json"

	#karlaKolumna = Spreadsheet()
	#karlaKolumna.createReport(_start, _end, _settingsPath)
	