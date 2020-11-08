# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|

  config.ssh.insert_key = false

  config.vm.define "gym_virtualbox" do |gym_virtualbox|

    gym_virtualbox.vm.box = "ubuntu/focal64"    
    gym_virtualbox.vm.network :private_network, ip: "192.168.56.101"
    gym_virtualbox.vm.hostname = "gym"
    
    gym_virtualbox.vm.provider "virtualbox" do |vb|
      vb.name = "gym"
      opts = ["modifyvm", :id, "--natdnshostresolver1", "on"]
      vb.customize opts
      vb.cpus = 2
      vb.memory = "2048"
    end

    gym_virtualbox.vm.synced_folder ".", "/home/gym", mount_options: ["dmode=775"]
    gym_virtualbox.vm.provision :shell, inline: "apt update && apt install -y make"
    gym_virtualbox.vm.provision :shell, inline: "cd /home/gym && make install"

  end


  config.vm.define "gym_libvirt" do |gym_libvirt|
 
    gym_libvirt.vm.box = "generic/ubuntu2004"
    gym_libvirt.vm.hostname = "gym"

    gym_libvirt.vm.provider "libvirt" do |libvirt|
      libvirt.cpus = 2
      libvirt.memory = 2048
    end

    gym_libvirt.vm.network :private_network, ip: "192.168.121.101"


    gym_libvirt.vm.synced_folder ".", "/home/gym", mount_options: ["dmode=775"]
    gym_libvirt.vm.provision :shell, inline: "apt update && apt install -y make"
    gym_libvirt.vm.provision :shell, inline: "cd /home/gym && make install"

  end

end