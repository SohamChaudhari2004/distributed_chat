import sys
import os
import grpc
from concurrent import futures
import time
import threading
import json
import redis
from contextlib import contextmanager

sys.path.append(os.path.dirname(__file__))

import pb.chat_pb2 as chat_pb2
import pb.chat_pb2_grpc as chat_pb2_grpc
import pb.auth_pb2 as auth_pb2
import pb.auth_pb2_grpc as auth_pb2_grpc
import pb.store_pb2 as store_pb2
import pb.store_pb2_grpc as store_pb2_grpc

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
STORE_HOST = os.environ.get("STORE_HOST", "localhost:50052")
AUTH_HOST = os.environ.get("AUTH_HOST", "localhost:50051")

class ChatService(chat_pb2_grpc.ChatServiceServicer):
    def __init__(self):
        self.clients = {}  # user_id -> Queue/Stream
        self.lock = threading.Lock()
        
        # Redis setup
        try:
            self.redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe('chat_channel')
            self.redis_available = True
            
            # Start redis listener thread
            self.redis_thread = threading.Thread(target=self.listen_redis, daemon=True)
            self.redis_thread.start()
        except Exception as e:
            print("Redis not available, falling back to local broadcast only.")
            self.redis_available = False

    def listen_redis(self):
        try:
            for message in self.pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    self.local_broadcast(data['sender'], data['message'], data['timestamp'])
        except Exception as e:
            print(f"Redis listener error: {e}")

    def local_broadcast(self, sender, message, timestamp):
        chat_msg = chat_pb2.ChatMessage(sender=sender, message=message, timestamp=timestamp)
        with self.lock:
            for q in self.clients.values():
                try:
                    q.append(chat_msg)
                except Exception:
                    pass

    def verify_auth(self, context):
        try:
            metadata = dict(context.invocation_metadata())
        except Exception as e:
            print(f"DEBUG: Failed to get metadata: {e}")
            return None
            
        print(f"DEBUG: All metadata keys: {list(metadata.keys())}")
        print(f"DEBUG: Full metadata: {metadata}")
        
        token = metadata.get('authorization', '')
        print(f"DEBUG: Token received: {token}")
        
        if not token:
            print("DEBUG: No token found in metadata")
            return None
            
        import base64
        
        # Handle both 'Basic {base64}' and raw base64 formats
        if token.startswith('Basic '):
            token_data = token[6:]
        else:
            token_data = token
            
        try:
            decoded = base64.b64decode(token_data).decode()
            username, password = decoded.split(':', 1)
            print(f"DEBUG: Decoded token - username: {username}, password: {password}")
        except Exception as e:
            print(f"DEBUG: base64 decode error: {e}, token_data: {token_data}")
            return None
            
        with grpc.insecure_channel(AUTH_HOST) as channel:
            stub = auth_pb2_grpc.AuthServiceStub(channel)
            try:
                response = stub.Login(auth_pb2.LoginRequest(username=username, password=password))
                print(f"DEBUG: Auth response - success: {response.success}, message: {response.message}")
                if response.success:
                    return username
                else:
                    print(f"DEBUG: Login failed for user {username}")
            except Exception as e:
                print(f"DEBUG: Auth service error: {e}")
        return None

    def ChatStream(self, request_iterator, context):
        username = self.verify_auth(context)
        if not username:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid credentials")
            return

        import queue
        q = []
        
        with self.lock:
            self.clients[username] = q

        def handle_incoming():
            try:
                for request in request_iterator:
                    msg_data = {
                        "sender": username,
                        "message": request.message,
                        "timestamp": str(int(time.time()))
                    }
                    
                    # Save to store
                    try:
                        with grpc.insecure_channel(STORE_HOST) as channel:
                            stub = store_pb2_grpc.StoreServiceStub(channel)
                            stub.SaveMessage(store_pb2.SaveMessageRequest(
                                sender=msg_data["sender"],
                                message=msg_data["message"],
                                timestamp=msg_data["timestamp"]
                            ))
                    except Exception as e:
                        print("Store service error:", e)
                    
                    if self.redis_available:
                        try:
                            self.redis_client.publish('chat_channel', json.dumps(msg_data))
                        except:
                            self.local_broadcast(msg_data["sender"], msg_data["message"], msg_data["timestamp"])
                    else:
                        self.local_broadcast(msg_data["sender"], msg_data["message"], msg_data["timestamp"])
            except grpc.RpcError as e:
                # Client disconnected or stream closed
                pass
            except Exception as e:
                print("Incoming thread error:", e)

        incoming_thread = threading.Thread(target=handle_incoming, daemon=True)
        incoming_thread.start()

        try:
            while context.is_active():
                if q:
                    with self.lock:
                        msg = q.pop(0)
                    yield msg
                else:
                    time.sleep(0.1)
        finally:
            with self.lock:
                if username in self.clients:
                    del self.clients[username]

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(ChatService(), server)
    server.add_insecure_port('[::]:50053')
    server.start()
    print("Chat Service started on port 50053")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
