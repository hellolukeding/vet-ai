#!/bin/bash
set -e

# 创建应用数据库和用户
mongo <<EOF
use admin
db.createUser({
  user: 'vet_ai_user',
  pwd: 'vet_ai_password',
  roles: [{
    role: 'readWrite',
    db: 'vet_ai'
  }]
});

use vet_ai
db.createCollection('diagnoses');
db.createCollection('pets');
db.createCollection('sessions');

EOF
