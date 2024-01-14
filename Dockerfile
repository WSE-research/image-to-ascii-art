FROM ubuntu:22.04

# parameters that might be provided at runtime by using the --env option
ENV REPLACE_INDEX_HTML_CONTENT="false"
ENV SERVER_PORT=8501
ENV SERVER_MAXUPLOADSIZE=4
ENV CANONICAL_URL=""
ENV ADDITIONAL_HTML_HEAD_CONTENT=""

# install dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -yq bash curl wget ca-certificates python3 python3-pip 

RUN echo 'deb [trusted=yes] https://apt.fury.io/ascii-image-converter/ /' | tee /etc/apt/sources.list.d/ascii-image-converter.list
RUN echo 'deb [trusted=yes] http://ppa.launchpad.net/inkscape.dev/stable-1.1/ubuntu focal InRelease' | tee /etc/apt/sources.list.d/inkscape.list
RUN apt-get update && apt-get install -yq inkscape ascii-image-converter 

# an acceptable version of inkscape would be >= 1.1
RUN /usr/bin/inkscape -V

# copy the application files
COPY . /app
WORKDIR /app

# install python dependencies
RUN python3 --version
RUN python3 -m pip install --upgrade pip 
RUN python3 -m pip install -r requirements.txt

# set environment variables for the required colorization of the terminal
ENV force_color_prompt=yes
ENV COLORTERM=24bit

# set environment variables for the application
ENV UPLOAD_DIRECTORY=/app/working_directory

# do a dry run to see if the applications would starts (so, we are not surprised if it doesn't work during the real start of the container)
RUN (export DRY_RUN=True; export UPLOAD_DIRECTORY="/app/working_directory"; streamlit run image-to-ascii-art-converter-web-ui.py &) && sleep 5 && curl http://localhost:${SERVER_PORT}/

EXPOSE $SERVER_PORT
HEALTHCHECK CMD curl --fail http://localhost:$SERVER_PORT/_stcore/health

# set all environment variables
ENTRYPOINT ["sh", "-c", "\
    export REPLACE_INDEX_HTML_CONTENT=$REPLACE_INDEX_HTML_CONTENT \
    export SERVER_PORT=$SERVER_PORT \
    export SERVER_MAXUPLOADSIZE=$SERVER_MAXUPLOADSIZE \
    export CANONICAL_URL=$CANONICAL_URL \
    export ADDITIONAL_HTML_HEAD_CONTENT=$ADDITIONAL_HTML_HEAD_CONTENT \
    && echo \"REPLACE_INDEX_HTML_CONTENT: $REPLACE_INDEX_HTML_CONTENT\" \
    && echo \"SERVER_PORT: $SERVER_PORT\" \
    && echo \"SERVER_MAXUPLOADSIZE: $SERVER_MAXUPLOADSIZE\" \
    && echo \"CANONICAL_URL: $CANONICAL_URL\" \
    && echo \"ADDITIONAL_HTML_HEAD_CONTENT: $ADDITIONAL_HTML_HEAD_CONTENT\" \
    && streamlit run image-to-ascii-art-converter-web-ui.py --server.port=$SERVER_PORT --server.address=0.0.0.0 --server.maxUploadSize=$SERVER_MAXUPLOADSIZE \
"]

