import sys
import os
import grpc
from concurrent import futures
import time

sys.path.append(os.path.dirname(__file__))

import pb.store_pb2 as store_pb2
import pb.store_pb2_grpc as store_pb2_grpc
from db import init_db, get_connection

class StoreService(store_pb2_grpc.StoreServiceServicer):
    def SaveMessage(self, request, context):
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)",
                      (request.sender, request.message, request.timestamp))
            conn.commit()
            return store_pb2.SaveMessageResponse(success=True)
        except Exception as e:
            return store_pb2.SaveMessageResponse(success=False)
        finally:
            conn.close()

    def GetHistory(self, request, context):
        conn = get_connection()
        c = conn.cursor()
        limit = request.limit if request.limit > 0 else 50
        c.execute("SELECT sender, message, timestamp FROM messages ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        
        # Return in chronological order
        messages = [store_pb2.ChatMessage(sender=r[0], message=r[1], timestamp=r[2]) for r in reversed(rows)]
        return store_pb2.GetHistoryResponse(messages=messages)

def serve():
    init_db()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    store_pb2_grpc.add_StoreServiceServicer_to_server(StoreService(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    print("Store Service started on port 50052")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
