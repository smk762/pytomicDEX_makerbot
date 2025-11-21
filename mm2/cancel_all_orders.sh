#!/bin/bash
curl --url "http://127.0.0.1:7763" --data '{
  "method": "cancel_all_orders",
  "cancel_by": {
    "type": "All"
  },
  "userpass": "hbM9a0WUY3RN-rhmtRD"
}'
