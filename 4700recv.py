#!/usr/bin/env python3

import argparse, socket, time, json, select, struct, sys, math, hashlib

class Receiver:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', 0))
        self.port = self.socket.getsockname()[1]
        self.log("Bound to port %d" % self.port)

        self.remote_host = None
        self.remote_port = None
        
        # Track the highest sequence number we've seen
        self.last_seq = -1

    def send(self, message):
        self.log("Sent message %s" % json.dumps(message))
        self.socket.sendto(json.dumps(message).encode("utf-8"), (self.remote_host, self.remote_port))

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
            self.log("Received message %s" % data.decode("utf-8"))
            return json.loads(data.decode("utf-8"))

    def log(self, message):
        sys.stderr.write(message + "\n")
        sys.stderr.flush()
        
    def calculate_checksum(self, data):
        """Calculate a checksum for the data."""
        if not data:
            return "0"
        # Use MD5 for a simple but effective checksum
        return hashlib.md5(data.encode('utf-8') if isinstance(data, str) else data).hexdigest()

    def verify_checksum(self, msg):
        """Verify the checksum in the message matches the calculated checksum."""
        if "checksum" not in msg:
            # If no checksum in message, assume it's valid (backward compatibility)
            return True
            
        received_checksum = msg["checksum"]
        calculated_checksum = self.calculate_checksum(msg["data"])
        
        return received_checksum == calculated_checksum

    def run(self):
        while True:
            socks = select.select([self.socket], [], [])[0]
            for conn in socks:
                msg = self.recv(conn)

                if msg:
                    # Verify the checksum
                    if not self.verify_checksum(msg):
                        self.log(f"Checksum verification failed for packet {msg['seq']}, discarding")
                        # Send NACK to request retransmission
                        self.send({"type": "nack", "seq": msg["seq"]})
                        continue
                        
                    # Only print out the data if this is a new sequence number
                    if msg["seq"] > self.last_seq:
                        print(msg["data"], end='', flush=True)
                        self.last_seq = msg["seq"]

                    # Always send back an ack
                    self.send({ "type": "ack", "seq": msg["seq"] })


        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='receive data')
    args = parser.parse_args()
    sender = Receiver()
    sender.run()
