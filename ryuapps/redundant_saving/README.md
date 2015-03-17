###Saving Energy in redundank links
This modules gives a sample on a network which uses both links in a redundant connection, or uses only 1 link when the utilization in the network is low.

<br>
#####Run mininet:
```bash
$ sudo python redundantlinks.py
```

<br>
#####Run the modules:
```bash
$ ryu-manager ofctl_rest.py host_tracker.py port_stats_reporter.py redundant_saving.py  
```
