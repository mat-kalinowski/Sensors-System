docker build -t sensors-service-cont .
docker run -v /home/kalinek/Desktop/PPM/sensors-service/src:/root/ --network=host sensors-service-cont 
