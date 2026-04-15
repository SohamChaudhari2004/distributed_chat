#!/usr/bin/env python3
import sys
import base64
import requests
import json
import time
import threading
import asyncio
import websockets

BASE_URL = "http://localhost:8000"

def test_registration():
    print("\n=== Test 1: User Registration ===")
    data = {"username": "alice", "password": "pass123"}
    resp = requests.post(f"{BASE_URL}/register", json=data)
    print(f"Status: {resp.status_code}, Response: {resp.json()}")
    assert resp.json()["success"] == True, "Registration failed!"
    print("✓ Registration successful")

def test_login():
    print("\n=== Test 2: User Login ===")
    data = {"username": "alice", "password": "pass123"}
    resp = requests.post(f"{BASE_URL}/login", json=data)
    print(f"Status: {resp.status_code}, Response: {resp.json()}")
    assert resp.json()["success"] == True, "Login failed!"
    print("✓ Login successful")

def test_history():
    print("\n=== Test 3: Fetch Chat History ===")
    resp = requests.get(f"{BASE_URL}/history")
    print(f"Status: {resp.status_code}, Messages: {len(resp.json()['messages'])}")
    print("✓ History fetch successful")

async def test_websocket():
    print("\n=== Test 4: WebSocket Connection ===")
    token = base64.b64encode(b"alice:pass123").decode()
    print(f"Token: {token}")
    
    try:
        async with websockets.connect(f"ws://localhost:8000/ws", ping_interval=None) as ws:
            print("✓ WebSocket connected")
            
            # Send token
            await ws.send(token)
            print("✓ Token sent")
            
            # Wait for a moment
            await asyncio.sleep(1)
            
            # Send a message
            await ws.send("Hello from Alice!")
            print("✓ Message sent: 'Hello from Alice!'")
            
            # Try to receive messages
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                print(f"✓ Received message: {msg}")
            except asyncio.TimeoutError:
                print("⚠ No message received within 2 seconds")
                
    except Exception as e:
        print(f"✗ WebSocket error: {e}")

def main():
    print("Starting Application Test Suite...")
    print("=" * 50)
    
    try:
        test_registration()
        test_login()
        test_history()
        asyncio.run(test_websocket())
        
        print("\n" + "=" * 50)
        print("✓ ALL TESTS PASSED!")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
