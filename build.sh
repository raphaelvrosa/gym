#!/usr/bin/env bash

sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt -qq update

sudo apt install docker-ce python3-setuptools python3-dev python3-pip byobu

sudo python3 setup.py install

sudo docker build -t raphaelvrosa/gym:latest .