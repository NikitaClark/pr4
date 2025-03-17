#!/usr/bin/env python3

import sys
import hashlib
import json
import random

def calculate_checksum(data):
    """Calculate a checksum for the data."""
    if not data:
        return "0"
    # Use MD5 for a simple but effective checksum
    return hashlib.md5(data.encode('utf-8') if isinstance(data, str) else data).hexdigest()

def test_checksum_verification():
    """Test the checksum verification functionality."""
    # Test case 1: Valid data
    test_data = "This is a test message"
    checksum = calculate_checksum(test_data)
    
    print(f"Original data: {test_data}")
    print(f"Checksum: {checksum}")
    
    # Verify checksum is correct
    recalculated = calculate_checksum(test_data)
    print(f"Recalculated checksum: {recalculated}")
    print(f"Checksums match: {checksum == recalculated}")
    
    # Test case 2: Corrupted data
    corrupted_data = test_data[:-1] + chr(ord(test_data[-1]) + 1)  # Change last character
    print(f"\nCorrupted data: {corrupted_data}")
    
    # Calculate checksum for corrupted data
    corrupted_checksum = calculate_checksum(corrupted_data)
    print(f"Corrupted checksum: {corrupted_checksum}")
    
    # Verify checksums don't match
    print(f"Checksums match (should be False): {checksum == corrupted_checksum}")
    
    # Test case 3: JSON packet
    packet = {
        "type": "msg",
        "data": test_data,
        "seq": 0,
        "checksum": checksum
    }
    
    print(f"\nOriginal packet: {json.dumps(packet)}")
    
    # Simulate packet corruption (change data but keep original checksum)
    corrupted_packet = packet.copy()
    corrupted_packet["data"] = corrupted_data
    
    print(f"Corrupted packet: {json.dumps(corrupted_packet)}")
    
    # Verify checksum
    original_checksum = packet["checksum"]
    calculated_checksum = calculate_checksum(packet["data"])
    print(f"Original packet checksum verification: {original_checksum == calculated_checksum}")
    
    corrupted_calculated = calculate_checksum(corrupted_packet["data"])
    print(f"Corrupted packet checksum verification: {original_checksum == corrupted_calculated}")

if __name__ == "__main__":
    test_checksum_verification() 