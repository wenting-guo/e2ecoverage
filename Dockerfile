FROM registry.daocloud.cn/mesh/python:3.7

WORKDIR /app

ADD requirements.txt .

RUN pip3 install -r requirements.txt

ADD . .

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo 'Asia/Shanghai' > /etc/timezone

RUN git remote set-url origin http://guangli.bao:Aew\"ahch3hooth8@gitlab.daocloud.cn/ndx/qa/e2ecoverage

# EXPOSE 8000

# CMD "python3" "main.py" "web"
