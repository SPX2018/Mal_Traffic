import json
import struct
import socket
import sys
import binascii
# ---Compatibility Helper Code Start---
if sys.version_info[0] == 2:
    # Python 2: Indexing strings returns characters. Use ord() to convert to integers
    def byte_to_int(b):
        return ord(b)
    # Python 2: Indexes strings and returns characters, requires ord() to convert to integers # Python 2: hexlify returns str, requires no decode
    def to_str(b):
        return str(b)
else:
    # Python 3: The index bytes return an integer. Return directly.
    def byte_to_int(b):
        return b
    # Python 3: hexlify returns bytes, JSON requires str, must decode
    def to_str(b):
        if isinstance(b, bytes):
            return b.decode('ascii', errors='ignore')
        return str(b)
# ---Compatibility Helper Code End ---
def extract_pcap_features(filepath):
    """
    Extract traffic features from PCAP file
    """
    results = []
    
    try:
        with open(filepath, 'rb') as f:
            # Read PCAP file header (24 bytes)
            header = f.read(24)
            if len(header) < 24:
                sys.stderr.write("Error: PCAP header too short\n")
                return json.dumps([])
            
            # Parse PCAP file header
            magic_number = struct.unpack('<I', header[0:4])[0]
            
            # Check byte order
            if magic_number == 0xA1B2C3D4:
                byte_order = '<'  # little endian
                sys.stderr.write("Little endian PCAP format\n")
            elif magic_number == 0xD4C3B2A1:
                byte_order = '>'  # big endian
                sys.stderr.write("Big endian PCAP format\n")
            else:
                sys.stderr.write("Unknown magic number: 0x{:08X}\n".format(magic_number))
                return json.dumps([])
            
            # Parse PCAP file header
            version_major = struct.unpack(byte_order + 'H', header[4:6])[0]
            version_minor = struct.unpack(byte_order + 'H', header[6:8])[0]
            sys.stderr.write("PCAP version: {}.{}\n".format(version_major, version_minor))
            
            # Read packets
            packet_count = 0
            while True:
                # Read packet header (16 bytes)
                packet_header = f.read(16)
                if len(packet_header) < 16:
                    sys.stderr.write("End of file or incomplete packet header\n")
                    break
                
                # Parse packet header
                ts_sec = struct.unpack(byte_order + 'I', packet_header[0:4])[0]
                ts_usec = struct.unpack(byte_order + 'I', packet_header[4:8])[0]
                incl_len = struct.unpack(byte_order + 'I', packet_header[8:12])[0]
                orig_len = struct.unpack(byte_order + 'I', packet_header[12:16])[0]
                
                sys.stderr.write("Packet {}: timestamp={}.{}, incl_len={}, orig_len={}\n".format(
                    packet_count, ts_sec, ts_usec, incl_len, orig_len))
                
                # Read packet data
                packet_data = f.read(incl_len)
                if len(packet_data) < incl_len:
                    sys.stderr.write("Incomplete packet data\n")
                    break
                
                # Parse Ethernet frame
                if len(packet_data) >= 14:
                    # Skip Ethernet header (14 bytes)
                    eth_type = struct.unpack('>H', packet_data[12:14])[0]
                    sys.stderr.write("Ethernet type: 0x{:04X}\n".format(eth_type))
                    
                    # Check if IPv4 (0x0800) or IPv6 (0x86DD)
                    if eth_type == 0x0800:
                        ip_data = packet_data[14:]
                        sys.stderr.write("IPv4 packet\n")
                    elif eth_type == 0x86DD:
                        ip_data = packet_data[14:]
                        sys.stderr.write("IPv6 packet\n")
                    else:
                        sys.stderr.write("Non-IP packet, type: 0x{:04X}\n".format(eth_type))
                        packet_count += 1
                        continue
                    
                    # Parse IP header
                    if len(ip_data) >= 20:
                        ip_header = ip_data[:20]
                        
                        # Parse IP version and header length
                        version_ihl =byte_to_int(ip_header[0])  # Convert byte to int
                        version = version_ihl >> 4
                        ihl = (version_ihl & 0x0F) * 4
                        
                        sys.stderr.write("IP version: {}, header length: {}\n".format(version, ihl))
                        
                        if version == 4 and len(ip_data) >= ihl:
                            # Extract source and destination IP
                            src_ip = socket.inet_ntoa(ip_header[12:16])
                            dst_ip = socket.inet_ntoa(ip_header[16:20])
                            
                            # Parse protocol type
                            protocol = byte_to_int(ip_header[9]) # Convert byte to int
                            
                            sys.stderr.write("IP: {} -> {}, protocol: {}\n".format(src_ip, dst_ip, protocol))
                            
                            # Extract transport layer data
                            transport_data = ip_data[ihl:]
                            
                            # Initialize features
                            ip_feature = "{} -> {}".format(src_ip, dst_ip)
                            port_feature = ""
                            statistical_data = {
                                "timestamp": "{}.{}".format(ts_sec, ts_usec),
                                "packet_length": incl_len,
                                "protocol": protocol
                            }
                            payload_feature = ""
                            
                            # Parse TCP
                            if protocol == 6 and len(transport_data) >= 20:
                                tcp_header = transport_data[:20]
                                src_port = struct.unpack('>H', tcp_header[0:2])[0]
                                dst_port = struct.unpack('>H', tcp_header[2:4])[0]
                                port_feature = "{} -> {}".format(src_port, dst_port)
                                
                                # Extract TCP flags
                                tcp_flags = byte_to_int(tcp_header[13])  # Convert byte to int
                                statistical_data["tcp_flags"] = {
                                    "fin": (tcp_flags & 0x01) != 0,
                                    "syn": (tcp_flags & 0x02) != 0,
                                    "rst": (tcp_flags & 0x04) != 0,
                                    "psh": (tcp_flags & 0x08) != 0,
                                    "ack": (tcp_flags & 0x10) != 0,
                                    "urg": (tcp_flags & 0x20) != 0
                                }
                                
                                # Extract TCP data offset
                                data_offset = (byte_to_int(tcp_header[12]) >> 4) * 4  # Convert byte to int
                                if len(transport_data) > data_offset:
                                    payload = transport_data[data_offset:]
                                    
                                    # Check if HTTP POST
                                    is_http_post = False
                                    if len(payload) >= 4 and payload[:4] == b'POST':
                                        is_http_post = True
                                    
                                    # Process payload
                                    if payload:
                                        if is_http_post:
                                            # HTTP POST - extract all payload
                                            payload_feature = binascii.hexlify(payload)
                                        else:
                                            # Check if encrypted traffic
                                            if is_encrypted(payload):
                                                payload_feature = "encrypted data"
                                            else:
                                                # Take first 500 bytes
                                                if len(payload) > 500:
                                                    payload_feature = binascii.hexlify(payload[:500])
                                                else:
                                                    payload_feature = binascii.hexlify(payload)
                                
                                sys.stderr.write("TCP: {} -> {}\n".format(src_port, dst_port))
                            
                            # Parse UDP
                            elif protocol == 17 and len(transport_data) >= 8:
                                udp_header = transport_data[:8]
                                src_port = struct.unpack('>H', udp_header[0:2])[0]
                                dst_port = struct.unpack('>H', udp_header[2:4])[0]
                                port_feature = "{} -> {}".format(src_port, dst_port)
                                
                                # Extract UDP payload
                                if len(transport_data) > 8:
                                    payload = transport_data[8:]
                                    
                                    # Check if DNS (port 53)
                                    if src_port == 53 or dst_port == 53:
                                        # DNS usually considered encrypted
                                        payload_feature = "encrypted data"
                                    else:
                                        # Check if encrypted
                                        if is_encrypted(payload):
                                            payload_feature = "encrypted data"
                                        else:
                                            # Take first 500 bytes
                                            if len(payload) > 500:
                                                payload_feature = binascii.hexlify(payload[:500])
                                            else:
                                                payload_feature = binascii.hexlify(payload)
                                
                                sys.stderr.write("UDP: {} -> {}\n".format(src_port, dst_port))
                            else:
                                sys.stderr.write("Other protocol: {}\n".format(protocol))
                            
                            # Add result
                            results.append({
                                "ip": ip_feature,
                                "port": port_feature,
                                "statistical_data": statistical_data,
                                "payload": payload_feature
                            })
                            
                            sys.stderr.write("Added result: IP={}, Port={}\n".format(ip_feature, port_feature))
                        else:
                            sys.stderr.write("Not IPv4 or header too short\n")
                    else:
                        sys.stderr.write("IP header too short\n")
                else:
                    sys.stderr.write("Packet too short for Ethernet\n")
                
                packet_count += 1
                if packet_count >= 10:  # Limit number of packets processed for testing
                    sys.stderr.write("Reached packet limit\n")
                    break
    
    except Exception as e:
        sys.stderr.write("Exception: {}\n".format(str(e)))
        import traceback
        traceback.print_exc(file=sys.stderr)
        return json.dumps([])
    
    sys.stderr.write("Total results: {}\n".format(len(results)))
    return json.dumps(results, default=lambda x: x.decode('utf-8', errors='ignore') if isinstance(x, bytes) else str(x))

def is_encrypted(payload):
    """
    Simple check if payload is encrypted
    """
    if not payload:
        return False
    
    # Check for common encrypted protocol signatures
    encrypted_indicators = [
        b'\x16\x03',  # TLS handshake
        b'\x17\x03',  # TLS application data
        b'SSH-',      # SSH
        b'\x80',      # SSLv2
    ]
    
    for indicator in encrypted_indicators:
        if payload.startswith(indicator):
            return True
    
    return False

# Execute extraction
if __name__ == "__main__":
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        print(extract_pcap_features(filepath))
    else:
        print(json.dumps([]))