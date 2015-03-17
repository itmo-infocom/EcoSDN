
1. setup queues with different rates:
queue 1: 10 M 
queue 2: 1 M 

2. read utilization on every port, if utilization on that port is less than 10%, then install flows matching to that mac dest to be outputted first
to the queue number 1 or 2 (not sure which one, goota read the paper)


