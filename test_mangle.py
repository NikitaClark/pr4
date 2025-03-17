#!/usr/bin/env python3

import socket
import threading
import time
import json
import random
import sys
import hashlib

# Sender configuration
SENDER_HOST = '127.0.0.1'
SENDER_PORT = 12345

# Receiver configuration
RECEIVER_HOST = '127.0.0.1'
RECEIVER_PORT = 12346

# Test data
TEST_DATA = """This is a test message for our reliable transport protocol.
It contains multiple lines to simulate a larger data transfer.
We'll use this to verify that our checksum implementation works correctly
when packets are corrupted during transmission."""

# Mangle probability (0.3 = 30% chance of corruption)
MANGLE_PROB = 0.3

def calculate_checksum(data):
    """Calculate a checksum for the data."""
    if not data:
        return "0"
    # Use MD5 for a simple but effective checksum
    return hashlib.md5(data.encode('utf-8') if isinstance(data, str) else data).hexdigest()

class TestReceiver:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((RECEIVER_HOST, RECEIVER_PORT))
        self.received_data = []
        self.last_seq = -1
        print(f"Receiver started on {RECEIVER_HOST}:{RECEIVER_PORT}")
        
    def verify_checksum(self, msg):
        """Verify the checksum in the message matches the calculated checksum."""
        if "checksum" not in msg:
            return True
            
        received_checksum = msg["checksum"]
        calculated_checksum = calculate_checksum(msg["data"])
        
        return received_checksum == calculated_checksum
        
    def run(self):
        while True:
            try:
                data, addr = self.socket.recvfrom(65535)
                msg = json.loads(data.decode('utf-8'))
                
                print(f"Receiver got: {msg}")
                
                # Verify checksum
                if not self.verify_checksum(msg):
                    print(f"Checksum verification failed for packet {msg['seq']}")
                    # Send NACK
                    response = {"type": "nack", "seq": msg["seq"]}
                else:
                    # Process new data
                    if msg["seq"] > self.last_seq:
                        self.received_data.append(msg["data"])
                        self.last_seq = msg["seq"]
                    
                    # Send ACK
                    response = {"type": "ack", "seq": msg["seq"]}
                
                # Send response back to sender
                self.socket.sendto(json.dumps(response).encode('utf-8'), addr)
                
            except Exception as e:
                print(f"Receiver error: {e}")
                break

class TestSender:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((SENDER_HOST, SENDER_PORT))
        print(f"Sender started on {SENDER_HOST}:{SENDER_PORT}")
        
    def send_data(self, data, chunk_size=50):
        # Split data into chunks
        chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
        
        for seq, chunk in enumerate(chunks):
            # Create packet with checksum
            checksum = calculate_checksum(chunk)
            packet = {"type": "msg", "data": chunk, "seq": seq, "checksum": checksum}
            
            # Send packet (with potential mangling)
            self.send_packet(packet)
            
    def send_packet(self, packet):
        packet_json = json.dumps(packet)
        
        # Potentially mangle the packet
        if random.random() < MANGLE_PROB:
            # Create a corrupted version by changing a character in the data
            corrupted_packet = packet.copy()
            if len(corrupted_packet["data"]) > 0:
                pos = random.randint(0, len(corrupted_packet["data"]) - 1)
                char_list = list(corrupted_packet["data"])
                char_list[pos] = chr(ord(char_list[pos]) + 1)  # Change one character
                corrupted_packet["data"] = ''.join(char_list)
                
                print(f"MANGLED PACKET {packet['seq']}: Original: '{packet['data']}', Corrupted: '{corrupted_packet['data']}'")
                packet_json = json.dumps(corrupted_packet)
            
        # Send the packet
        self.socket.sendto(packet_json.encode('utf-8'), (RECEIVER_HOST, RECEIVER_PORT))
        print(f"Sent packet {packet['seq']}")
        
        # Wait for ACK/NACK
        self.socket.settimeout(1.0)
        try:
            while True:
                data, addr = self.socket.recvfrom(65535)
                response = json.loads(data.decode('utf-8'))
                
                if response["type"] == "ack" and response["seq"] == packet["seq"]:
                    print(f"Received ACK for packet {packet['seq']}")
                    break
                elif response["type"] == "nack" and response["seq"] == packet["seq"]:
                    print(f"Received NACK for packet {packet['seq']}, resending")
                    # Resend the original (uncorrupted) packet
                    self.socket.sendto(json.dumps(packet).encode('utf-8'), (RECEIVER_HOST, RECEIVER_PORT))
                    continue
            
        except socket.timeout:
            print(f"Timeout waiting for ACK for packet {packet['seq']}, resending")
            self.send_packet(packet)  # Recursive retry

def main():
    # Start receiver in a separate thread
    receiver = TestReceiver()
    receiver_thread = threading.Thread(target=receiver.run)
    receiver_thread.daemon = True
    receiver_thread.start()
    
    # Give receiver time to start
    time.sleep(1)
    
    # Start sender and send test data
    sender = TestSender()
    sender.send_data(TEST_DATA)
    
    # Wait for all data to be received
    time.sleep(2)
    
    # Print received data
    print("\nReceived data:")
    print(''.join(receiver.received_data))
    
    # Verify data integrity
    original_data = TEST_DATA
    received_data = ''.join(receiver.received_data)
    
    if original_data == received_data:
        print("\nSUCCESS: Data transmitted correctly with checksums!")
    else:
        print("\nFAILURE: Data was corrupted during transmission.")
        print(f"Original length: {len(original_data)}, Received length: {len(received_data)}")

if __name__ == "__main__":
    main() 