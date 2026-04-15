import asyncio
import websockets
import json
import base64
import time

async def test_two_users_sequential():
    """Test with explicit sequencing and delays between operations"""
    import httpx
    
    async with httpx.AsyncClient() as client:
        # Register and login both users
        await client.post("http://localhost:8000/register", json={"username": "alice", "password": "alice123"})
        await client.post("http://localhost:8000/register", json={"username": "bob", "password": "bob123"})
        
        r1 = await client.post("http://localhost:8000/login", json={"username": "alice", "password": "alice123"})
        r2 = await client.post("http://localhost:8000/login", json={"username": "bob", "password": "bob123"})
        
        print(f"Alice login: {r1.json()}")
        print(f"Bob login: {r2.json()}\n")

    # Create long-lived WebSocket connections
    print("=== PHASE 1: Opening WebSocket Connections ===")
    token_alice = base64.b64encode(b"alice:alice123").decode()
    token_bob = base64.b64encode(b"bob:bob123").decode()
    
    ws_alice = await websockets.connect("ws://localhost:8000/ws")
    await ws_alice.send(token_alice)
    print(f"[Alice] Connected and sent token")
    
    ws_bob = await websockets.connect("ws://localhost:8000/ws")
    await ws_bob.send(token_bob)
    print(f"[Bob] Connected and sent token\n")
    
    try:
        print("=== PHASE 2: Alice sends first message ===")
        await ws_alice.send("Message 1 from Alice")
        print(f"[Alice] Sent: 'Message 1 from Alice'")
        
        # Wait for Alice to receive her own message
        await asyncio.sleep(0.2)
        msg = await asyncio.wait_for(ws_alice.recv(), timeout=2)
        print(f"[Alice] Received: {json.loads(msg)['message']}")
        
        # Check if Bob also received Alice's message
        await asyncio.sleep(0.2)
        try:
            msg = await asyncio.wait_for(ws_bob.recv(), timeout=1)
            bob_received = json.loads(msg)['message']
            print(f"[Bob] Received: {bob_received}")
        except asyncio.TimeoutError:
            print(f"[Bob] Timeout (no message yet)\n")
        
        print("\n=== PHASE 3: Bob sends first message ===")
        await ws_bob.send("Message 1 from Bob")
        print(f"[Bob] Sent: 'Message 1 from Bob'")
        
        # Wait for Bob to receive his own message
        await asyncio.sleep(0.2)
        msg = await asyncio.wait_for(ws_bob.recv(), timeout=2)
        bob_msg = json.loads(msg)
        print(f"[Bob] Received: {bob_msg['message']} (from {bob_msg['sender']})")
        
        # Check if Alice also received Bob's message
        await asyncio.sleep(0.2)
        try:
            msg = await asyncio.wait_for(ws_alice.recv(), timeout=1)
            alice_msg = json.loads(msg)
            print(f"[Alice] Received: {alice_msg['message']} (from {alice_msg['sender']})\n")
        except asyncio.TimeoutError:
            print(f"[Alice] Timeout (no message yet)\n")
        
        print("=== PHASE 4: Test concurrent messages ===")
        # Send two messages at almost the same time
        await ws_alice.send("Message 2 from Alice")
        print(f"[Alice] Sent: 'Message 2 from Alice'")
        
        await asyncio.sleep(0.1)
        
        await ws_bob.send("Message 2 from Bob")
        print(f"[Bob] Sent: 'Message 2 from Bob'")
        
        # Each should receive both messages
        await asyncio.sleep(0.5)
        
        print(f"[Alice] Messages in buffer:")
        for i in range(2):
            try:
                msg = json.loads(await asyncio.wait_for(ws_alice.recv(), timeout=1))
                print(f"  - {msg['message']} (from {msg['sender']})")
            except asyncio.TimeoutError:
                print(f"  - [Timeout]")
                
        print(f"[Bob] Messages in buffer:")
        for i in range(2):
            try:
                msg = json.loads(await asyncio.wait_for(ws_bob.recv(), timeout=1))
                print(f"  - {msg['message']} (from {msg['sender']})")
            except asyncio.TimeoutError:
                print(f"  - [Timeout]")
                
    finally:
        await ws_alice.close()
        await ws_bob.close()
        print("\n✓ Test completed")

if __name__ == "__main__":
    asyncio.run(test_two_users_sequential())
