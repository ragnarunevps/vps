#!/bin/bash

# Start tmate in background
tmate -S /tmp/tmate.sock new-session -d
tmate -S /tmp/tmate.sock wait tmate-ready
tmate -S /tmp/tmate.sock display -p '#{tmate_ssh}'
tmate -S /tmp/tmate.sock display -p '#{tmate_web}'

# Start fake web server on port 10000 (any unused port)
while true; do echo -e "HTTP/1.1 200 OK\n\nWorking" | nc -l -p 10000 -q 1; done
