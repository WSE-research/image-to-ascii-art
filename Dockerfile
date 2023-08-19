FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -yq bash curl wget ca-certificates python3 python3-pip 

RUN echo 'deb [trusted=yes] https://apt.fury.io/ascii-image-converter/ /' | tee /etc/apt/sources.list.d/ascii-image-converter.list
RUN echo 'deb [trusted=yes] http://ppa.launchpad.net/inkscape.dev/stable-1.1/ubuntu focal InRelease' | tee /etc/apt/sources.list.d/inkscape.list
RUN apt-get update && apt-get install -yq inkscape ascii-image-converter 

# an acceptable version of inkscape would be >= 1.1
RUN /usr/bin/inkscape -V
COPY . /app
WORKDIR /app
RUN python3 -m pip install --upgrade pip 
RUN python3 -m pip install -r requirements.txt

ENV UPLOAD_DIRECTORY=/app/working_directory
ENV force_color_prompt=yes
ENV COLORTERM=24bit

EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
SHELL ["/bin/bash", "-c"]
ENTRYPOINT ["streamlit", "run", "image-to-ascii-art-converter-web-ui.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.maxUploadSize=1"]

