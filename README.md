# Super Simple Server Stats Using Python


Collection of simple monitoring sccripts in Python.
Why Python? Because.

## Requirements
1. _simplejson_ and _rrdtool_ Python packages
2. web server

## Installation
1. Copy the _linux/*_ files to somewhere in your web directory
2. Change the path of _runall.sh_ to your web stats directory and add it to a crontab that runs **every** minute
3. Configure _config.json_

## Configuration
Why a JSON file? So I can reuse the info in _index.html_. Plus, I <3 JSON
The configuration file is a single JSON dictionary, with the following usage:

* **network_devices**
  * dictionary of device name to role, ie: "eth0": "web"

* **cpu**
  * **physical**: number of physical cpus, used to mark max line, especially usefull for hyperthreading
