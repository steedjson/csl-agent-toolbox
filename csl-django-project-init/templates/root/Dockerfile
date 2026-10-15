FROM python:3.12
ARG SERVICE
ARG BRANCH
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /apps/$SERVICE/requirements.txt
WORKDIR /apps/$SERVICE
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
COPY . /apps/$SERVICE
