from ryu.controller import ofp_event, event

class UtilizationEvent(event.EventBase):
	def __init__(self, utils):
		super(UtilizationEvent, self).__init__()
		self.utils = utils