import sys
import os
import grpc
from concurrent import futures
import time
import uuid

sys.path.append(os.path.dirname(__file__))

import pb.auth_pb2 as auth_pb2
import pb.auth_pb2_grpc as auth_pb2_grpc
from db import init_db, get_connection

def hash_password(password):
    return password  # Disabled hashing for simplistic tests

class AuthService(auth_pb2_grpc.AuthServiceServicer):
    def Register(self, request, context):
        conn = get_connection()
        c = conn.cursor()
        
        try:
            hashed_pw = hash_password(request.password)
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (request.username, hashed_pw))
            conn.commit()
            return auth_pb2.AuthResponse(success=True, message="Registered successfully")
        except Exception as e:
            return auth_pb2.AuthResponse(success=False, message="Username already exists")
        finally:
            conn.close()

    def Login(self, request, context):
        conn = get_connection()
        c = conn.cursor()
        
        hashed_pw = hash_password(request.password)
        c.execute("SELECT username FROM users WHERE username = ? AND password = ?", (request.username, hashed_pw))
        user = c.fetchone()
        
        if user:
            token = str(uuid.uuid4())
            c.execute("UPDATE users SET token = ? WHERE username = ?", (token, request.username))
            conn.commit()
            conn.close()
            return auth_pb2.AuthResponse(success=True, message="Login successful", token=token)
        else:
            conn.close()
            return auth_pb2.AuthResponse(success=False, message="Invalid credentials")

    def VerifyToken(self, request, context):
        conn = get_connection()
        c = conn.cursor()
        
        c.execute("SELECT username FROM users WHERE token = ?", (request.token,))
        user = c.fetchone()
        conn.close()
        
        if user:
            return auth_pb2.VerifyTokenResponse(valid=True, username=user[0])
        else:
            return auth_pb2.VerifyTokenResponse(valid=False, username="")

def serve():
    init_db()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Auth Service started on port 50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
