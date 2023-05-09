from enum import Enum

class ReportState(Enum):
	"""
	Mail state definition
	"""
	IDLE = 0

	CREATING = 1
	SENDING = 30

	SEND_SUCCESSFULLY = 50
	CANCELED  = 100
	
	UNKNOWN = 500


class Schedule(Enum):
	"""
	Schedule types
	"""
	
	YEARLY = 0,
	MONTHLY = 1,
	WEEKLY = 2,
	DAILY = 3
