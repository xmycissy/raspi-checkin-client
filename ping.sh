#!/bin/bash
PREFIX=192.168.123.
for i in `seq 1 254`
do
    echo "${PREFIX}$i"
    timeout 0.2 ping -c1 ${PREFIX}${i} > /dev/null 2>&1
done

arp -v | grep ether | awk '{print $1,$3}'
