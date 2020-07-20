# Simple script to build esp docker image and run the container
#
# INPUT ARGUMENTS
#
# --rebuild  - rebuilds docker image
# --sources <src_path> - provides path to ESP_RTOS_SDK source code mounted in /opt/sdk
# --project <project_path> - provides path to own project mounted in /root

if [ -z "$1" ]; then
	echo "Not enough input arguments !"
	
	echo "--rebuild  - rebuilds docker image"
	echo "--sources <src_path> - provides path to ESP_RTOS_SDK source code mounted in /opt/sdk"
	echo "--project <project_path> - provides path to own project mounted in /root"

	exit
fi

cmd="docker run"

for ((i=0; i<=$#; i++)); do
	next=$(($i + 1))
	next=${!next}

	if [ "${!i}" = "--rebuild" ]; then
		docker build . -t esp:latest
		if [ $? -ne 0 ]; then echo "Docker build failed !"; exit; fi

	elif [ "${!i}" = "--sources" ] && [[ ! -z "$next" ]]; then
		cmd="${cmd} -v ${next}:/opt/sdk"

        elif [ "${!i}" = "--project" ] && [[ ! -z "$next" ]]; then
		cmd="${cmd} -v ${next}:/root"
	fi

done

tty_dev=$(dmesg | grep cp210x | grep ttyUSB[0-9]* -o | tail -n1)

if [[ ${tty_dev} != "" ]]; then
	cmd="${cmd} --device=/dev/$tty_dev"
fi

cmd="${cmd} -ti esp:latest /bin/sh"


eval $cmd
