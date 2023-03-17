#!/usr/bin/env bash

#sudo ps -ef | grep monitor_stg | awk '{print $2}' | xargs kill
#
#sleep 2s

nohup ~/anaconda3/envs/lbk-tornado/bin/python ./monitor_stg.py  >/dev/null 2>&1 &
