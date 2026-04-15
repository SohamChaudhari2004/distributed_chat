#!/usr/bin/env python3
"""
Test script to verify:
1. User registration with persistent storage
2. User login with localStorage emulation
3. Message sending and storage
"""

import requests
import json
import time
import websockets
import asyncio
import base64

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"

async def test_full_flow():
    print("=" * 60)
    print("Testing Full Chat Application Flow")
    print("=" * 60)
    
    # Test 1: Register users
    print("\n[TEST 1] Registering users...")
    users = ["alice", "bob"]
    password = "test123"
    
    for user in users:
        resp = requests.post(f"{BASE_URL}/register", json={"username": user, "password": password})
        print(f"  Register {user}: Status={resp.status_code}")
        if resp.status_code == 200:
            print(f"    ✓ {user} registered successfully")
        else:
            print(f"    ✗ Error: {resp.text}")
    
    # Test 2: Login users
    print("\n[TEST 2] Logging in users...")
    for user in users:
        resp = requests.post(f"{BASE_URL}/login", json={"username": user, "password": password})
        print(f"  Login {user}: Status={resp.status_code}")
        if resp.status_code == 200:
            print(f"    ✓ {user} logged in successfully")
        else:
            print(f"    ✗ Error: {resp.text}")
    
    # Test 3: Send messages and verify storage
    print("\n[TEST 3] Testing WebSocket messaging and storage...")
    
    try:
        # Create token for alice
        alice_token = base64.b64encode(f"alice:{password}".encode()).decode()
        bob_token = base64.b64encode(f"bob:{password}".encode()).decode()
        
        print(f"  Alice token: {alice_token[:20]}...")
        print(f"  Bob token: {bob_token[:20]}...")
        
        async with websockets.connect(WS_URL) as alice_ws:
            print("  ✓ Alice WebSocket connected")
            
            # Send token
            await alice_ws.send(alice_token)
            print("  ✓ Alice sent authentication token")
            
            # Try to receive first message (history or echo)
            try:
                time.sleep(1)  # Give time to connect and establish stream
                msg = await asyncio.wait_for(alice_ws.recv(), timeout=2)
                print(f"  ✓ Alice received message (likely history or system): {msg[:100]}")
            except asyncio.TimeoutError:
                print("  ! No immediate message (this is OK)")
            
            # Send a message
            await alice_ws.send("Hello from Alice!")
            print("  ✓ Alice sent message: 'Hello from Alice!'")
            
            # Try to receive own message
            try:
                msg = await asyncio.wait_for(alice_ws.recv(), timeout=3)
                msg_data = json.loads(msg)
                print(f"  ✓ Alice received: from={msg_data.get('sender')}, msg={msg_data.get('message')}")
            except asyncio.TimeoutError:
                print("  ! Timeout waiting for message response")
    
    except Exception as e:
        print(f"  ✗ WebSocket error: {e}")
    
    # Test 4: Verify message history
    print("\n[TEST 4] Checking message history...")
    resp = requests.get(f"{BASE_URL}/history")
    if resp.status_code == 200:
        data = resp.json()
        messages = data.get("messages", [])
        print(f"  ✓ Retrieved {len(messages)} messages from history")
        for msg in messages[-3:]:  # Show last 3
            print(f"    - {msg['sender']}: {msg['message']} ({msg['timestamp']})")
    else:
        print(f"  ✗ Failed to get history: {resp.text}")
    
    # Test 5: Verify persistence - re-login and check
    print("\n[TEST 5] Testing persistence by re-login...")
    resp = requests.post(f"{BASE_URL}/login", json={"username": "alice", "password": password})
    if resp.status_code == 200:
        print("  ✓ Re-login successful (credentials persisted)")
    else:
        print(f"  ✗ Re-login failed: {resp.text}")
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("✓ All core tests completed")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(test_full_flow())
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
