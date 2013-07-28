# Super Simple Server Stats Using Python

Collection of simple monitoring sccripts in Python. Why Python? Because.

## Requirements
1. *simplejson*, *rrdtool*, *twisted*, *crontab* Python packages
2. web server

## Installation
1. Copy the _src/*_ files to somewhere in your web directory
2. Add a crontab to cd into that directory and run the script **every** minute
3. Configure _config.json_

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
