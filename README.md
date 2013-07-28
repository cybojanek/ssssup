# Super Simple Server Stats Using Python and RRDTool

Collection of simple monitoring sccripts in Python. Why Python? Because. Demo at http://cybojanek.net:8080

## Requirements
1. *simplejson*, *rrdtool*, *twisted*, *crontab* Python packages
2. web server

## Installation
1. Configure _config.json_
2. Launch with twistd:

```
twistd -y server.py
```

## Configuration
Why a JSON file? So I can reuse the info in _index.html_.

The configuration file is a single JSON dictionary, with the following usage:

* **network_devices**
  * dictionary of device name to role, ie: "eth0": "web"

* **cpu**
  * **physical**: number of physical cpus, used to mark max line, especially usefull for hyperthreading

* **hdd**
  * dictionary of device name to role, ie: "sda": "root"

* **swap**
  * Set to "true" / "false" for whether to record swap usage

* **nginx**
  * Set to a non empty url that points to the nginx stat module
  * You also need to enable the nginx stats module:

```
location /nginx_status {
    stub_status on;
    access_log   off;
}
```
