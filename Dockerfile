FROM debian:bookworm
WORKDIR /app

RUN apt update && \
	apt install -y --no-install-recommends \
		gnupg && \
	echo "deb http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list && \
	apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 82B129927FA3303E && \
	apt update && \
	apt -y upgrade && \
	apt update && apt install -y --no-install-recommends \
        python3-pip \
        python3-picamera2 \
        gcc \
        python3-dev \
        build-essential \
        crossbuild-essential-arm64 \
        ffmpeg && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/cache/apt/archives/* && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /app/recordings

COPY ./pyproject.toml README.md ./
COPY ./src ./src
RUN pip3 install --break-system-packages --no-cache-dir .

CMD ["python3", "-m", "ld2410_securitycam.main"]
