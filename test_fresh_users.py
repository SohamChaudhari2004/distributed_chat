import asyncio
import websockets
import json
import base64
import httpx

async def test_fresh_users():
    """Test with fresh user registration"""
    async with httpx.AsyncClient() as client:
        # Clean start - register new users
        print("=== Registering Users ===")
        r = await client.post("http://localhost:8000/register", 
            json={"username": "fresh_alice", "password": "pass123"})
        print(f"Register Alice: {r.json()}")
        
        r = await client.post("http://localhost:8000/register", 
            json={"username": "fresh_bob", "password": "pass456"})
        print(f"Register Bob: {r.json()}")
        
        # Verify login works
        print("\n=== Verifying Login ===")
        r = await client.post("http://localhost:8000/login", 
            json={"username": "fresh_alice", "password": "pass123"})
        print(f"Login Alice: {r.json()}")
        
        r = await client.post("http://localhost:8000/login", 
            json={"username": "fresh_bob", "password": "pass456"})
        print(f"Login Bob: {r.json()}")

    # Now test WebSocket connections
    token_alice = base64.b64encode(b"fresh_alice:pass123").decode()
    token_bob = base64.b64encode(b"fresh_bob:pass456").decode()
    
    print("\n=== Opening WebSocket Connections ===")
    ws_alice = await websockets.connect("ws://localhost:8000/ws")
    await ws_alice.send(token_alice)
    print(f"[Alice] Connected and sent token")
    
    await asyncio.sleep(0.2)
    
    ws_bob = await websockets.connect("ws://localhost:8000/ws")
    await ws_bob.send(token_bob)
    print(f"[Bob] Connected and sent token")
    
    await asyncio.sleep(0.5)
    
    try:
        print("\n=== Alice sends message ===")
        await ws_alice.send("Hi from Alice")
        print(f"[Alice] Sent: 'Hi from Alice'")
        
        # Try to receive on Alice's connection
        try:
            msg = await asyncio.wait_for(ws_alice.recv(), timeout=2)
            alice_msg = json.loads(msg)
            print(f"[Alice] Received: {alice_msg['message']} from {alice_msg['sender']}")
        except asyncio.TimeoutError:
            print(f"[Alice] Timeout waiting for message")
        
        await asyncio.sleep(0.3)
        
        # Check if Bob received Alice's message
        try:
            msg = await asyncio.wait_for(ws_bob.recv(), timeout=1)
            bob_received = json.loads(msg)
            print(f"[Bob] Received Alice's message: {bob_received['message']}")
        except asyncio.TimeoutError:
            print(f"[Bob] Did not receive Alice's message")
        
        print("\n=== Bob sends message ===")
        await ws_bob.send("Hi from Bob")
        print(f"[Bob] Sent: 'Hi from Bob'")
        
        # Try to receive on Bob's connection
        try:
            msg = await asyncio.wait_for(ws_bob.recv(), timeout=2)
            bob_msg = json.loads(msg)
            print(f"[Bob] Received: {bob_msg['message']} from {bob_msg['sender']}")
        except asyncio.TimeoutError:
            print(f"[Bob] Timeout waiting for own message")
        
        await asyncio.sleep(0.3)
        
        # Check if Alice received Bob's message
        try:
            msg = await asyncio.wait_for(ws_alice.recv(), timeout=1)
            alice_received = json.loads(msg)
            print(f"[Alice] Received Bob's message: {alice_received['message']}")
        except asyncio.TimeoutError:
            print(f"[Alice] Did not receive Bob's message")
            
    finally:
        await ws_alice.close()
        await ws_bob.close()
        print("\n✓ Test completed")

if __name__ == "__main__":
    asyncio.run(test_fresh_users())
