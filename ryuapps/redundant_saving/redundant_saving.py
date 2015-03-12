from operator import attrgetter

from ryu.app import simple_switch_13
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub

#import urllib
#import urllib2
import requests
import json
import ast

class SimpleMonitor(simple_switch_13.SimpleSwitch13):

    def __init__(self, *args, **kwargs):
        super(SimpleMonitor, self).__init__(*args, **kwargs)
        self.datapaths = {}
        
        self.rx_bytes = [0,0]
        self.tx_bytes = [0,0]
        self.utilization= [0.0,0.0]
        self.ports = [1,1]

        self.monitoring_time = 5;
        
        #self.macsOfSwitch={}

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        if ev.state == MAIN_DISPATCHER:
          self.noBroadcastOnPort(2)
          self.installBalancingRoutes()

    def noBroadcastOnPort(self,port=2):
        eth_dsts=["ff:ff:ff:ff:ff:ff","33:33:00:00:00:16","33:33:00:00:00:02"]
        #eth_dsts=["ff:ff:ff:ff:ff:ff","33:33:00:00:00:00/ff::ff"]
        for i in range(0,len(eth_dsts)):
            url = 'http://localhost:8080/stats/flowentry/add'
            payload = {
                      "dpid": 1,
                      "table_id": 0,
                      "priority": 32768,
                      "match": {
                         "in_port": port,
                         "eth_dst": eth_dsts[i]
                            },
                      "actions":[
                            
                      ]
                    }
            response = requests.post(url,data=json.dumps(payload))
            self.logger.info(response.text)

            payload = {
                      "dpid": 2,
                      "table_id": 0,
                      "priority": 32768,
                      "match": {
                         "in_port": port,
                         "eth_dst": eth_dsts[i]
                            },
                      "actions":[
                      ]
                    }
            response = requests.post(url,data=json.dumps(payload))
            self.logger.info(response.text)

    def installBalancingRoutes(self,remove=False):
        out_port = 2
        if remove:
            out_port = 1
        url = 'http://localhost:8080/stats/flowentry/modify'
        payload = {
                  "dpid": 2,
                  "table_id": 0,
                  "priority": 32768,
                  "match": {
                     "eth_dst": "00:00:00:00:00:12",
                     "in_port":4
                        },
                  "actions":[ 
                     {"type":"OUTPUT",
                     "port": out_port}
                  ]
                }
        response = requests.post(url,data=json.dumps(payload))
        self.logger.info(response.text)

    
        url = 'http://localhost:8080/stats/flowentry/modify'
        payload = {
                  "dpid": 1,
                  "table_id": 0,
                  "priority": 32768,
                  "match": {
                     "eth_dst": "00:00:00:00:00:24",
                     "in_port":4
                        },
                  "actions":[
                     {"type":"OUTPUT",
                     "port": out_port}
                  ]
                }
        response = requests.post(url,data=json.dumps(payload))
        self.logger.info(response.text)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body

        #self.logger.info('datapath         port     '
        #                 'rx-pkts  rx-bytes rx-error '
        #                 'tx-pkts  tx-bytes tx-error')
        #self.logger.info('---------------- -------- '
        #                 '-------- -------- -------- '
        #                 '-------- -------- --------')
        for stat in sorted(body, key=attrgetter('port_no')):
            if (stat.port_no == 1):
                #self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d', 
                #                 ev.msg.datapath.id, stat.port_no,
                #                 stat.rx_packets, stat.rx_bytes, stat.rx_errors,
                #                 stat.tx_packets, stat.tx_bytes, stat.tx_errors)
                
                deltatraffic= (stat.rx_bytes - self.rx_bytes[stat.port_no-1]) + (stat.tx_bytes - self.tx_bytes[stat.port_no-1])
                self.utilization[stat.port_no - 1] = deltatraffic * 8 * 100 / (self.monitoring_time * 1*1000000.0) 
                self.logger.info('\nutilization port 1: %f', self.utilization[stat.port_no-1] )
                self.tx_bytes [stat.port_no - 1] = stat.tx_bytes
                self.rx_bytes [stat.port_no - 1] = stat.rx_bytes

                #if not(self.isPortUp('1',2)) and self.utilization[stat.port_1]+self.utilization[stat.port_2] > 90:
                if not(self.isPortUp('1',2)) and self.utilization[stat.port_no-1] > 70:
                    #enable port 2 on both switches
                    self.logger.info("enabling port 2 and load balancing")
                    self._modify_port('1',2,0,0xFFFFFFFF)
                    self._modify_port('2',2,0,0xFFFFFFFF)
                    self.installBalancingRoutes()
                elif self.isPortUp('1',2) and (self.utilization[stat.port_no-1] < 80):
                    self.logger.info("remove load balancing and disable port 2")
                    self.installBalancingRoutes(True)
                    self._modify_port('1',2,1<<0,0xFFFFFFFF)
                    self._modify_port('2',2,1<<0,0xFFFFFFFF)
            


    def _modify_port(self,dpid,port_no,config,mask):
        url = 'http://localhost:8080/stats/portdesc/modify'
        payload = {
          'dpid': dpid ,
          'port_no': port_no,
          'config': config,
          'mask' : mask
        }
        response = requests.post(url,data=json.dumps(payload))
        self.logger.info(response.text)
        self.logger.info(response)

    def isPortUp(self,dpid,port_no):
        url = "http://localhost:8080/stats/portdesc/"+dpid
        response = requests.get(url)
        if (response.text):
            portdescarrays = ast.literal_eval(response.text)[dpid]
            #print portdescarrays
            for entry in portdescarrays:
                if entry['port_no'] == port_no:
                    print entry['config']
                    if entry['config'] == 0:
                        return True
                    else:
                        return False
                    break

    


