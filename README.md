# oabcak

#### 介绍
{**以下是 Gitee 平台说明，您可以替换此简介**
Gitee 是 OSCHINA 推出的基于 Git 的代码托管平台（同时支持 SVN）。专为开发者提供稳定、高效、安全的云端软件开发协作平台
无论是个人、团队、或是企业，都能够用 Gitee 实现代码托管、项目管理、协作开发。企业项目请看 [https://gitee.com/enterprises](https://gitee.com/enterprises)}

#### 技术应用
1. 使用Django作为后端框架，重写了Django自带的User模型类，关闭了默认的session、auth模块， 使用自定义中间件+JWToken实现前后端登录验证。
2. 使用了ORM+MySQL8作为后端存储，对经常搜索的关键字段添加了索引。
3. 使用django-cors-headers实现前端与后端跨域请求访问。
4. 使用了djangorestframework插件的序列化、视图集、认证和权限、限速节流、分页等模块。
5. 使用了Celery+Redis实现邮件等任务的异步化，提高了耗时任务请求的响应速度。
6. 使用Pandas库对上传Excel和下载Excel文件进行快速处理。
7. 使用docker+nginx+uwsgi+git实现项目的部署。


#### 服务器部署流程
1.  克隆该项目
```git clone https://github.com/tsaydust/wumi_oaback.git```
和wumi_oafront,放在同一个文件夹www下
```git clone https://github.com/tsaydust/wumi_oafront.git```
2.  在www目录创建volumes文件夹负责容器数据持久化
```mkdir volumes```
3.  创建compose.yml
```
name: oa
services:
  oaredis:
    image: "redis:7.2.5"
    container_name: "oaredis"
    restart: always
    healthcheck:
      test: [ "CMD", "redis-cli", "--raw", "incr", "ping" ]
    volumes:
      # redis中产生的数据是放到容器的/data中的
      - ./volumes/oaredis:/data
    networks:
      - oa
  oadb:
    image: "mysql:8.4.0"
    container_name: "oadb"
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: 123456
      MYSQL_DATABASE: zhiliaooa
      MYSQL_ALLOW_EMPTY_PASSWORD: "no"
      TZ: Asia/Shanghai
    command:
      --character-set-server=UTF8MB4
      --max_connections=1000
    healthcheck:
      test: ["CMD","mysqladmin", "ping", "-h", "localhost", "-uroot", "-p$$MYSQL_ROOT_PASSWORD"]
    volumes:
      # mysql容器中的数据，是存储在/var/lib/mysql下
      - ./volumes/db/data:/var/lib/mysql
      - ./volumes/db/log:/var/log/mysql
    networks:
      - oa
  oaback:
    build: ./wumi_oaback
    restart: always
    container_name: "oaback"
    healthcheck:
      test: curl -f http://127.0.0.1:8000/api/home/health
    depends_on:
      oaredis:
        condition: service_healthy
      oadb:
        condition: service_healthy
    volumes:
      - ./volumes/sock:/data/sock
      - ./volumes/oaback/data:/data
    networks:
      - oa
  oafront:
    build: ./wumi_oafront
    container_name: "oafront"
    restart: always
    ports:
      - "80:80"
    healthcheck:
      test: curl -f http://127.0.0.1
    volumes:
      - ./volumes/sock:/data/sock
      - ./volumes/oafront/log:/data/log
    networks:
      - oa
networks:
  oa:
    driver: "bridge"

```
4. 运行命令```docker compose up```
#### 使用说明
1. 实现了考勤管理功能，员工能向上级领导发起考勤申请，领导能进行考勤审核。
2. 实现了通知管理，发布带有富文本标签的通知，并实现了按部门浏览的权限。
3. 实现了员工管理，能通过发送邮件邀请员工，搜索员工，领导修改员工状态，批量上传员工，批量 下载员工信息，分页等功能。
4. 自定义权限管理，实现了按部门的权限管理。


