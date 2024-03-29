# FastAPI + HTMX with Sign in with Google

## What this look like

<img src=./images/FastAPI-HTMX-Google-OAuth043.gif width="600px">

## Directory structure

```
.
├── Readme.md
├── admin
│   ├── auth.py
│   ├── debug.py
│   └── user.py
├── auth
├── config.py
├── customer
├── data
│   ├── cache.db
│   ├── create_data.sh
│   ├── data.db
│   └── db.py
├── htmx
│   ├── htmx.py
│   └── htmx_secret.py
├── images
│   ├── FastAPI-HTMX-Google-OAuth01.gif
│   ├── cat_meme.png
│   ├── dog_meme.png
│   ├── door-check-out-icon.png
│   ├── image.py
│   └── unknown-person-icon.png
├── main.py
└── templates
    ├── auth_navbar.login.callback.j2
    ├── auth_navbar.login.html.j2
    ├── auth_navbar.login.j2
    ├── auth_navbar.login.js.j2
    ├── auth_navbar.logout.j2
    ├── content.error.j2
    ├── content.list.j2
    ├── content.list.tbody.j2
    ├── content.secret.j2
    ├── content.top.j2
    ├── head.j2
    └── spa.j2
```

# Howto run app in this repository.

## 1. <a name="googleapisetup">Setup OAuth configuration on Google APIs console</a>

1. Open https://console.cloud.google.com/apis/credentials.
1. Go CREATE CREDENTIALS -> Go Create OAuth client ID -> Choose "Web applicatin" as Application type -> create.
1. Save the client ID somewhere, as it is needed later. 
1. Go one of the OAuth 2.0 Client IDs just created, then add both of the following to the Authorized JavaScript origins box.

~~~
http://localhost
http://localhost:8000
~~~

For details, see https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid.

## 2. FastAPI

Prepare python venv and install packages
~~~
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi sqlalchemy uvicorn google-auth requests python-dotenv python-multipart pydantic-settings pydantic[email] jinja2 PyJWT redis
~~~

Create database
~~~
rm data/data.db data/cache.db
python3 data/db.py
./data/create_data.sh
~~~

Edit .env in the directory where main.py exists.
~~~
ORIGIN_SERVER=http://localhost:3000
GOOGLE_OAUTH2_CLIENT_ID=888888888888-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com
ADMIN_EMAIL=admin@example.com
SESSION_MAX_AGE=300
CACHE_STORE=sql
# CACHE_STORE=redis
REDIS_HOST=localhost
REDIS_PORT=6379
~~~

Run server
~~~
uvicorn main:app  --host 0.0.0.0 --reload --log-config log_config.yaml
~~~

## (Optional) Redis for Session Storage

Run redis

```
docker compose -f data/docker-compose.yml up -d
```

Edit .env file

```
# CACHE_STORE=sql
CACHE_STORE=redis
```

re-create a session for admin login
```
./data/renew_admin_session.sh
```

restart uvicon
```
uvicorn main:app  --host 0.0.0.0 --reload --log-config log_config.yaml
```

## (Optional) Monitor Session storage contents

### SQLite

```
watch -n 1 'echo "select * from sessions" | sqlite3 data/cache.db'
```

### Redis

If the OS has redis-cli, use the following;

```
watch -n 1  'for k in $(redis-cli keys "*" | xargs) ; do echo -n $k": " ; redis-cli get $k|xargs ; done'
```

If the OS does not have redis-cli, first exec into the redis docker container,

```
$ docker ps
CONTAINER ID   IMAGE     COMMAND                  CREATED      STATUS      PORTS                                       NAMES
29a78e16ec02   redis     "docker-entrypoint.s…"   7 days ago   Up 7 days   0.0.0.0:6379->6379/tcp, :::6379->6379/tcp   data-redis-1

$ docker exec -it data-redis-1 bash
```

then monitor the contents using redis-cli, for example;

```
while true ; do sleep 1 ;clear; for k in $(redis-cli keys "*" | xargs) ; do echo -n $k": " ; redis-cli get $k|xargs ;done ; done
```
