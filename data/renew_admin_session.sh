#!/bin/bash

pwgen(){
    basenc --base64url < /dev/urandom | head -c 64 ; echo
}

email="admin01@example.com"
ssid=$(pwgen)

DB=data/cache.db

delete(){
echo "delete from sessions where email = 'admin01@example.com'" | sqlite3 $DB
}

delete_all(){
echo "delete from sessions" | sqlite3 $DB
}

insert_or_replace(){
echo "insert or replace into sessions (id, session_id,user_id,email)
	values (1, '$ssid', 1, '$email')" | sqlite3 $DB
}

check(){
echo "Sessions:"
echo "select * from sessions" | sqlite3 $DB
echo "session_id:" $ssid
}

insert_or_replace
check

