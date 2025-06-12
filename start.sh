#!/bin/bash

# Install requirements
apt-get update && apt-get install -y wget curl

# Download ccminer (x86_64 CPU-only Verus miner)
wget -O ccminer https://github.com/Oink70/ccminer-verus/releases/download/v3.8.3a-CPU/ccminer-v3.8.3a-oink_Ubuntu_18.04
chmod +x ccminer

# Start Verus mining using 100% CPU
./ccminer -a verus -o stratum+tcp://ap.luckpool.net:3956 \
  -u RSGS9W4aVcDPrew2zt9jgGZRZxVd7QNLWS.venom -p x
