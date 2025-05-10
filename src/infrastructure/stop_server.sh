#!/bin/bash

nohup_id=$(pgrep -f "node server.js")
if [ -n "$nohup_id" ]; then
  echo "killing existing server instance"
  sudo kill -9 $nohup_id
fi
