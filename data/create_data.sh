#!/bin/bash

DB=data/data.db

for i in {001..020} ; do
echo "insert into customer(name,email) values('a$i','a$i@example.com')"  \
| sqlite3 $DB
done

for i in {01..01} ; do
echo "insert into user(name,email,disabled,admin,password) values('admin$i','admin$i@example.com','0','1','fakehashed_admin$i')" | sqlite3 $DB
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

echo "Sessions:"
echo "select * from sessions" | sqlite3 data/cache.db

echo "Users:"
echo "select * from user" | sqlite3 $DB
