FROM debian:bullseye

RUN apt-get update && apt-get install -y tmate netcat

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 10000
CMD ["/start.sh"]
