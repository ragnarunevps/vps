#!/bin/bash

tmate -S /tmp/tmate.sock new-session -d
tmate -S /tmp/tmate.sock wait tmate-ready
tmate -S /tmp/tmate.sock display -p '#{tmate_ssh}'
tmate -S /tmp/tmate.sock display -p '#{tmate_web}'

while true; do echo -e "HTTP/1.1 200 OK\n\nworking" | nc -l -p 10000 -q 1; done
