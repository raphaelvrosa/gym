#!/bin/bash

python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. gym.proto

# protoc  --proto_path=/home/raphael/play/gym/gym/common/protobuf/ --python_out=. --python_grpc_out=. /home/raphael/play/gym/gym/common/protobuf/vnf_pp.proto
# protoc  --proto_path=/home/raphael/play/gym/gym/common/protobuf/ --python_out=. --python_grpc_out=. /home/raphael/play/gym/gym/common/protobuf/vnf_bd.proto
# protoc  --proto_path=/home/raphael/play/gym/gym/common/protobuf/ --python_out=. --python_grpc_out=. /home/raphael/play/gym/gym/common/protobuf/gym.proto

# Update in gym_grpc.py -> from gym.common.protobuf import gym_pb2
# Update in gym_pb2.py -> from gym.common.protobuf import vnf_bd_pb2 as vnf__bd__pb2 and from gym.common.protobuf import vnf_pp_pb2 as vnf__pp__pb2
