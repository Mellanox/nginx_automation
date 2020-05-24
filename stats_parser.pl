#!/bin/env perl

if ($#ARGV < 0) {
    print "usage: $0 <dbname>\n";
    exit 1;
}

$uid = 0;
clear_all_vars();

#
# Database initialization
#

$sqlite = 'sqlite3';
$dbname = $ARGV[0];
if (-s $dbname) {
    database_read_state();
} else {
    database_init();
}

while (<STDIN>) {
    $line = $_;
    chomp $line;
    
    if ($line =~ /^=+$/) {
        if ($fd != 0) {
            store_stats();
        }
        clear_all_vars();
    }
    elsif ($line =~ /Rx and Tx where not active/) {
        # ignore this record
        $fd = 0;
    }
    elsif ($line =~ /Fd=\[(\d+)\]/) {
        $fd = $1;
    }
    elsif ($line =~ /TCP, Blocked/) {
        $blocked = 1;
    }
    elsif ($line =~ /Local Address\s+=\s+\[([0-9:.]+)\]/) {
        $local_addr = "$1";
    }
    elsif ($line =~ /Foreign Address\s+=\s+\[([0-9:.]+)\]/) {
        $remote_addr = "$1";
    }
    elsif ($line =~ /Tx Offload: (\d+) \/ (\d+) \/ (\d+) \/ (\d+)/) {
        $txoff_kb = $1;
        $txoff_pkt = $2;
        $txoff_drop = $3;
        $txoff_err = $4;
    }
    elsif ($line =~ /n_rto: (\d+)/) {
        $n_rto = $1;
    }
    elsif ($line =~ /Retransmissions: (\d+)/) {
        $n_rtx = $1;
    }
    elsif ($line =~ /n_rtx_fast: (\d+)/) {
        $n_rtx_fast = $1;
    }
    elsif ($line =~ /n_rtx_rto: (\d+)/) {
        $n_rtx_rto = $1;
    }
    elsif ($line =~ /n_rtx_ss: (\d+)/) {
        $n_rtx_ss = $1;
    }
    elsif ($line =~ /n_rtx_spurious: (\d+)/) {
        $n_rtx_spurious = $1;
    }
    elsif ($line =~ /n_recovered_fast: (\d+)/) {
        $n_recovered_fast = $1;
    }
    elsif ($line =~ /n_dupacks: (\d+)/) {
        $n_dupacks = $1;
    }
    elsif ($line =~ /n_ofo: (\d+)/) {
        $n_ofo = $1;
    }
    elsif ($line =~ /n_underruns: (\d+)/) {
        $n_underruns = $1;
    }
    elsif ($line =~ /n_blocked_cwnd: (\d+)/) {
        $n_blocked_cwnd = $1;
    }
    elsif ($line =~ /n_blocked_rwnd: (\d+)/) {
        $n_blocked_rwnd = $1;
    }
    elsif ($line =~ /n_blocked_sndbuf: (\d+)/) {
        $n_blocked_sndbuf = $1;
    }
    elsif ($line =~ /n_updates_rtt: (\d+)/) {
        $n_updates_rtt = $1;
    }
    elsif ($line =~ /n_rst: (\d+)/) {
        $n_rst = $1;
    }
    elsif ($line =~ /n_zero_wnd: (\d+)/) {
        $n_zero_wnd = $1;
    }
    elsif ($line =~ /n_rx_ignored: (\d+)/) {
        $n_rx_ignored = $1;
    }
    elsif ($line =~ /n_dropped: (\d+)/) {
        $n_dropped = $1;
    }
    elsif ($line =~ /n_memerr_pbuf: (\d+)/) {
        $n_memerr_pbuf = $1;
    }
    elsif ($line =~ /n_memerr_seg: (\d+)/) {
        $n_memerr_seg = $1;
    }
    elsif ($line =~ /n_mss: (\d+)/) {
        $n_mss = $1;
    }
    elsif ($line =~ /n_rto_timer: (\d+)/) {
        $n_rto_timer = $1;
    }
    elsif ($line =~ /n_snd_wnd: (\d+)/) {
        $n_snd_wnd = $1;
    }
    elsif ($line =~ /n_cwnd: (\d+)/) {
        $n_cwnd = $1;
    }
    elsif ($line =~ /n_ssthresh: (\d+)/) {
        $n_ssthresh = $1;
    }
    elsif ($line =~ /time_up: (\d+)/) {
        $time_up = $1;
    }
    elsif ($line =~ /time_tx: (\d+)/) {
        $time_tx = $1;
    }
    elsif ($line =~ /time_rx: (\d+)/) {
        $time_rx = $1;
    }
    elsif ($line =~ /time_tx_wait: (\d+)/) {
        $time_tx_wait = $1;
    }
    elsif ($line =~ /time_rx_wait: (\d+)/) {
        $time_rx_wait = $1;
    }
    elsif ($line =~ /time_tcp_out: (\d+)/) {
        $time_tcp_out = $1;
    }
    elsif ($line =~ /time_tcp_rcv: (\d+)/) {
        $time_tcp_rcv = $1;
    }
    elsif ($line =~ /time_tcp_write: (\d+)/) {
        $time_tcp_write = $1;
    }
    elsif ($line =~ /time_epoll: (\d+)/) {
        $time_epoll = $1;
    }
    elsif ($line =~ /time_sendfile: (\d+)/) {
        $time_sendfile = $1;
    }
    elsif ($line =~ /time_readv: (\d+)/) {
        $time_readv = $1;
    }
}

database_fini();

#
# Subroutines
#

sub clear_all_vars
{
    $fd = 0;
    $blocked = 0;
    $local_addr = '';
    $remote_addr = '';
    $txoff_kb = 0;
    $txoff_pkt = 0;
    $txoff_drop = 0;
    $txoff_err = 0;
    $n_rto = 0;
    $n_rtx = 0;
    $n_rtx_fast = 0;
    $n_rtx_rto = 0;
    $n_rtx_ss = 0;
    $n_rtx_spurious = 0;
    $n_recovered_fast = 0;
    $n_dupacks = 0;
    $n_ofo = 0;
    $n_underruns = 0;
    $n_blocked_cwnd = 0;
    $n_blocked_rwnd = 0;
    $n_blocked_sndbuf = 0;
    $n_updates_rtt = 0;
    $n_rst = 0;
    $n_zero_wnd = 0;
    $n_rx_ignored = 0;
    $n_dropped = 0;
    $n_memerr_pbuf = 0;
    $n_memerr_seg = 0;
    $n_mss = 0;
    $n_rto_timer = 0;
    $n_snd_wnd = 0;
    $n_cwnd = 0;
    $n_ssthresh = 0;
    $time_up = 0;
    $time_tx = 0;
    $time_rx = 0;
    $time_tx_wait = 0;
    $time_rx_wait = 0;
    $time_tcp_out = 0;
    $time_tcp_rcv = 0;
    $time_tcp_write = 0;
    $time_epoll = 0;
    $time_sendfile = 0;
    $time_readv = 0;
}

sub database_init
{
    my $cmd = '';

    $cmd = 'CREATE TABLE info (';
    $cmd .= 'id INTEGER PRIMARY KEY,';
    $cmd .= 'uid INTEGER';
    $cmd .= ');';
    #print "$cmd\n";
    system("$sqlite $dbname \"$cmd\"");

    $cmd = 'INSERT INTO info VALUES (';
    $cmd .= '0,';
    $cmd .= '0';
    $cmd .= ');';
    #print "$cmd\n";
    system("$sqlite $dbname \"$cmd\"");

    $cmd = 'CREATE TABLE results (';
    $cmd .= 'id INTEGER PRIMARY KEY,';
    $cmd .= 'fd INTEGER,';
    $cmd .= 'blocked INTEGER,';
    $cmd .= 'local STRING,';
    $cmd .= 'remote STRING,';
    $cmd .= 'txoff_kb INTEGER,';
    $cmd .= 'txoff_pkt INTEGER,';
    $cmd .= 'txoff_drop INTEGER,';
    $cmd .= 'txoff_err INTEGER,';
    $cmd .= 'rto_nr INTEGER,';
    $cmd .= 'rtx INTEGER,';
    $cmd .= 'rtx_fast INTEGER,';
    $cmd .= 'rtx_rto INTEGER,';
    $cmd .= 'rtx_ss INTEGER,';
    $cmd .= 'rtx_spurious INTEGER,';
    $cmd .= 'recovered_fast INTEGER,';
    $cmd .= 'dupacks INTEGER,';
    $cmd .= 'ofo_nr INTEGER,';
    $cmd .= 'underruns INTEGER,';
    $cmd .= 'blocked_cwnd INTEGER,';
    $cmd .= 'blocked_rwnd INTEGER,';
    $cmd .= 'blocked_sndbuf INTEGER,';
    $cmd .= 'updates_rtt INTEGER,';
    $cmd .= 'rst_nr INTEGER,';
    $cmd .= 'zero_wnd INTEGER,';
    $cmd .= 'time_up INTEGER,';
    $cmd .= 'time_tx INTEGER,';
    $cmd .= 'time_rx INTEGER,';
    $cmd .= 'time_tx_wait INTEGER,';
    $cmd .= 'time_rx_wait INTEGER,';
    $cmd .= 'time_tcp_out INTEGER,';
    $cmd .= 'time_tcp_rcv INTEGER,';
    $cmd .= 'time_tcp_write INTEGER,';
    $cmd .= 'time_epoll INTEGER,';
    $cmd .= 'time_sendfile INTEGER,';
    $cmd .= 'time_readv INTEGER,';
    $cmd .= 'rx_ignored INTEGER,';
    $cmd .= 'tcp_drops INTEGER,';
    $cmd .= 'memerr_pbuf INTEGER,';
    $cmd .= 'memerr_seg INTEGER,';
    $cmd .= 'mss INTEGER,';
    $cmd .= 'rto_timer INTEGER,';
    $cmd .= 'snd_wnd INTEGER,';
    $cmd .= 'cwnd INTEGER,';
    $cmd .= 'ssthresh INTEGER';
    $cmd .= ');';
    #print "$cmd\n";
    system("$sqlite $dbname \"$cmd\"");
}

sub database_fini
{
    my $cmd = '';

    $cmd = "UPDATE info SET uid = $uid WHERE id = 0;";
    #print "$cmd\n";
    system("$sqlite $dbname \"$cmd\"");
}

sub database_read_state
{
    $uid = `$sqlite $dbname "select uid from info where id = 0;"`;
    chomp $uid;
}

sub store_stats
{
    my $cmd = '';

    $uid += 1;

    $cmd = 'INSERT INTO results (';
    $cmd .= 'id,';
    $cmd .= 'fd,';
    $cmd .= 'blocked,';
    $cmd .= 'local,';
    $cmd .= 'remote,';
    $cmd .= 'txoff_kb,';
    $cmd .= 'txoff_pkt,';
    $cmd .= 'txoff_drop,';
    $cmd .= 'txoff_err,';
    $cmd .= 'rto_nr,';
    $cmd .= 'rtx,';
    $cmd .= 'rtx_fast,';
    $cmd .= 'rtx_rto,';
    $cmd .= 'rtx_ss,';
    $cmd .= 'rtx_spurious,';
    $cmd .= 'recovered_fast,';
    $cmd .= 'dupacks,';
    $cmd .= 'ofo_nr,';
    $cmd .= 'underruns,';
    $cmd .= 'blocked_cwnd,';
    $cmd .= 'blocked_rwnd,';
    $cmd .= 'blocked_sndbuf,';
    $cmd .= 'updates_rtt,';
    $cmd .= 'rst_nr,';
    $cmd .= 'zero_wnd,';
    $cmd .= 'time_up,';
    $cmd .= 'time_tx,';
    $cmd .= 'time_rx,';
    $cmd .= 'time_tx_wait,';
    $cmd .= 'time_rx_wait,';
    $cmd .= 'time_tcp_out,';
    $cmd .= 'time_tcp_rcv,';
    $cmd .= 'time_tcp_write,';
    $cmd .= 'time_epoll,';
    $cmd .= 'time_sendfile,';
    $cmd .= 'time_readv,';
    $cmd .= 'rx_ignored,';
    $cmd .= 'tcp_drops,';
    $cmd .= 'memerr_pbuf,';
    $cmd .= 'memerr_seg,';
    $cmd .= 'mss,';
    $cmd .= 'rto_timer,';
    $cmd .= 'snd_wnd,';
    $cmd .= 'cwnd,';
    $cmd .= 'ssthresh';
    $cmd .= ') VALUES (';
    $cmd .= "$uid,";
    $cmd .= "$fd,";
    $cmd .= "$blocked,";
    $cmd .= "'$local_addr',";
    $cmd .= "'$remote_addr',";
    $cmd .= "$txoff_kb,";
    $cmd .= "$txoff_pkt,";
    $cmd .= "$txoff_drop,";
    $cmd .= "$txoff_err,";
    $cmd .= "$n_rto,";
    $cmd .= "$n_rtx,";
    $cmd .= "$n_rtx_fast,";
    $cmd .= "$n_rtx_rto,";
    $cmd .= "$n_rtx_ss,";
    $cmd .= "$n_rtx_spurious,";
    $cmd .= "$n_recovered_fast,";
    $cmd .= "$n_dupacks,";
    $cmd .= "$n_ofo,";
    $cmd .= "$n_underruns,";
    $cmd .= "$n_blocked_cwnd,";
    $cmd .= "$n_blocked_rwnd,";
    $cmd .= "$n_blocked_sndbuf,";
    $cmd .= "$n_updates_rtt,";
    $cmd .= "$n_rst,";
    $cmd .= "$n_zero_wnd,";
    $cmd .= "$time_up,";
    $cmd .= "$time_tx,";
    $cmd .= "$time_rx,";
    $cmd .= "$time_tx_wait,";
    $cmd .= "$time_rx_wait,";
    $cmd .= "$time_tcp_out,";
    $cmd .= "$time_tcp_rcv,";
    $cmd .= "$time_tcp_write,";
    $cmd .= "$time_epoll,";
    $cmd .= "$time_sendfile,";
    $cmd .= "$time_readv,";
    $cmd .= "$n_rx_ignored,";
    $cmd .= "$n_dropped,";
    $cmd .= "$n_memerr_pbuf,";
    $cmd .= "$n_memerr_seg,";
    $cmd .= "$n_mss,";
    $cmd .= "$n_rto_timer,";
    $cmd .= "$n_snd_wnd,";
    $cmd .= "$n_cwnd,";
    $cmd .= "$n_ssthresh";
    $cmd .= ");";
    #print "$cmd\n";
    system("$sqlite $dbname \"$cmd\"");
}
