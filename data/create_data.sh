#!/bin/bash

source .env

DB=data/data.db

for i in {001..080} ; do
echo "insert into customer(name,email) values('a$i','a$i@example.com')"  \
| sqlite3 $DB
done

for i in {01..01} ; do
echo "insert into user(name,email,disabled,admin,password,picture) values('${ADMIN_EMAIL}','${ADMIN_EMAIL}','0','1','fakehashed_admin$i','/img/admin_icon.webp')" | sqlite3 $DB
done

for i in {02..02} ; do
echo "insert into user(name,email,disabled,admin) values('admin$i','admin$i@example.com','1','1')" | sqlite3 $DB
done

for i in {01..01} ; do
echo "insert into user(name,email,disabled,admin) values('user$i','user$i@example.com','0','0')" | sqlite3 $DB
done

for i in {02..02} ; do
echo "insert into user(name,email,disabled,admin) values('user$i','user$i@example.com','1','0')" | sqlite3 $DB
done


echo "Customer:"
echo "select * from customer" | sqlite3 $DB | tail

echo "Users:"
echo "select * from user" | sqlite3 $DB

pwgen(){
    basenc --base64url < /dev/urandom | head -c 64 ; echo
}

email=${ADMIN_EMAIL}
ssid=$(pwgen)
csrf_token=$(pwgen)

# if [ "$CACHE_STORE" == "sql" ]; then
    DB=data/cache.db
    echo "insert or replace into sessions (id, session_id,user_id,email,csrf_token) values (1, '$ssid', 1, '$email', '$csrf_token')" | sqlite3 $DB
    echo "Sessions:"
    echo "select * from sessions" | sqlite3 $DB
# fi

# if [ "$CACHE_STORE" == "redis" ]; then
    reds_cmd="redis-cli -h $REDIS_HOST -p $REDIS_PORT"

    # Clean up existing sessions
    $reds_cmd keys "*"| xargs -i $reds_cmd del {}

    # Create admin session
    # session_data="{session_id: $ssid, csrf_token: $csrf_token, user_id: 1, email: $email}"
    session_data="{\"session_id\": \"$ssid\", \"csrf_token\": \"$csrf_token\", \"user_id\": \"1\", \"email\": \"$email\"}"
    echo $reds_cmd set session:$ssid \"$session_data\"
    $reds_cmd set session:$ssid "$session_data"
# fi
