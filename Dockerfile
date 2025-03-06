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

EXPOSE 8000

ENTRYPOINT python manage.py migrate; \
python manage.py initdepartments; \
python manage.py inituser; \
python manage.py initabsenttype; \
celery -A oaback worker -l INFO --detach; \
uwsgi --ini uwsgi.ini