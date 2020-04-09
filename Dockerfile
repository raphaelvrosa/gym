FROM ubuntu:18.04

RUN apt update \
	&& apt install -y tcpdump net-tools libpcap-dev build-essential wget git \
					inetutils-ping iperf3 build-essential bc libpcap-dev iperf iproute2

RUN cp /usr/bin/iperf /usr/sbin/iperf

RUN wget -c "https://downloads.sourceforge.net/project/tcpreplay/tcpreplay/4.2.6/tcpreplay-4.2.6.tar.gz?r=https%3A%2F%2Fsourceforge.net%2Fprojects%2Ftcpreplay%2F&ts=1495545608&use_mirror=excellmedia" -O "tcpreplay_426.tar.gz"
RUN tar xzf tcpreplay_426.tar.gz && cd tcpreplay-4.2.6/ && ./configure && make && make install && cd -

RUN apt update \
	&& apt install -y software-properties-common \
	&& add-apt-repository ppa:deadsnakes/ppa \
	&& apt update \
	&& apt install -y python3.7 python3.7-dev python3-pip

RUN apt install -y unzip
RUN wget -c https://github.com/protocolbuffers/protobuf/releases/download/v3.11.2/protoc-3.11.2-linux-x86_64.zip -O protoc-3.11.2-linux-x86_64.zip
RUN mkdir protoc && mv protoc-3.11.2-linux-x86_64.zip protoc/ && cd protoc && unzip protoc-3.11.2-linux-x86_64.zip && cp ./bin/protoc /usr/local/bin/ && cp -R ./include/google /usr/local/include/

RUN git clone https://github.com/protocolbuffers/protobuf \
	&& cd protobuf/python \
	&& python3.7 setup.py install \
	&& cd -

RUN /usr/bin/python3.7 -m pip install asyncio protobuf grpclib grpcio-tools pyang pyangbind jinja2 pandas docker-py psutil flatten_json pyyaml paramiko

RUN mkdir -p gym/gym
COPY * /gym/
COPY gym /gym/gym/

WORKDIR /gym
RUN python3.7 setup.py install 

RUN export PATH=$PATH:~/.local/bin
