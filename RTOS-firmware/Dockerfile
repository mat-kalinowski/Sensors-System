FROM ubuntu:18.04

#ADD https://dl.espressif.com/dl/xtensa-lx106-elf-linux64-1.22.0-100-ge567ec7-5.2.0.tar.gz /tools
COPY xtensa-lx106-elf-linux64-1.22.0-100-ge567ec7-5.2.0.tar.gz /tools
RUN mkdir -p /toolchain \
     && tar -xzf /tools -C /toolchain/

FROM ubuntu:18.04

COPY --from=0 /toolchain .
ENV PATH /xtensa-lx106-elf/bin:$PATH
ENV IDF_PATH /opt/sdk

RUN apt-get update \
     && apt-get -y install python-pip gcc git wget make libncurses-dev flex bison gperf python python-serial \ 
     && mkdir -p /opt 

CMD /usr/bin/python -m pip install --user -r /opt/sdk/requirements.txt
