import socket
from dnslib import A, DNSRecord, QTYPE, RCODE, RR

FLAG = 0
cache = {}
PUBLIC_DNS_SERVERS = [
    ("Google", "8.8.8.8"),
    ("Cloudflare", "1.1.1.1"),
    ("Quad9", "9.9.9.9"),
    ("OpenDNS", "208.67.222.222"),
]
ROOT_DNS_SERVERS = ['198.41.0.4', '170.247.170.2', '192.33.4.12', '199.7.91.13',
                '192.203.230.10', '192.5.5.241', '192.112.36.4', '198.97.190.53',
                '192.36.148.17', '192.58.128.30', '193.0.14.129', '199.7.83.42',
                '202.12.27.33']

def read_exact(sock, size):
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ValueError("DNS server closed the TCP connection early")
        data.extend(chunk)
    return bytes(data)

def ask_server(domain, server_ip, recursive=False):
    request = DNSRecord.question(domain, "A")
    request.header.rd = int(recursive)
    packet = request.pack()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(3)
        print("Querying DNS server:", server_ip)
        sock.sendto(packet, (server_ip, 53))
        data, addr = sock.recvfrom(4096)

    if addr != (server_ip, 53):
        raise ValueError(f"DNS response came from {addr}, expected {server_ip}:53")
    try:
        response = DNSRecord.parse(data)
    except Exception as e:
        raise ValueError(f"Invalid DNS response from {server_ip}: {e}") from e

    if response.header.tc:
        print("UDP response truncated; retrying with TCP:", server_ip)
        with socket.create_connection((server_ip, 53), timeout=3) as sock:
            sock.settimeout(3)
            sock.sendall(len(packet).to_bytes(2, "big") + packet)
            size = int.from_bytes(read_exact(sock, 2), "big")
            data = read_exact(sock, size)
        try:
            response = DNSRecord.parse(data)
        except Exception as e:
            raise ValueError(f"Invalid TCP DNS response from {server_ip}: {e}") from e

    if not response.header.qr:
        raise ValueError(f"DNS response from {server_ip} is not marked as a reply")
    if response.header.id != request.header.id:
        raise ValueError(f"DNS response ID from {server_ip} does not match the request")
    if (not response.questions or
            str(response.q.qname).lower() != str(request.q.qname).lower() or
            response.q.qtype != QTYPE.A):
        raise ValueError(f"DNS response question from {server_ip} does not match the request")
    if response.header.tc:
        raise ValueError(f"TCP DNS response from {server_ip} is still truncated")

    return response

def query_public_dns(domain):
    errors = []
    for name, server_ip in PUBLIC_DNS_SERVERS:
        try:
            response = ask_server(
                domain, server_ip, recursive=True
            )
        except (OSError, ValueError) as e:
            errors.append(f"{name} ({server_ip}): {e}")
            continue

        if response.header.rcode == RCODE.NXDOMAIN:
            raise ValueError(f"Domain {domain} does not exist (NXDOMAIN)")
            
        if response.header.rcode != RCODE.NOERROR:
            errors.append(f"{name} ({server_ip}): {RCODE[response.header.rcode]}")
            continue

        for record in response.rr:
            if record.rtype == QTYPE.A:
                return str(record.rdata)
        errors.append(f"{name} ({server_ip}): no A record in the answer")

    raise ValueError(f"No public DNS server returned an A record for {domain}: "
                     + "; ".join(errors))
    
def query_iterative_dns(domain):
    def lookup(name, depth=0):
        name = str(name).lower().rstrip(".") + "."
        if depth >= 8:
            raise ValueError(f"Too many nested DNS or CNAME lookups for {name}")

        servers = ROOT_DNS_SERVERS[:]
        for _ in range(20):
            response = None
            errors = []
            for server_ip in servers:
                try:
                    candidate = ask_server(name, server_ip, recursive=False)
                    if candidate.header.rcode not in (RCODE.NOERROR, RCODE.NXDOMAIN):
                        errors.append(f"{server_ip}: {RCODE[candidate.header.rcode]}")
                        continue
                    response = candidate
                    break
                except (OSError, ValueError) as e:
                    errors.append(f"{server_ip}: {e}")
                    continue

            if response is None:
                raise ValueError(f"No usable DNS response for {name}: "
                                 + "; ".join(errors))
            if response.header.rcode == RCODE.NXDOMAIN:
                raise ValueError(f"Domain {name} does not exist (NXDOMAIN)")
            if response.header.rcode != RCODE.NOERROR:
                raise ValueError(f"DNS query for {name} failed: "
                                 f"{RCODE[response.header.rcode]}")

            for record in response.rr:
                if str(record.rname).lower() == name.lower() and record.rtype == QTYPE.A:
                    return str(record.rdata)

            for record in response.rr:
                if str(record.rname).lower() == name.lower() and record.rtype == QTYPE.CNAME:
                    return lookup(str(record.rdata), depth + 1)

            nameservers = {
                str(record.rdata).lower()
                for record in response.auth
                if record.rtype == QTYPE.NS
            }
            if not nameservers:
                raise ValueError(f"No A record or DNS referral found for {name}")

            servers = [
                str(record.rdata)
                for record in response.ar
                if record.rtype == QTYPE.A and str(record.rname).lower() in nameservers
            ]
            if not servers:
                ns_errors = []
                for ns in nameservers:
                    try:
                        servers.append(lookup(ns, depth + 1))
                    except ValueError as e:
                        ns_errors.append(f"{ns}: {e}")
                        continue
                if not servers:
                    raise ValueError(f"Could not resolve DNS servers for {name}: "
                                     + "; ".join(ns_errors))

        raise ValueError(f"Too many DNS referrals while looking up {name}")

    return lookup(domain)


def make_dns_response(request, ip):
    response = request.reply()
    response.add_answer(RR(rname=request.q.qname, rtype=QTYPE.A, rdata=A(ip), ttl=60))
    return response.pack()

def handle_request(data, addr, server):
    try:
        request = DNSRecord.parse(data)
    except Exception as e:
        print(f"Invalid DNS request from {addr}: {e}")
        return
    if not request.questions:
        print(f"DNS request from {addr} has no question")
        return
    domain = str(request.q.qname).lower()

    if request.q.qtype != QTYPE.A or request.q.qclass != 1:
        response = request.reply()
        response.header.rcode = RCODE.NOTIMP
        server.sendto(response.pack(), addr)
        return

    try:
        if domain in cache:
            ip = cache[domain]

        else:
            if FLAG == 0:
                ip = query_public_dns(domain)
            else:
                ip = query_iterative_dns(domain)

            cache[domain] = ip

        response_data = make_dns_response(request, ip)

    except Exception as e:
        print(f"DNS lookup failed for {domain}: {e}")
        response = request.reply()
        response.header.rcode = RCODE.SERVFAIL
        response_data = response.pack()

    server.sendto(response_data, addr)




def main():
    if FLAG not in (0, 1):
        raise ValueError("FLAG must be 0 (public DNS) or 1 (iterative DNS)")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind(("127.0.0.1", 1234))
        print(f"DNS server listening on 127.0.0.1:1234 (FLAG={FLAG})")

        while True:
            data, addr = server.recvfrom(4096)
            handle_request(data, addr, server)

if __name__ == "__main__":
    main()
