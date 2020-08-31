FROM python:3.8

ENV DEBIAN_FRONTEND noninteractive

RUN apt update \
	&& apt install -y tcpdump net-tools libpcap-dev build-essential wget git \
					inetutils-ping iperf3 build-essential bc libpcap-dev iproute2

RUN wget -c "https://downloads.sourceforge.net/project/tcpreplay/tcpreplay/4.2.6/tcpreplay-4.2.6.tar.gz?r=https%3A%2F%2Fsourceforge.net%2Fprojects%2Ftcpreplay%2F&ts=1495545608&use_mirror=excellmedia" -O "tcpreplay_426.tar.gz"
RUN tar xzf tcpreplay_426.tar.gz && cd tcpreplay-4.2.6/ && ./configure && make && make install && cd -

# RUN apt install -y unzip
# RUN wget -c https://github.com/protocolbuffers/protobuf/releases/download/v3.11.2/protoc-3.11.2-linux-x86_64.zip -O protoc-3.11.2-linux-x86_64.zip
# RUN mkdir protoc && mv protoc-3.11.2-linux-x86_64.zip protoc/ && cd protoc && unzip protoc-3.11.2-linux-x86_64.zip && cp ./bin/protoc /usr/local/bin/ && cp -R ./include/google /usr/local/include/

# RUN git clone https://github.com/protocolbuffers/protobuf \
# 	&& cd protobuf/python \
# 	&& python3.8 setup.py install \
# 	&& cd -

RUN python3.8 -m pip install \
	"asyncio<=3.4.3" \
	"protobuf<=3.12.2" \
	"grpclib<=0.3.2" \
	"grpcio-tools<=1.31.0" \
	"pyang<=2.3.2" \
	"pyangbind<=0.8.1" \
	"jinja2<=2.10.1" \
	"pyyaml<=5.3.1" \
	"pandas<=1.1.0" \
	"docker<=4.1.0" \
	"psutil<=5.7.0" \
	"paramiko<=2.6.0" \
	"scp<=0.13.2"  \
	"flatten_json"
	
RUN mkdir -p gym/gym
COPY * /gym/
COPY gym /gym/gym/

WORKDIR /gym
RUN python3.8 setup.py install 
