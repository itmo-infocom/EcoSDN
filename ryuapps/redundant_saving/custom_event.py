from ryu.controller import ofp_event, event

class NewHostEvent(event.EventBase):
    def __init__(self, macAddr,dpid,port,hosts):
        super(NewHostEvent, self).__init__()
        self.macAddr = macAddr
        self.dpid = dpid
        self.port = port
        self.hosts = hosts