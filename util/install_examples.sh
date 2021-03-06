echo "This scripts clones and builds the images needed for the gym test case 1, 2 and 3"
echo "And download pcap files needed for test case 3"

cd ..
make docker-build
cd - 

git clone https://github.com/raphaelvrosa/gym-vnfs

cd gym-vnfs

sudo chmod +x build.sh

sudo ./build.sh

echo "Downloading pcap files for test case 3"
wget https://s3.amazonaws.com/tcpreplay-pcap-files/smallFlows.pcap 
wget https://s3.amazonaws.com/tcpreplay-pcap-files/bigFlows.pcap

sudo mkdir -p /mnt/pcaps
sudo mv smallFlows.pcap /mnt/pcaps/
sudo mv bigFlows.pcap /mnt/pcaps/

echo "Added pcap files smallFlows.pcap and bigFlows.pcap to /mnt/pcaps/ folder"

echo "Installing Containernet"

sudo apt-get install ansible git aptitude
git clone https://github.com/raphaelvrosa/containernet.git
cd containernet/ansible
sudo ansible-playbook -i "localhost," -c local install.yml
cd -

# sudo apt-get install mininet
# git clone https://github.com/raphaelvrosa/containernet.git
# cd containernet
# sudo python3.8 setup.py install
# cd -