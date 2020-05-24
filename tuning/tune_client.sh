#!/bin/bash -x

if [ "$1" != "" ]
then
    INTERFACE=$1
else
    INTERFACE="enp94s0f0"
fi

# nofile – The user file descriptor limit, set in the /etc/security/limits.conf file
# *             -   nofile         1048575

cp -f /auto/mtrswgwork/simonra/tools/nginx/conf/limits.conf /etc/security/limits.conf

# Tune system for networking throughput performance
#
set_irq_affinity.sh $INTERFACE
systemctl start tuned
tuned-adm profile throughput-performance
tuned-adm active
mlnx_tune -p HIGH_THROUGHPUT

# Tune system configuration for multiple concurrent connections
#
sysctl -w fs.file-max=13076284
sysctl -w kernel.shmmax=1000000000
sysctl -w vm.nr_hugepages=800
sysctl -w net.ipv4.tcp_fin_timeout=1
sysctl -w net.ipv4.tcp_tw_recycle=1
sysctl -w net.ipv4.tcp_tw_reuse=1
sysctl -w net.ipv4.ip_local_port_range="1024  65535"
sysctl -w net.ipv4.tcp_sack=0

# Enable HW offloads
#
ethtool -K $INTERFACE lro off # on by default
ethtool -K $INTERFACE gro on # on by default
ethtool -K $INTERFACE gso on # on by default
ethtool -K $INTERFACE tso on # on by default
ethtool --set-priv-flags $INTERFACE hw_lro on
ethtool --set-priv-flags $INTERFACE rx_striding_rq on

# Expand buffers
#
ethtool -G $INTERFACE tx 8192
ethtool -G $INTERFACE rx 8192
ifconfig $INTERFACE txqueuelen 16000
