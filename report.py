from sendBase import SendBase
from logging import Logger
from enums import Schedule, ReportState
from datetime import datetime

class Report(SendBase):
	"""
	Object to handle all reports for one user
	"""

	reportSchedule = Schedule.MONTHLY
	reportConfig = {}

	def __init__(self, name:str, logLevel:int) -> None:
		"""
		Initialise the object
		"""

		super().__init__(name, logLevel)        
		self.logger.debug("Init the report object")

	def configure(self, elionaConfig:dict, mailConfig:dict, reportConfig:dict={}, userConfig:dict={})->bool:

		self.reportConfig = reportConfig
		self.reports = []
		self.reports.append(self.reportConfig)

		return super().configure(elionaConfig=elionaConfig, mailConfig=mailConfig)
	
