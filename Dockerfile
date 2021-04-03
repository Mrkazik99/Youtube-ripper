FROM python:3.9-slim
LABEL maintainer="David Sn <divad.nnamtdeis@gmail.com>"

# Install required ffmpeg
RUN apt-get update && \
    apt-get install --no-install-recommends -y ffmpeg && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app
ADD requirements.txt .
RUN pip install -r requirements.txt
ADD . ./
ENTRYPOINT [ "python", "main.py" ]
