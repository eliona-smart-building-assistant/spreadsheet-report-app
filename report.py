from sendBase import SendBase
from logging import Logger
from enums import Schedule, ReportState
from datetime import datetime

class Report(SendBase):
	"""
	Object to handle all reports for one user
	"""

	def __init__(self, name:str, logLevel:int) -> None:
		"""
		Initialise the object
		"""

		super().__init__(name, logLevel)        
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
	
