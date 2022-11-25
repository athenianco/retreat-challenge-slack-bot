#!/bin/bash

set -oe pipefail

message=$1
slack_token=$2

docker run \
  --rm \
  -v $(pwd):/var/bot \
  -v ${message}:/etc/message.json \
  -e SLACK_TOKEN=${slack_token} \
  -it \
  --workdir=/var/bot \
  --entrypoint go \
  golang:1 \
  run cmd/publisher/main.go -f /etc/message.json
