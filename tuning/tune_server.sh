#!/bin/bash -x
# See http://www.nginxer.com/records/optimization-of-linux-kernel-parameters-when-using-nginx/


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

# Enable memory HP
#
sysctl -w kernel.shmmax=1000000000
sysctl -w vm.nr_hugepages=800

# The system wide limit for file descriptors
#
sysctl -w fs.file-max=13076284

# Enable TIME-WAIT state sockets fast reclaim function; used to quickly
# reduce the number of TCP connections in the TIME-WAIT state.
# 1 means enabled; 0 means closed.
# However, it is important to note that this option
# is generally not recommended, because under the Network (Network Address Translation) network,
# a large number of TCP connection establishment errors will occur,
# causing website access failure.
#
sysctl -w net.ipv4.tcp_tw_recycle=1

# When the server has to cycle through a high volume of TCP connections,
# it can build up a large number of connections in TIME_WAIT state.
# TIME_WAIT means a connection is closed but the allocated
# resources are yet to be released. Setting this directive to 1
# will tell the kernel to try to recycle the allocation
# for a new connection when safe to do so.
# This is cheaper than setting up a new connection from scratch.
# When the server has to cycle through a high volume of TCP connections,
# it can build up a large number of connections in TIME_WAIT state.
#
sysctl -w net.ipv4.tcp_tw_reuse=1

# The minimum number of seconds that must elapse before
# a connection in TIME_WAIT state can be recycled.
# Lowering this value will mean allocations will be recycled faster.
#
sysctl -w net.ipv4.tcp_fin_timeout=1

# The start and end of the range of port values.
# Increase the Number of Available Ephemeral Ports
# If you’re seeing errors in your /var/log/syslog such as:
# “possible SYN flooding on port 80. Sending cookies”
# it might mean the system can’t find an available port for the pending connection.
# Increasing the capacity will help alleviate this symptom
#
sysctl -w net.ipv4.ip_local_port_range="1024  65535"

# The maximum number of connections that can be queued for acceptance by NGINX.
# The default is often very low and that’s usually acceptable because NGINX accepts
# connections very quickly, but it can be worth increasing it if your website
# experiences heavy traffic.
# If error messages in the kernel log indicate that the value is too small,
# increase it until the errors stop.
# Note: If you set this to a value greater than 512, change the backlog parameter to
# the NGINX listen directive to match.
# It an unsigned 16 bit integer so between 0 and 65535
#
sysctl -w net.core.somaxconn=65535

# The maximum number of packets that are allowed to be sent to the queue when each
# network interface receives packets at a faster rate than the kernel processes them.
#
sysctl -w net.core.netdev_max_backlog=262144

# The maximum number of connection requests logged that have not yet received client
# acknowledgment information. For systems with 128M memory, the default is 1024,
# and for small memory systems is 128.
#
sysctl -w net.ipv4.tcp_max_syn_backlog=262144

# The controls how many attempts will be done before a server-less port is released.
#
sysctl -w net.ipv4.tcp_orphan_retries=0

# The TCP Selective Acknowledgments
#
sysctl -w net.ipv4.tcp_sack=0

# Enable HW offloads
#
ethtool -K $INTERFACE lro on
ethtool -K $INTERFACE gro on
ethtool -K $INTERFACE gso on
ethtool -K $INTERFACE tso on
ethtool --set-priv-flags $INTERFACE hw_lro on
ethtool --set-priv-flags $INTERFACE rx_striding_rq on

# Expand buffers
#
ethtool -G $INTERFACE tx 8192
ethtool -G $INTERFACE rx 8192
ifconfig $INTERFACE txqueuelen 16000
