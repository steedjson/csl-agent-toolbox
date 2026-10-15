# build stage
FROM python:3.12 as build-env
ARG SERVICE
COPY . /apps/$SERVICE
WORKDIR /apps/
RUN pip install --no-cache-dir cython -i https://pypi.mirrors.ustc.edu.cn/simple/ && \
    mv $SERVICE/compiler.py ./ && \
    python compiler.py ./$SERVICE 32

# final stage
FROM python:3.12
ARG SERVICE
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /apps/$SERVICE/requirements.txt
WORKDIR /apps/$SERVICE
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple/
COPY --from=build-env /apps/$SERVICE /apps/$SERVICE
