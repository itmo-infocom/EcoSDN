from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub



class PortStatsReporter(app_manager.RyuApp):
	def __init__(self, *args, **kwargs):
		super(PortStatsReporter, self).__init__(*args, **kwargs)
		self.datapaths = {}

		self.monitor_thread = hub.spawn(self._monitor)
		self.monitoring_time = 5;



	@set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
	def _state_change_handler(self, ev):
		datapath = ev.datapath
        
		if ev.state == MAIN_DISPATCHER:
			if not datapath.id in self.datapaths:
			    self.logger.debug('register datapath: %016x', datapath.id)
			    self.datapaths[datapath.id] = datapath
			    #self.getMacsOfSwitch()
			    #self.routeLoadBalance('10.0.0.1')
			    #print self.mac_to_port
			    self.noBroadcastOnPort(2)
			    self.installBalancingRoutes()

		elif ev.state == DEAD_DISPATCHER:
		    if datapath.id in self.datapaths:
		        self.logger.debug('unregister datapath: %016x', datapath.id)
		        del self.datapaths[datapath.id]

	def _monitor(self):
	    while True:
	        for dp in self.datapaths.values():
	            if dp.id == 1:
	                self._request_stats(dp)
	        hub.sleep(self.monitoring_time)

	def _request_stats(self, datapath):
	    self.logger.debug('send stats request: %016x', datapath.id)
	    ofproto = datapath.ofproto
	    parser = datapath.ofproto_parser

	    #request port stats
	    req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
	    datapath.send_msg(req)



