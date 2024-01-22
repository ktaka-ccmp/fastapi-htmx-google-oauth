# FastAPI + HTMX with Sign in with Google

## What this look like

<img src=./images/FastAPI-HTMX-Google-OAuth01.gif width="600px">

## Directory structure

```
.
├── Readme.md
├── admin
│   ├── debug.py
│   └── user.py
├── auth
│   └── auth.py
├── config.py
├── data
│   ├── cache.db
│   ├── create_data.sh
│   ├── data.db
│   └── db.py
├── htmx
│   └── htmx.py
├── images
│   └── FastAPI-HTMX-Google-OAuth01.gif
├── main.py
└── templates
    ├── auth.j2
    ├── auth.login.google.html.j2
    ├── auth.login.google.j2
    ├── auth.login.google.js.j2
    ├── auth.logout.j2
    ├── header.j2
    ├── list.j2
    ├── list.tbody.j2
    └── list.tbody_empty.j2
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
pip install fastapi sqlalchemy uvicorn google-auth requests python-dotenv python-multipart pydantic-settings pydantic[email] jinja2 PyJWT
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
~~~

Run server
~~~
uvicorn main:app  --host 0.0.0.0 --reload
~~~

