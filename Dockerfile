# 基础镜像
FROM python:3.12.3
# 将当前目录下的所有文件，都拷贝到容器的/www目录下
COPY . /www/
# 将容器中的工作目录，切换到/www下
WORKDIR /www
# 安装项目依赖的包
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
# 安装uwsgi
RUN pip install uwsgi==2.0.25.1 -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN mkdir -p /data/log
RUN mkdir -p /data/sock

RUN python manage.py collectstatic --noinput

EXPOSE 8000

# 在 Dockerfile 中添加初始化逻辑
ENTRYPOINT ["/bin/sh", "-c", \
  "if [ ! -f /data/initialized ]; then \
    python manage.py migrate && \
    python manage.py initdepartments && \
    python manage.py inituser && \
    python manage.py initabsenttype && \
    touch /data/initialized; \
  fi && \
  celery -A oaback worker -l INFO --detach && \
  uwsgi --ini uwsgi.ini"]