#!/bin/bash
cd /srv/http/stats
./cpu.py &
./network.py &
./ram.py &