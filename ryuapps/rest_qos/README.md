### REST API for QoS Settings in [of12softswitch](https://github.com/itmo-infocom/of12softswitch) and [ofsoftswitch13](https://github.com/satrianachandra/ofsoftswitch13)

The module rest_qos_ss.py is used to provide REST API for QoS settings in of12softswitch and ofsoftswitch13.

#### Testing the module:

To run the module make sure that [ryu](https://github.com/osrg/ryu/tree/master/ryu) is already installed.

run the module located at ryuapps
```bash
# ryu-manager rest_qos_ss.py qos_simple_switch_12.py rest_conf_switch.py conf_switch_key.py
```

run mininet
```bash
# mn -v debug --topo single,2 --mac --switch user --controller remote
```

set switch address:
```bash
curl -X PUT -d '"/tmp/s1"' http://localhost:8080/v1.0/conf/switches/0000000000000001/unix_socket 
```

set qos settings:
```bash
curl -X POST -d '{"port_name": "1", "queues": [{"id": "1", "min_rate":"50"},{"id":"2", "min_rate": "50"}]}' \
 http://localhost:8080/qos/queue/0000000000000001
```
it is also possible to set the max rate, for example:
```bash
curl -X POST -d '{"port_name": "1", "queues": [{"id": "1", "min_rate":"50", "max_rate":"70"}]}' \
http://localhost:8080/qos/queue/0000000000000001
```

get qos settings:
```bash
curl -X GET http://localhost:8080/qos/queue/0000000000000001
```

| Endpoint | Description |
| ---- | --------------- |
| [PUT /v1.0/conf/switches/{SWITCH_ID}](https://github.com/satrianachandra/ryu/wiki/REST-API-for-Ecology-Framework#put-confswitchesswitch_idunix_socket) | Set switch address |
| [POST /qos/queue/{SWITCH_ID}](https://github.com/satrianachandra/ryu/wiki/REST-API-for-Ecology-Framework#post-qosqueueswitch_id) | Set QoS settings with data : port-name, queues: min-rate: |
| [GET /qos/queue/{SWITCH_ID}](https://github.com/satrianachandra/ryu/wiki/REST-API-for-Ecology-Framework#get-qosqueueswitch_id) | Get all queues settings in the switch |
| [DELETE /qos/queue/{SWITCH_ID}](https://github.com/satrianachandra/ryu/wiki/REST-API-for-Ecology-Framework#delete-qosqueueswitch_id) | Delete all queues settings in the switch |
| [DELETE /qos/queue/{SWITCH_ID}/{PORT}/{QUEUE_ID}](https://github.com/satrianachandra/ryu/wiki/REST-API-for-Ecology-Framework#delete-qosqueueswitch_id) | Delete a specific queue |
