from sendBase import SendBase
from logging import Logger
from enums import Schedule, ReportState
from datetime import datetime

class User(SendBase):
	"""
	Object to handle all reports for one user
	"""

	
	def __init__(self, name:str, logLevel:int) -> None:
		"""
		Initialise the object
		"""
		super().__init__(name, logLevel)        
		self.logger.debug("Init the user object")

	def configure(self, elionaConfig:dict, userConfig:dict={})->bool:

	
		#Add the reports to the list
		self.reports = userConfig["reports"]

		#Add the user to the list
		self.recipients = None
		self.blindCopyRecipients = []
		self.blindCopyRecipients.append(userConfig["msgEndpoint"])

		return super().configure(elionaConfig=elionaConfig)