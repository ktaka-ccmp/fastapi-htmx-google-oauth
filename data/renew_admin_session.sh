#!/bin/bash

source .env

pwgen(){
    basenc --base64url < /dev/urandom | head -c 64 ; echo
}

email=${ADMIN_EMAIL}
ssid=$(pwgen)
csrf_token=$(pwgen)

SQL_STORE=data/cache.db

delete(){
echo "delete from sessions where email = '$email'" | sqlite3 $SQL_STORE
}

delete_all(){
echo "delete from sessions" | sqlite3 $SQL_STORE
}

insert_or_replace(){
echo "insert or replace into sessions (id, session_id,user_id,email,csrf_token)
    values (1, '$ssid', 1, '$email', '$csrf_token')" | sqlite3 $SQL_STORE
}

check(){
echo "session_id for $email : " $ssid
echo
echo "Sessions in $SQL_STORE:"
echo "select * from sessions" | sqlite3 $SQL_STORE
}

insert_or_replace_redis(){
    if [ "$CACHE_STORE" == "redis" ]; then
        reds_cmd="redis-cli -h $REDIS_HOST -p $REDIS_PORT"

        # Clean up existing admin sessions
        for k in $($reds_cmd keys "*"); do
            if ($reds_cmd get $k | egrep "\"email\": \"$ADMIN_EMAIL\"" > /dev/null) ; then
                $reds_cmd del $k > /dev/null
            fi
        done

        # Create admin session
        session_data="{\"session_id\": \"$ssid\", \"csrf_token\": \"$csrf_token\", \"user_id\": \"1\", \"email\": \"$email\"}"
        # echo $reds_cmd set session:$ssid \"$session_data\"
        $reds_cmd set session:$ssid "$session_data" > /dev/null
    fi
}

check_redis(){
    echo
    echo "Sessions in Redis:"
    for k in $(redis-cli keys "*" | xargs) ; do
        echo -n $k": " ; redis-cli get $k|xargs
    done
}

insert_or_replace
check

if [ "$CACHE_STORE" == "redis" ]; then
    insert_or_replace_redis
    check_redis
fi
