#!/usr/bin/env python3

import argparse, socket, time, json, select, struct, sys, math, hashlib

DATA_SIZE = 1375

class Sender:
    def __init__(self, host, port):
        self.host = host
        self.remote_port = int(port)
        self.log("Sender starting up using port %s" % self.remote_port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', 0))
        self.local_port = self.socket.getsockname()[1]
        self.log("Bound to port %d" % self.local_port)
        self.waiting = False

        self.remote_host = None

    def log(self, message):
        sys.stderr.write(message + "\n")
        sys.stderr.flush()

    def calculate_checksum(self, data):
        """Calculate a checksum for the data."""
        if not data:
            return "0"
        # Use MD5 for a simple but effective checksum
        return hashlib.md5(data.encode('utf-8') if isinstance(data, str) else data).hexdigest()

    def send(self, message):
        self.log("Sending message '%s'" % json.dumps(message))
        self.socket.sendto(json.dumps(message).encode("utf-8"), (self.host, self.remote_port))

    def recv(self, socket):
        data, addr = socket.recvfrom(65535)

        # Grab the remote host/port if we don't already have it
        if self.remote_host is None:
            self.remote_host = addr[0]
            self.remote_port = addr[1]

        # Make sure we're talking to the same remote host
        if addr != (self.remote_host, self.remote_port):
            self.log("Error:  Received response from unexpected remote; ignoring")
            return None
        else:
            self.log("Received message %s" % data)
            return json.loads(data.decode("utf-8"))

    def run(self):
        seq = 0
        data = sys.stdin.read()  # Read all input at once
        
        # Send data in chunks
        while data:
            # Create packet with data and checksum
            chunk = data[:DATA_SIZE]
            checksum = self.calculate_checksum(chunk)
            msg = {"type": "msg", "data": chunk, "seq": seq, "checksum": checksum}
            self.send(msg)
            
            # Wait for ACK
            ack_received = False
            while not ack_received:
                ready = select.select([self.socket], [], [], 0.5)[0]  # 500ms timeout
                if not ready:
                    # Timeout occurred, resend packet
                    self.log("Timeout waiting for ACK, resending packet %d" % seq)
                    self.send(msg)
                    continue
                    
                for s in ready:
                    response = self.recv(s)
                    if response and response["type"] == "ack" and response["seq"] == seq:
                        self.log("Received ACK for packet %d" % seq)
                        ack_received = True
                        break
                    elif response and response["type"] == "nack" and response["seq"] == seq:
                        self.log("Received NACK for packet %d (checksum failed), resending" % seq)
                        self.send(msg)
                        continue
            
            # Move to next chunk
            data = data[DATA_SIZE:]
            seq += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='send data')
    parser.add_argument('host', type=str, help="Remote host to connect to")
    parser.add_argument('port', type=int, help="UDP port number to connect to")
    args = parser.parse_args()
    sender = Sender(args.host, args.port)
    sender.run()
