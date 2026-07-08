#!/bin/bash
# Connect to srv VPS (72.60.210.157)
ssh -i ~/.ssh/id_srv_vps -o StrictHostKeyChecking=accept-new root@72.60.210.157 "$@"