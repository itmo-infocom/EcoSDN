###Adaptive Link Rate 
(still in development)
This modules lower down the rate of the port's bandwidth when the utilization is low, to save energy.
This is achieved by inserting qos rules with the destination of the host connected to the port.

<br>
Run mininet:
```bash
$ sudo python adaptive_link_rate/4h1sw.py 
```
<br>
To run the module:
```bash
$ sudo ryu-manager rest_qos/rest_conf_switch.py redundant_saving/ofctl_rest.py redundant_saving/port_stats_reporter.py  rest_qos/rest_qos_ss.py redundant_saving/host_tracker.py adaptive_link_rate/adaptive_link_rate.py
```
