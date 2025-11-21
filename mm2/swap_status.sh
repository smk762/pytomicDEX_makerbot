#!/bin/bash
curl --url "http://127.0.0.1:7763" --data '{
  "method": "my_swap_status",
  "params": {
    "uuid": "'$1'"
  },
  "userpass": "hbM9a0WUY3RN-rhmtRD"
}'
