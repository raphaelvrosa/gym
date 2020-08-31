#!/bin/bash

if [ "$EUID" != "0" ]; then
    echo "Sorry dude! You must be root to run this script."
    exit 1
fi

SCRIPT_NAME='Gym Test'
COMMAND=$1
TEST=$2

echo_bold() {
    echo -e "\033[1m${1}\033[0m"
}

kill_process_tree() {
    top=$1
    pid=$2

    children=`ps -o pid --no-headers --ppid ${pid}`

    for child in $children
    do
        kill_process_tree 0 $child
    done

    if [ $top -eq 0 ]; then
        kill -9 $pid &> /dev/null
    fi
}

reset() {
    init=$1;
    if [ $init -eq 1 ]; then
        echo_bold "-> Resetting $SCRIPT_NAME";
    else
        echo_bold "-> Stopping child processes...";
        kill_process_tree 1 $$
    fi

    byobu kill-session -t "gym"

    GYMDOCKERS=`docker ps -q -f name=gym`
    if [ -n "$GYMDOCKERS" ]
    then
        echo_bold "Removing containers $GYMDOCKERS"
        docker stop -t0 $GYMDOCKERS
        docker rm $GYMDOCKERS
    fi

    GYMDOCKERNET=`docker network ls -q -f name=gym`
    if [ -n "$GYMDOCKERNET" ]
    then
        echo_bold "Removing gym docker network $GYMDOCKERNET"
        docker network rm gym
    fi
    
    
    PLAYERPID=`ps -o pid --no-headers -C gym-player`
    MONPID=`ps -o pid --no-headers -C gym-monitor`
    
    if [ -n "$PLAYERPID" ]
    then
        #echo "$PLAYERPID is running"
        kill -9 $PLAYERPID &> /dev/null
    fi
    
    if [ -n "$MONPID" ]
    then
        #echo "$MONPID is running"
        kill -9 $MONPID &> /dev/null
    fi

    if [ -f ./vnf-br.json ]; then
        echo "Cleaning vnf-br.json"
        rm ./vnf-br.json
    fi

    shopt -s nullglob dotglob     # To include hidden files

    echo "Cleaning logs"
    files=(./logs/*)
    if [ ${#files[@]} -gt 0 ]; then
        rm ./logs/*
    fi 

    echo "Cleaning csv files"
    files=(./csv/*)
    if [ ${#files[@]} -gt 0 ]; then
        rm ./csv/*
    fi 

    mn -c
}


case "$COMMAND" in
    start)

        if [ -z "$TEST" ]
        then 
            echo_bold "Please, define test case: [ 0 | 1 | 2 | 3 ]"
            exit 1
        fi

        echo_bold "-> Start: $SCRIPT_NAME Layout Case: $TEST"

        if [ ! -d "./logs" ]; then
            mkdir ./logs
        fi
        
        if [ ! -d "./csv" ]; then
            mkdir ./csv
        fi 

        case "$TEST" in
            0)
                echo_bold "-> Starting Agents"
                byobu new-session -d -s "gym" "gym-agent --uuid agent-1 --address 127.0.0.1:8985 --debug"
                byobu new-window "gym-agent --uuid agent-2 --address 127.0.0.1:8986 --debug"

                sleep 1
                echo_bold "-> Starting Manager"
                byobu new-window "gym-manager --uuid manager --address 127.0.0.1:8987 --contacts agent/127.0.0.1:8985 agent/127.0.0.1:8986 --debug"

                sleep 1
                echo_bold "-> Starting Player"
                byobu new-window "gym-player --uuid player --address 172.17.0.1:8990 --contacts manager/127.0.0.1:8987 --debug"

                sleep 2
            ;;
            4)
                echo_bold "-> Creating docker gym network "
                docker network create --subnet=172.21.0.0/24 gym

                echo_bold "-> Starting SSH Containers"
                docker run --name gym-ssh-agent1 -d -e "USERNAME=gym" -e "PASSWORD=R0cks.4l1v3" -e "SUDOER=nopasswd" --net gym --ip 172.21.0.10 vnf/sshd:latest
                docker run --name gym-ssh-agent2 -d -e "USERNAME=gym" -e "PASSWORD=R0cks.4l1v3" -e "SUDOER=nopasswd" --net gym --ip 172.21.0.20 vnf/sshd:latest
                docker run --name gym-ssh-manager -d -e "USERNAME=gym" -e "PASSWORD=R0cks.4l1v3" -e "SUDOER=nopasswd" --net gym --ip 172.21.0.30 vnf/sshd:latest
                
                echo_bold "-> Starting Infra"
                byobu new-session -d -s "gym" "gym-infra --uuid infra --address 172.17.0.1:9090 --debug > logs/infra.log 2>&1"

                sleep 1
                echo_bold "-> Starting Player"
                byobu new-window "gym-player --uuid player --address 172.17.0.1:8990 --debug > logs/player.log 2>&1"
            ;;
            *)
                echo_bold "-> Starting Infra"
                byobu new-session -d -s "gym" "gym-infra --uuid infra --address 172.17.0.1:9090 --debug > logs/infra.log 2>&1"

                sleep 1
                echo_bold "-> Starting Player"
                byobu new-window "gym-player --uuid player --address 172.17.0.1:8990 --debug > logs/player.log 2>&1"
            ;;
        esac

        sleep 2
        echo_bold "-> Running Examples - Deploying Layout and waiting for Result"
       
        examples="/usr/bin/python ./examples.py --test ${TEST}"
        exec ${examples}

        echo_bold "-> Check the logs at: ./logs/*.log"
        echo_bold "-> Run the stop option to clean the test results/logs"
        ;;

    stop)
        echo_bold "-> Stop"
        reset 1
        ;;

    *)
        echo_bold "Usage: $0 ( start | stop ) [ 0 | 1 ]"
        echo_bold "=> Start - Run a test case specified."
        echo_bold "=> Stop - Clean logs/results and operations performed by test case"
        echo_bold "# Test Cases:"
        echo_bold " - 0: Simple two agent processes exercising ping/iperf3"
        echo_bold " - 1: Uses containernet to run two agents exchanging iperf3 and ping through a dummy VNF"
        echo_bold " - 2: Uses containernet to run two agents exchanging iperf3 and ping through a dummy VNF, while monitoring it"
        echo_bold " - 3: Uses containernet to run two agents to tcpreplay pcaps in a Suricata VNF, while monitoring it inside and outside"
        echo_bold " - 4: Uses containernet to run scenario 0 - agents/manager via ssh plugin"
        exit 1
esac