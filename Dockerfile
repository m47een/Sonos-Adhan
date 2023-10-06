# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11-alpine

RUN apk update
RUN apk upgrade

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN addgroup -S soco-cli && adduser -S soco-cli -G soco-cli
USER soco-cli

WORKDIR /app
VOLUME ./config

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

ENV PATH /home/soco-cli/.local/bin:$PATH


# Install pip requirements
COPY requirements.txt .

RUN pip install --no-cache-dir --disable-pip-version-check --upgrade pip
RUN pip install --no-cache-dir -r ./requirements.txt

COPY . /.

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "PrayerTime.py"]