#!/bin/bash

python3 -m grpc_tools.protoc -I. --python_out=. --grpclib_python_out=. vnf_bd.proto
python3 -m grpc_tools.protoc -I. --python_out=. --grpclib_python_out=. vnf_pp.proto
python3 -m grpc_tools.protoc -I. --python_out=. --grpclib_python_out=. gym.proto

# Update in gym_grpc.py -> from gym.common.protobuf import gym_pb2
# Update in gym_pb2.py -> from gym.common.protobuf import vnf_bd_pb2 as vnf__bd__pb2 and from gym.common.protobuf import vnf_pp_pb2 as vnf__pp__pb2
