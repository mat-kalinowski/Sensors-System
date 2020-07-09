FROM python:3

WORKDIR /root

COPY requirements.txt ./
RUN pip install -r requirements.txt

CMD ["python", "-u", "./dummy-firmware.py"]
