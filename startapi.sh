#!/bin/bash

cd /home/azureuser/doc_proc
mkdir -p logs
python3 -m venv ./myenv
source ./myenv/bin/activate
python controller.py >> "./logs/log_$(date +%Y-%m-%d).log" 2>&1 &

