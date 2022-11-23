from sendBase import SendBase
from logging import Logger
from enums import Schedule, ReportState
from datetime import datetime

class User(SendBase):
	"""
	Object to handle all reports for one user
	"""

	userMail = ""
	userConfig = {}
	
	def __init__(self, name:str, logLevel:int) -> None:
		"""
		Initialise the object
		"""
		super().__init__(name, logLevel)        
		self.logger.debug("Init the user object")

	def configure(self, elionaConfig:dict, mailConfig:dict, userConfig:dict={})->bool:

	
		#Object specific configuration
		self.userConfig = userConfig 
		self.reports.append(self.userConfig["reports"])

		return super().configure(elionaConfig, mailConfig)