import asyncio
import websockets
import json
import base64

async def test_two_users():
    # Register and login two users
    import httpx
    
    async with httpx.AsyncClient() as client:
        # Register user1
        await client.post("http://localhost:8000/register", json={"username": "user1", "password": "pass1"})
        await client.post("http://localhost:8000/register", json={"username": "user2", "password": "pass2"})
        
        # Login to get tokens (though we're using basic auth)
        r1 = await client.post("http://localhost:8000/login", json={"username": "user1", "password": "pass1"})
        r2 = await client.post("http://localhost:8000/login", json={"username": "user2", "password": "pass2"})
        
        print(f"User1 login: {r1.json()}")
        print(f"User2 login: {r2.json()}")

    # Connect both users via WebSocket
    token1 = base64.b64encode(b"user1:pass1").decode()
    token2 = base64.b64encode(b"user2:pass2").decode()
    
    async with websockets.connect("ws://localhost:8000/ws") as ws1:
        await ws1.send(token1)
        print(f"[User1] Connected and sent token")
        
        async with websockets.connect("ws://localhost:8000/ws") as ws2:
            await ws2.send(token2)
            print(f"[User2] Connected and sent token")
            
            # User 1 sends a message
            await asyncio.sleep(0.5)
            await ws1.send("Hello from User1")
            print("[User1] Sent: 'Hello from User1'")
            
            # Try to receive on both
            try:
                msg1 = await asyncio.wait_for(ws1.recv(), timeout=2)
                print(f"[User1] Received: {msg1}")
            except asyncio.TimeoutError:
                print("[User1] Timeout waiting for message")
            
            # User 2 tries to send a message
            await asyncio.sleep(0.5)
            try:
                print("[User2] Attempting to send message...")
                await asyncio.wait_for(ws2.send("Hello from User2"), timeout=2)
                print("[User2] Sent: 'Hello from User2'")
                
                msg2 = await asyncio.wait_for(ws2.recv(), timeout=2)
                print(f"[User2] Received: {msg2}")
            except asyncio.TimeoutError:
                print("[User2] Timeout - cannot send or receive!")
            except Exception as e:
                print(f"[User2] Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_two_users())
