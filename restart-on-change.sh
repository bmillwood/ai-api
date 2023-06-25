#!/usr/bin/env bash
set -o errexit -o nounset -o pipefail
set -x
trap 'kill -INT $(jobs -p)' INT
while sleep 1
do
  inotifywait -e modify main.py &
  ./main.py &
  wait %inotifywait
  kill %./main.py || true
done
