import os
import subprocess

import sys

def compile_protos():
    protos_dir = os.path.join(os.path.dirname(__file__), 'protos')
    
    # We will copy protos into each service's directory (or just use one shared path)
    services = ['auth_service', 'store_service', 'chat_service', 'gateway']
    
    
    for service in services:
        out_dir = os.path.join(os.path.dirname(__file__), 'services', service, 'pb')
        os.makedirs(out_dir, exist_ok=True)
        # also create __init__.py
        with open(os.path.join(out_dir, "__init__.py"), "w") as f:
            pass
            
        subprocess.run([
            sys.executable, '-m', 'grpc_tools.protoc',
            f'-I{protos_dir}',
            f'--python_out={out_dir}',
            f'--grpc_python_out={out_dir}',
            os.path.join(protos_dir, 'auth.proto'),
            os.path.join(protos_dir, 'store.proto'),
            os.path.join(protos_dir, 'chat.proto')
        ], check=True)
        
        # Patch the generated files to use absolute imports
        for filename in os.listdir(out_dir):
            if filename.endswith("_pb2_grpc.py"):
                filepath = os.path.join(out_dir, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                content = content.replace('import auth_pb2 as auth__pb2', 'from . import auth_pb2 as auth__pb2')
                content = content.replace('import store_pb2 as store__pb2', 'from . import store_pb2 as store__pb2')
                content = content.replace('import chat_pb2 as chat__pb2', 'from . import chat_pb2 as chat__pb2')
                with open(filepath, 'w') as f:
                    f.write(content)

if __name__ == "__main__":
    compile_protos()