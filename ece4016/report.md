# DNS Server Experiment Report

## Implementation

The Python UDP server listens on `127.0.0.1:1234`. `FLAG=0` forwards A queries to public recursive DNS servers; `FLAG=1` follows referrals from root servers and resolves CNAMEs. Successful addresses are stored in an in-memory cache. Both runs enabled `DEBUG=1` and `SHOW_CACHE_HITS=1`, and each mode used a fresh server process.

Use Python 3.9 and install the permitted `dnslib` dependency with `python3 -m pip install dnslib`. From the `ece4016` directory, set `FLAG` in `dns_server.py`, run `python3 dns_server.py`, and issue `dig www.example.com @127.0.0.1 -p 1234` and `dig www.baidu.com @127.0.0.1 -p 1234` in another terminal. The same `dig` commands were used for the outputs below.

## Public DNS Test

With `FLAG=0`, both domains returned `NOERROR` and an A record. The server contacted `8.8.8.8` once per uncached domain. `DEBUG` prints full upstream replies only in iterative mode, so this server log contains the public server addresses and cache messages.

In both client transcripts, `SERVER: 127.0.0.1#1234` confirms that `dig` received the reply from the local server. The `ANSWER SECTION` contains one IPv4 address for the requested name, while the server log shows that the local server obtained each uncached answer by contacting the public resolver. The two `Cache hit` lines belong to the repeated queries described below.

The client output for `www.example.com` was:

```text
$ dig www.example.com @127.0.0.1 -p 1234

; <<>> DiG 9.18.39-0ubuntu0.24.04.7-Ubuntu <<>> www.example.com @127.0.0.1 -p 1234
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 51694
;; flags: qr aa rd ra ad; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;www.example.com.		IN	A

;; ANSWER SECTION:
www.example.com.	60	IN	A	172.66.147.243

;; SERVER: 127.0.0.1#1234(127.0.0.1) (UDP)
;; MSG SIZE  rcvd: 49
```

The client output for `www.baidu.com` was:

```text
$ dig www.baidu.com @127.0.0.1 -p 1234

; <<>> DiG 9.18.39-0ubuntu0.24.04.7-Ubuntu <<>> www.baidu.com @127.0.0.1 -p 1234
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 26275
;; flags: qr aa rd ra ad; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;www.baidu.com.			IN	A

;; ANSWER SECTION:
www.baidu.com.		60	IN	A	103.235.46.96

;; SERVER: 127.0.0.1#1234(127.0.0.1) (UDP)
;; MSG SIZE  rcvd: 47
```

The server output with `DEBUG=1` and `SHOW_CACHE_HITS=1`, including the repeated queries used in Cache Test, was:

```text
DNS server listening on 127.0.0.1:1234 (FLAG=0)
Querying DNS server: 8.8.8.8
Cache hit: www.example.com. -> 172.66.147.243
Querying DNS server: 8.8.8.8
Cache hit: www.baidu.com. -> 103.235.46.96
```

## Iterative DNS Test

With `FLAG=1`, both domains returned `NOERROR` and an A record. The server log records each received DNS reply, including referral and answer sections; `www.baidu.com` also followed a CNAME to `www.a.shifen.com`. The first `www.baidu.com` command showed two timeout notices before `dig` received a valid answer.

The `www.example.com` trace starts with a root-server referral for `.com`, continues to a `.com` server, and ends with an authoritative A answer. For `www.baidu.com`, the first authoritative answer is a CNAME, so the server starts another lookup for `www.a.shifen.com` and returns its A address to the client. This explains why the Baidu trace contains more upstream queries than the Example trace.

Some `Querying DNS server` lines have no matching `Response from` line because the attempted server did not provide a usable reply and the program tried another address. The root reply for the CNAME lookup was truncated over UDP; the following TCP reply supplied the records needed to continue. The two client timeout notices therefore show a slow first lookup, not a failed final result: the same `dig` command eventually received `NOERROR` and an A record.

The client output for `www.example.com` was:

```text
$ dig www.example.com @127.0.0.1 -p 1234

; <<>> DiG 9.18.39-0ubuntu0.24.04.7-Ubuntu <<>> www.example.com @127.0.0.1 -p 1234
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 38961
;; flags: qr aa rd ra ad; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;www.example.com.		IN	A

;; ANSWER SECTION:
www.example.com.	60	IN	A	172.66.147.243

;; SERVER: 127.0.0.1#1234(127.0.0.1) (UDP)
;; MSG SIZE  rcvd: 49
```

The client output for `www.baidu.com` was:

```text
$ dig www.baidu.com @127.0.0.1 -p 1234
;; communications error to 127.0.0.1#1234: timed out
;; communications error to 127.0.0.1#1234: timed out

; <<>> DiG 9.18.39-0ubuntu0.24.04.7-Ubuntu <<>> www.baidu.com @127.0.0.1 -p 1234
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 37089
;; flags: qr aa rd ra ad; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;www.baidu.com.			IN	A

;; ANSWER SECTION:
www.baidu.com.		60	IN	A	183.2.172.177

;; SERVER: 127.0.0.1#1234(127.0.0.1) (UDP)
;; MSG SIZE  rcvd: 47
```

The server output with `DEBUG=1` and `SHOW_CACHE_HITS=1`, including the repeated queries used in Cache Test, was:

```text
DNS server listening on 127.0.0.1:1234 (FLAG=1)
Querying DNS server: 198.41.0.4
Querying DNS server: 170.247.170.2
Response from 170.247.170.2 (UDP):
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 35631
;; flags: qr; QUERY: 1, ANSWER: 0, AUTHORITY: 13, ADDITIONAL: 12
;; QUESTION SECTION:
;www.example.com.               IN      A
;; AUTHORITY SECTION:
com.                    172800  IN      NS      a.gtld-servers.net.
com.                    172800  IN      NS      b.gtld-servers.net.
com.                    172800  IN      NS      c.gtld-servers.net.
com.                    172800  IN      NS      d.gtld-servers.net.
com.                    172800  IN      NS      e.gtld-servers.net.
com.                    172800  IN      NS      f.gtld-servers.net.
com.                    172800  IN      NS      g.gtld-servers.net.
com.                    172800  IN      NS      h.gtld-servers.net.
com.                    172800  IN      NS      i.gtld-servers.net.
com.                    172800  IN      NS      j.gtld-servers.net.
com.                    172800  IN      NS      k.gtld-servers.net.
com.                    172800  IN      NS      l.gtld-servers.net.
com.                    172800  IN      NS      m.gtld-servers.net.
;; ADDITIONAL SECTION:
a.gtld-servers.net.     172800  IN      A       192.5.6.30
a.gtld-servers.net.     172800  IN      AAAA    2001:503:a83e::2:30
b.gtld-servers.net.     172800  IN      A       192.33.14.30
b.gtld-servers.net.     172800  IN      AAAA    2001:503:231d::2:30
c.gtld-servers.net.     172800  IN      A       192.26.92.30
c.gtld-servers.net.     172800  IN      AAAA    2001:503:83eb::30
d.gtld-servers.net.     172800  IN      A       192.31.80.30
d.gtld-servers.net.     172800  IN      AAAA    2001:500:856e::30
e.gtld-servers.net.     172800  IN      A       192.12.94.30
e.gtld-servers.net.     172800  IN      AAAA    2001:502:1ca1::30
f.gtld-servers.net.     172800  IN      A       192.35.51.30
g.gtld-servers.net.     172800  IN      A       192.42.93.30
Querying DNS server: 192.5.6.30
Response from 192.5.6.30 (UDP):
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 27541
;; flags: qr; QUERY: 1, ANSWER: 0, AUTHORITY: 2, ADDITIONAL: 12
;; QUESTION SECTION:
;www.example.com.               IN      A
;; AUTHORITY SECTION:
example.com.            172800  IN      NS      hera.ns.cloudflare.com.
example.com.            172800  IN      NS      elliott.ns.cloudflare.com.
;; ADDITIONAL SECTION:
hera.ns.cloudflare.com. 172800  IN      A       108.162.192.162
hera.ns.cloudflare.com. 172800  IN      A       172.64.32.162
hera.ns.cloudflare.com. 172800  IN      A       173.245.58.162
hera.ns.cloudflare.com. 172800  IN      AAAA    2606:4700:50::adf5:3aa2
hera.ns.cloudflare.com. 172800  IN      AAAA    2803:f800:50::6ca2:c0a2
hera.ns.cloudflare.com. 172800  IN      AAAA    2a06:98c1:50::ac40:20a2
elliott.ns.cloudflare.com. 172800  IN      A       108.162.195.228
elliott.ns.cloudflare.com. 172800  IN      A       162.159.44.228
elliott.ns.cloudflare.com. 172800  IN      A       172.64.35.228
elliott.ns.cloudflare.com. 172800  IN      AAAA    2606:4700:58::a29f:2ce4
elliott.ns.cloudflare.com. 172800  IN      AAAA    2803:f800:50::6ca2:c3e4
elliott.ns.cloudflare.com. 172800  IN      AAAA    2a06:98c1:50::ac40:23e4
Querying DNS server: 108.162.192.162
Response from 108.162.192.162 (UDP):
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 60832
;; flags: qr aa; QUERY: 1, ANSWER: 2, AUTHORITY: 0, ADDITIONAL: 0
;; QUESTION SECTION:
;www.example.com.               IN      A
;; ANSWER SECTION:
www.example.com.        300     IN      A       172.66.147.243
www.example.com.        300     IN      A       104.20.23.154
Cache hit: www.example.com. -> 172.66.147.243
Querying DNS server: 198.41.0.4
Querying DNS server: 170.247.170.2
Response from 170.247.170.2 (UDP):
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 34331
;; flags: qr; QUERY: 1, ANSWER: 0, AUTHORITY: 13, ADDITIONAL: 12
;; QUESTION SECTION:
;www.baidu.com.                 IN      A
;; AUTHORITY SECTION:
com.                    172800  IN      NS      a.gtld-servers.net.
com.                    172800  IN      NS      b.gtld-servers.net.
com.                    172800  IN      NS      c.gtld-servers.net.
com.                    172800  IN      NS      d.gtld-servers.net.
com.                    172800  IN      NS      e.gtld-servers.net.
com.                    172800  IN      NS      f.gtld-servers.net.
com.                    172800  IN      NS      g.gtld-servers.net.
com.                    172800  IN      NS      h.gtld-servers.net.
com.                    172800  IN      NS      i.gtld-servers.net.
com.                    172800  IN      NS      j.gtld-servers.net.
com.                    172800  IN      NS      k.gtld-servers.net.
com.                    172800  IN      NS      l.gtld-servers.net.
com.                    172800  IN      NS      m.gtld-servers.net.
;; ADDITIONAL SECTION:
a.gtld-servers.net.     172800  IN      A       192.5.6.30
a.gtld-servers.net.     172800  IN      AAAA    2001:503:a83e::2:30
b.gtld-servers.net.     172800  IN      A       192.33.14.30
b.gtld-servers.net.     172800  IN      AAAA    2001:503:231d::2:30
c.gtld-servers.net.     172800  IN      A       192.26.92.30
c.gtld-servers.net.     172800  IN      AAAA    2001:503:83eb::30
d.gtld-servers.net.     172800  IN      A       192.31.80.30
d.gtld-servers.net.     172800  IN      AAAA    2001:500:856e::30
e.gtld-servers.net.     172800  IN      A       192.12.94.30
e.gtld-servers.net.     172800  IN      AAAA    2001:502:1ca1::30
f.gtld-servers.net.     172800  IN      A       192.35.51.30
g.gtld-servers.net.     172800  IN      A       192.42.93.30
Querying DNS server: 192.5.6.30
Response from 192.5.6.30 (UDP):
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 15027
;; flags: qr; QUERY: 1, ANSWER: 0, AUTHORITY: 5, ADDITIONAL: 11
;; QUESTION SECTION:
;www.baidu.com.                 IN      A
;; AUTHORITY SECTION:
baidu.com.              172800  IN      NS      ns2.baidu.com.
baidu.com.              172800  IN      NS      ns3.baidu.com.
baidu.com.              172800  IN      NS      ns4.baidu.com.
baidu.com.              172800  IN      NS      ns1.baidu.com.
baidu.com.              172800  IN      NS      ns7.baidu.com.
;; ADDITIONAL SECTION:
ns2.baidu.com.          172800  IN      A       220.181.33.31
ns2.baidu.com.          172800  IN      AAAA    240e:940:603:4:0:ff:b01b:589a
ns3.baidu.com.          172800  IN      A       153.3.238.93
ns3.baidu.com.          172800  IN      A       36.155.132.78
ns4.baidu.com.          172800  IN      A       111.45.3.226
ns4.baidu.com.          172800  IN      A       14.215.178.80
ns1.baidu.com.          172800  IN      A       110.242.68.134
ns1.baidu.com.          172800  IN      AAAA    240e:bf:b801:1002:0:ff:b024:26de
ns7.baidu.com.          172800  IN      A       14.215.178.80
ns7.baidu.com.          172800  IN      AAAA    240e:940:603:4:0:ff:b01b:589a
ns7.baidu.com.          172800  IN      AAAA    240e:bf:b801:1002:0:ff:b024:26de
Querying DNS server: 220.181.33.31
Response from 220.181.33.31 (UDP):
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 11170
;; flags: qr aa; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0
;; QUESTION SECTION:
;www.baidu.com.                 IN      A
;; ANSWER SECTION:
www.baidu.com.          1200    IN      CNAME   www.a.shifen.com.
Querying DNS server: 198.41.0.4
Response from 198.41.0.4 (UDP):
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 26815
;; flags: qr tc; QUERY: 1, ANSWER: 0, AUTHORITY: 13, ADDITIONAL: 11
;; QUESTION SECTION:
;www.a.shifen.com.              IN      A
;; AUTHORITY SECTION:
com.                    172800  IN      NS      l.gtld-servers.net.
com.                    172800  IN      NS      j.gtld-servers.net.
com.                    172800  IN      NS      h.gtld-servers.net.
com.                    172800  IN      NS      d.gtld-servers.net.
com.                    172800  IN      NS      b.gtld-servers.net.
com.                    172800  IN      NS      f.gtld-servers.net.
com.                    172800  IN      NS      k.gtld-servers.net.
com.                    172800  IN      NS      m.gtld-servers.net.
com.                    172800  IN      NS      i.gtld-servers.net.
com.                    172800  IN      NS      g.gtld-servers.net.
com.                    172800  IN      NS      a.gtld-servers.net.
com.                    172800  IN      NS      c.gtld-servers.net.
com.                    172800  IN      NS      e.gtld-servers.net.
;; ADDITIONAL SECTION:
l.gtld-servers.net.     172800  IN      A       192.41.162.30
l.gtld-servers.net.     172800  IN      AAAA    2001:500:d937::30
j.gtld-servers.net.     172800  IN      A       192.48.79.30
j.gtld-servers.net.     172800  IN      AAAA    2001:502:7094::30
h.gtld-servers.net.     172800  IN      A       192.54.112.30
h.gtld-servers.net.     172800  IN      AAAA    2001:502:8cc::30
d.gtld-servers.net.     172800  IN      A       192.31.80.30
d.gtld-servers.net.     172800  IN      AAAA    2001:500:856e::30
b.gtld-servers.net.     172800  IN      A       192.33.14.30
b.gtld-servers.net.     172800  IN      AAAA    2001:503:231d::2:30
f.gtld-servers.net.     172800  IN      A       192.35.51.30
UDP response truncated; retrying with TCP: 198.41.0.4
Response from 198.41.0.4 (TCP):
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 26815
;; flags: qr; QUERY: 1, ANSWER: 0, AUTHORITY: 13, ADDITIONAL: 26
;; QUESTION SECTION:
;www.a.shifen.com.              IN      A
;; AUTHORITY SECTION:
com.                    172800  IN      NS      l.gtld-servers.net.
com.                    172800  IN      NS      j.gtld-servers.net.
com.                    172800  IN      NS      h.gtld-servers.net.
com.                    172800  IN      NS      d.gtld-servers.net.
com.                    172800  IN      NS      b.gtld-servers.net.
com.                    172800  IN      NS      f.gtld-servers.net.
com.                    172800  IN      NS      k.gtld-servers.net.
com.                    172800  IN      NS      m.gtld-servers.net.
com.                    172800  IN      NS      i.gtld-servers.net.
com.                    172800  IN      NS      g.gtld-servers.net.
com.                    172800  IN      NS      a.gtld-servers.net.
com.                    172800  IN      NS      c.gtld-servers.net.
com.                    172800  IN      NS      e.gtld-servers.net.
;; ADDITIONAL SECTION:
l.gtld-servers.net.     172800  IN      A       192.41.162.30
l.gtld-servers.net.     172800  IN      AAAA    2001:500:d937::30
j.gtld-servers.net.     172800  IN      A       192.48.79.30
j.gtld-servers.net.     172800  IN      AAAA    2001:502:7094::30
h.gtld-servers.net.     172800  IN      A       192.54.112.30
h.gtld-servers.net.     172800  IN      AAAA    2001:502:8cc::30
d.gtld-servers.net.     172800  IN      A       192.31.80.30
d.gtld-servers.net.     172800  IN      AAAA    2001:500:856e::30
b.gtld-servers.net.     172800  IN      A       192.33.14.30
b.gtld-servers.net.     172800  IN      AAAA    2001:503:231d::2:30
f.gtld-servers.net.     172800  IN      A       192.35.51.30
f.gtld-servers.net.     172800  IN      AAAA    2001:503:d414::30
k.gtld-servers.net.     172800  IN      A       192.52.178.30
k.gtld-servers.net.     172800  IN      AAAA    2001:503:d2d::30
m.gtld-servers.net.     172800  IN      A       192.55.83.30
m.gtld-servers.net.     172800  IN      AAAA    2001:501:b1f9::30
i.gtld-servers.net.     172800  IN      A       192.43.172.30
i.gtld-servers.net.     172800  IN      AAAA    2001:503:39c1::30
g.gtld-servers.net.     172800  IN      A       192.42.93.30
g.gtld-servers.net.     172800  IN      AAAA    2001:503:eea3::30
a.gtld-servers.net.     172800  IN      A       192.5.6.30
a.gtld-servers.net.     172800  IN      AAAA    2001:503:a83e::2:30
c.gtld-servers.net.     172800  IN      A       192.26.92.30
c.gtld-servers.net.     172800  IN      AAAA    2001:503:83eb::30
e.gtld-servers.net.     172800  IN      A       192.12.94.30
e.gtld-servers.net.     172800  IN      AAAA    2001:502:1ca1::30
Querying DNS server: 192.41.162.30
Querying DNS server: 192.48.79.30
Querying DNS server: 192.54.112.30
Response from 192.54.112.30 (UDP):
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 28943
;; flags: qr; QUERY: 1, ANSWER: 0, AUTHORITY: 4, ADDITIONAL: 8
;; QUESTION SECTION:
;www.a.shifen.com.              IN      A
;; AUTHORITY SECTION:
shifen.com.             172800  IN      NS      dns.baidu.com.
shifen.com.             172800  IN      NS      ns2.baidu.com.
shifen.com.             172800  IN      NS      ns3.baidu.com.
shifen.com.             172800  IN      NS      ns4.baidu.com.
;; ADDITIONAL SECTION:
dns.baidu.com.          172800  IN      A       110.242.68.134
dns.baidu.com.          172800  IN      AAAA    240e:bf:b801:1002:0:ff:b024:26de
ns2.baidu.com.          172800  IN      A       220.181.33.31
ns2.baidu.com.          172800  IN      AAAA    240e:940:603:4:0:ff:b01b:589a
ns3.baidu.com.          172800  IN      A       153.3.238.93
ns3.baidu.com.          172800  IN      A       36.155.132.78
ns4.baidu.com.          172800  IN      A       111.45.3.226
ns4.baidu.com.          172800  IN      A       14.215.178.80
Querying DNS server: 110.242.68.134
Response from 110.242.68.134 (UDP):
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 964
;; flags: qr; QUERY: 1, ANSWER: 0, AUTHORITY: 5, ADDITIONAL: 9
;; QUESTION SECTION:
;www.a.shifen.com.              IN      A
;; AUTHORITY SECTION:
a.shifen.com.           86400   IN      NS      ns2.a.shifen.com.
a.shifen.com.           86400   IN      NS      ns1.a.shifen.com.
a.shifen.com.           86400   IN      NS      ns5.a.shifen.com.
a.shifen.com.           86400   IN      NS      ns4.a.shifen.com.
a.shifen.com.           86400   IN      NS      ns3.a.shifen.com.
;; ADDITIONAL SECTION:
ns5.a.shifen.com.       86400   IN      A       14.215.177.229
ns4.a.shifen.com.       86400   IN      A       14.215.177.229
ns4.a.shifen.com.       86400   IN      A       111.20.4.28
ns3.a.shifen.com.       86400   IN      A       36.155.132.12
ns3.a.shifen.com.       86400   IN      A       153.3.238.162
ns2.a.shifen.com.       86400   IN      A       220.181.33.32
ns1.a.shifen.com.       86400   IN      A       110.242.68.42
ns5.a.shifen.com.       86400   IN      AAAA    240e:bf:b801:1006:0:ff:b04f:346b
ns5.a.shifen.com.       86400   IN      AAAA    240e:940:603:a:0:ff:b08d:239d
Querying DNS server: 14.215.177.229
Response from 14.215.177.229 (UDP):
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 11247
;; flags: qr aa; QUERY: 1, ANSWER: 1, AUTHORITY: 5, ADDITIONAL: 9
;; QUESTION SECTION:
;www.a.shifen.com.              IN      A
;; ANSWER SECTION:
www.a.shifen.com.       120     IN      A       183.2.172.177
;; AUTHORITY SECTION:
a.shifen.com.           86400   IN      NS      ns5.a.shifen.com.
a.shifen.com.           86400   IN      NS      ns1.a.shifen.com.
a.shifen.com.           86400   IN      NS      ns2.a.shifen.com.
a.shifen.com.           86400   IN      NS      ns3.a.shifen.com.
a.shifen.com.           86400   IN      NS      ns4.a.shifen.com.
;; ADDITIONAL SECTION:
ns1.a.shifen.com.       86400   IN      A       110.242.68.42
ns2.a.shifen.com.       86400   IN      A       220.181.33.32
ns3.a.shifen.com.       86400   IN      A       36.155.132.12
ns3.a.shifen.com.       86400   IN      A       153.3.238.162
ns4.a.shifen.com.       86400   IN      A       14.215.177.229
ns4.a.shifen.com.       86400   IN      A       111.20.4.28
ns5.a.shifen.com.       86400   IN      A       14.215.177.229
ns5.a.shifen.com.       86400   IN      AAAA    240e:bf:b801:1006:0:ff:b04f:346b
ns5.a.shifen.com.       86400   IN      AAAA    240e:940:603:a:0:ff:b08d:239d
Cache hit: www.baidu.com. -> 183.2.172.177
Cache hit: www.baidu.com. -> 183.2.172.177
Cache hit: www.baidu.com. -> 183.2.172.177
```

## Cache Test

Each domain was queried twice in each mode without restarting the server. The second query returned the same A record, printed a `Cache hit` line, and caused no additional upstream query. In the iterative `www.baidu.com` run, `dig` also retried after its first timeout, which explains the extra cache-hit lines before the separately repeated command.

The strongest evidence for a cache hit is the combination of the matching second answer, the explicit `Cache hit` message, and the unchanged number of `Querying DNS server` lines. An unchanged answer alone would not prove that the cache was used, because an upstream server could return the same address again. The cache is in memory, so these observations apply while each server process remains running.

With `FLAG=0`, `www.example.com` returned `172.66.147.243` both times; the cumulative upstream-query count stayed at 1 after the repeat, while cache-hit messages for that domain increased from 0 to 1.

With `FLAG=0`, `www.baidu.com` returned `103.235.46.96` both times; the cumulative upstream-query count stayed at 2 after the repeat, while cache-hit messages for that domain increased from 0 to 1.

With `FLAG=1`, `www.example.com` returned `172.66.147.243` both times; the cumulative upstream-query count stayed at 4 after the repeat, while cache-hit messages for that domain increased from 0 to 1.

With `FLAG=1`, `www.baidu.com` returned `183.2.172.177` both times; the cumulative upstream-query count stayed at 14 after the repeat, while cache-hit messages for that domain increased from 2 to 3.

## Conclusion

Both lookup modes resolved both required domains. The public mode obtained answers through `8.8.8.8`, while the iterative mode followed referrals and a CNAME to reach authoritative answers. Repeated queries used the in-memory cache without new upstream requests. One iterative lookup produced two client timeout notices, but its retry succeeded and returned a valid answer.
