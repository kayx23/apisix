---
title: rocketmq-logger
keywords:
  - Apache APISIX
  - API Gateway
  - Plugin
  - RocketMQ Logger
description: The rocketmq-logger Plugin sends APISIX request and response logs to Apache RocketMQ in batches with structured, original-request, or customized formats.
---
<!--
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
-->

<head>
  <link rel="canonical" href="https://docs.api7.ai/hub/rocketmq-logger" />
</head>

## Description

The `rocketmq-logger` Plugin sends request and response logs to Apache RocketMQ in batches. It supports the default structured log format, the original HTTP request format, and customized log fields.

## Attributes

| Name                   | Type    | Required | Default            | Valid values          | Description                                                                                                                                                                                                                                                                                                    |
|------------------------|---------|----------|--------------------|-----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| nameserver_list        | array[string]  | True     |                    |                       | List of RocketMQ nameservers.                                                                                                                                                                                                                                                                                  |
| topic                  | string  | True     |                    |                       | Target topic to push the data to.                                                                                                                                                                                                                                                                              |
| key                    | string  | False    |                    |                       | Key of the message.                                                                                                                                                                                                                                                                                            |
| tag                    | string  | False    |                    |                       | Tag of the message.                                                                                                                                                                                                                                                                                            |
| log_format             | object  | False    |                    |                       | Custom log format using key-value pairs in JSON format. Values can reference [NGINX variables](https://nginx.org/en/docs/http/ngx_http_core_module.html). You can also configure log format on a global scale using the [plugin metadata](../terminology/plugin-metadata.md), which configures the log format for all `rocketmq-logger` Plugin instances. If the log format configured on the individual Plugin instance differs from the log format configured on Plugin metadata, the log format configured on the individual Plugin instance takes precedence. |
| log_format_extra             | object  | False    |                    |                       | Extra log fields **added on top of** the default log entry, keeping every default field instead of replacing them (unlike `log_format`). Same value syntax as `log_format`. Ignored when `log_format` is set. |
| timeout                | integer | False    | 3                  |                       | Timeout for the upstream to send data.                                                                                                                                                                                                                                                                         |
| use_tls                | boolean | False    | false              |                       | If true, enable TLS encryption for the connection.                                                                                                                                                                                                                                                             |
| access_key             | string  | False    |                    |                       | Access key for ACL. Setting to an empty string will disable the ACL.                                                                                                                                                                                                                                           |
| secret_key             | string  | False    |                    |                       | Secret key for ACL.                                                                                                                                                                                                                                                                                            |
| name                   | string  | False    | `rocketmq logger`  |                       | Unique identifier of the Plugin for the batch processor. If you use Prometheus to monitor APISIX metrics, the name is exported in `apisix_batch_process_entries`.                                                                                                                                              |
| meta_format            | string  | False    | `default`          | `default` or `origin` | Format to collect the request information. Setting to `default` collects the information in JSON format and `origin` collects the information with the original HTTP request.                                                                                                                                   |
| include_req_body       | boolean | False    | false              |                       | If true, include the request body in the log. Note that if the request body is too big to be kept in the memory, it cannot be logged due to NGINX's limitations.                                                                                                                                               |
| include_req_body_expr  | array   | False    |                    |                       | An array of one or more conditions in the form of [lua-resty-expr](https://github.com/api7/lua-resty-expr) expressions. Used when `include_req_body` is true. Request body is only logged when the expressions configured here evaluate to true.                                                                |
| include_resp_body      | boolean | False    | false              |                       | If true, include the response body in the log.                                                                                                                                                                                                                                                                 |
| include_resp_body_expr | array   | False    |                    |                       | An array of one or more conditions in the form of [lua-resty-expr](https://github.com/api7/lua-resty-expr) expressions. Used when `include_resp_body` is true. Response body is only logged when the expressions configured here evaluate to true.                                                              |
| max_req_body_bytes     | integer | False    | 524288             | greater than or equal to 1 | Maximum request body size in bytes to include in the log. If the request body exceeds this value, it will be truncated. Available in APISIX from 3.16.0.                                                                                                                                                  |
| max_resp_body_bytes    | integer | False    | 524288             | greater than or equal to 1 | Maximum response body size in bytes to include in the log. If the response body exceeds this value, it will be truncated. Available in APISIX from 3.16.0.                                                                                                                                                |
| batch_max_size         | integer | False    | 1000               | greater than 0        | The number of log entries allowed in one batch. Once reached, the batch will be sent to the logging service. Setting this parameter to 1 means immediate processing.                                                                                                                                           |
| inactive_timeout       | integer | False    | 5                  | greater than 0        | The maximum time in seconds to wait for new logs before sending the batch to the logging service. The value should be smaller than `buffer_duration`.                                                                                                                                                           |
| buffer_duration        | integer | False    | 60                 | greater than 0        | The maximum time in seconds from the earliest entry allowed before sending the batch to the logging service.                                                                                                                                                                                                   |
| retry_delay            | integer | False    | 1                  | greater than or equal to 0 | The time interval in seconds to retry sending the batch to the logging service if the batch was not successfully sent.                                                                                                                                                                                    |
| max_retry_count        | integer | False    | 0                  | greater than or equal to 0 | The maximum number of unsuccessful retries allowed before dropping the log entries.                                                                                                                                                                                                                       |

NOTE: `encrypt_fields = {"secret_key"}` is also defined in the schema, which means that the field will be stored encrypted in etcd. See [encrypted storage fields](../plugin-develop.md#encrypted-storage-fields).

## Metadata

You can also set the format of the logs by configuring the Plugin metadata. The following configurations are available:

| Name                | Type    | Required | Default | Description                                                                                                                                                                                                     |
|---------------------|---------|----------|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| log_format          | object  | False    |         | Custom log format using key-value pairs in JSON format. Values can reference [NGINX variables](https://nginx.org/en/docs/http/ngx_http_core_module.html).                                                       |
| log_format_extra          | object  | False    |         | Extra log fields **added on top of** the default log entry, keeping every default field instead of replacing them (unlike `log_format`). Same value syntax as `log_format`. Ignored when `log_format` is set. |
| max_pending_entries | integer | False | 8192 | Maximum number of entries waiting to be processed. New entries are discarded while the backlog exceeds this, which stops a slow or unreachable log server from growing the worker's memory without bound. See [Batch Processor](../batch-processor.md#limiting-the-backlog) for the memory a backlog of this size costs. |
:::info IMPORTANT

Configuring the Plugin metadata is global in scope. This means that it will take effect on all Routes and Services which use the `rocketmq-logger` Plugin.

:::

## Examples

The examples below configure the `rocketmq-logger` Plugin for common logging scenarios.

To follow the examples, start a RocketMQ NameServer and broker. The APISIX and RocketMQ containers must share a Docker network so that APISIX can reach the NameServer by container name.

Set `APISIX_CONTAINER` to the name of the running APISIX container. Create a dedicated Docker network and connect APISIX to it:

```shell
export APISIX_CONTAINER=replace-with-apisix-container-name

docker network create apisix-rocketmq-net
docker network connect apisix-rocketmq-net "$APISIX_CONTAINER"
```

Create the Docker Compose file:

```yaml title="docker-compose.yml"
services:
  rocketmq-namesrv:
    image: apache/rocketmq:5.5.0
    container_name: rocketmq-namesrv
    restart: unless-stopped
    command: ["nameserver"]
    networks:
      - apisix-rocketmq-net

  rocketmq-broker:
    image: apache/rocketmq:5.5.0
    container_name: rocketmq-broker
    restart: unless-stopped
    depends_on:
      - rocketmq-namesrv
    environment:
      NAMESRV_ADDR: rocketmq-namesrv:9876
    command: ["broker", "-n", "rocketmq-namesrv:9876"]
    networks:
      - apisix-rocketmq-net

networks:
  apisix-rocketmq-net:
    external: true
```

Start containers:

```shell
docker compose up -d
```

Wait for the broker to register with the NameServer:

```shell
until docker exec rocketmq-namesrv sh mqadmin clusterList \
  -n rocketmq-namesrv:9876 2>/dev/null | grep -q "DefaultCluster"; do
  sleep 2
done
```

Create the `TopicTest` topic:

```shell
docker exec rocketmq-namesrv sh mqadmin updateTopic \
  -n rocketmq-namesrv:9876 \
  -t TopicTest \
  -c DefaultCluster
```

After sending a request in the following examples, inspect the messages in `TopicTest`:

```shell
docker exec rocketmq-namesrv sh mqadmin printMsg \
  -n rocketmq-namesrv:9876 \
  -t TopicTest
```

:::note

You can fetch the `admin_key` from `config.yaml` and save to an environment variable with the following command:

```bash
admin_key=$(yq '.deployment.admin.admin_key[0].key' conf/config.yaml | sed 's/"//g')
```

:::

### Compare Structured and Original Request Logs

The `default` metadata format sends a structured JSON log entry, while the `origin` format sends the original HTTP request. This example configures both formats so that you can compare their output.

Create a Route with `rocketmq-logger` with `meta_format` set to the `default` log format and `batch_max_size` set to 1 to send the log entry immediately:

```shell
curl "http://127.0.0.1:9180/apisix/admin/routes/rocketmq-logger-route" -X PUT \
  -H "X-API-KEY: ${admin_key}" \
  -d '{
    "uri": "/anything",
    "plugins": {
      "rocketmq-logger": {
        "nameserver_list": [ "rocketmq-namesrv:9876" ],
        "topic": "TopicTest",
        "key": "key1",
        "timeout": 30,
        "meta_format": "default",
        "batch_max_size": 1
      }
    },
    "upstream": {
      "nodes": {
        "httpbin.org:80": 1
      },
      "type": "roundrobin"
    }
  }'
```

Send a request to the Route to generate a log entry:

```shell
curl -i "http://127.0.0.1:9080/anything"
```

Inspect `TopicTest`. The message body should contain a log entry similar to the following:

```json
{
  "client_ip": "127.0.0.1",
  "upstream": "34.197.122.172:80",
  "start_time": 1789377954622,
  "request": {
    "headers": {
      "host": "127.0.0.1:9080",
      "accept": "*/*",
      "user-agent": "curl/8.6.0"
    },
    "querystring": {},
    "size": 86,
    "uri": "/anything",
    "url": "http://127.0.0.1:9080/anything",
    "method": "GET"
  },
  "route_id": "rocketmq-logger-route",
  "apisix_latency": 8.9998455047607,
  "upstream_latency": 503,
  "latency": 511.99984550476,
  "response": {
    "size": 617,
    "headers": {
      "content-length": "391",
      "connection": "close",
      "date": "Mon, 14 Sep 2026 09:25:54 GMT",
      "server": "APISIX/3.18.0",
      "content-type": "application/json"
    },
    "status": 200
  },
  "server": {
    "hostname": "apisix",
    "version": "3.18.0"
  },
  "service_id": ""
}
```

Update the `rocketmq-logger` meta log format to `origin`:

```shell
curl "http://127.0.0.1:9180/apisix/admin/routes/rocketmq-logger-route" -X PATCH \
  -H "X-API-KEY: ${admin_key}" \
  -d '{
    "plugins": {
      "rocketmq-logger": {
        "meta_format": "origin"
      }
    }
  }'
```

Send a request to the Route again to generate a new log entry:

```shell
curl -i "http://127.0.0.1:9080/anything"
```

Inspect the topic again. The new message body should contain the request in its original HTTP format:

```text
GET /anything HTTP/1.1
host: 127.0.0.1:9080
user-agent: curl/8.6.0
accept: */*
```

### Customize Log Fields With Plugin Metadata

Use [plugin metadata](../terminology/plugin-metadata.md) to apply a common log format to every `rocketmq-logger` instance. The following configuration uses NGINX variables to record a request header and a response header. Set `meta_format` to `default` because Plugin metadata does not customize logs in the `origin` format.

First, create a Route with `rocketmq-logger` with `meta_format` set to `default` and `batch_max_size` set to 1 to send the log entry immediately:

```shell
curl "http://127.0.0.1:9180/apisix/admin/routes/rocketmq-logger-route" -X PUT \
  -H "X-API-KEY: ${admin_key}" \
  -d '{
    "uri": "/anything",
    "plugins": {
      "rocketmq-logger": {
        "nameserver_list": [ "rocketmq-namesrv:9876" ],
        "topic": "TopicTest",
        "key": "key1",
        "timeout": 30,
        "meta_format": "default",
        "batch_max_size": 1
      }
    },
    "upstream": {
      "nodes": {
        "httpbin.org:80": 1
      },
      "type": "roundrobin"
    }
  }'
```

Next, configure the Plugin metadata for `rocketmq-logger` to log the custom request header `env` and the response header `Content-Type`:

```shell
curl "http://127.0.0.1:9180/apisix/admin/plugin_metadata/rocketmq-logger" -X PUT \
  -H "X-API-KEY: ${admin_key}" \
  -d '{
    "log_format": {
      "host": "$host",
      "@timestamp": "$time_iso8601",
      "client_ip": "$remote_addr",
      "env": "$http_env",
      "resp_content_type": "$sent_http_Content_Type"
    }
  }'
```

Send a request to the Route with the `env` header:

```shell
curl -i "http://127.0.0.1:9080/anything" -H "env: dev"
```

Inspect the topic. The message body should contain a log entry similar to the following:

```json
{
  "host": "127.0.0.1",
  "client_ip": "127.0.0.1",
  "resp_content_type": "application/json",
  "route_id": "rocketmq-logger-route",
  "env": "dev",
  "@timestamp": "2026-09-14T09:28:24+00:00"
}
```

### Log Request Bodies Conditionally

The following example records the request body only when the `log_body` query parameter is `yes`.

Create a Route with `rocketmq-logger` as follows, enabling request body logging only when the URL query string `log_body` is `yes`:

```shell
curl "http://127.0.0.1:9180/apisix/admin/routes/rocketmq-logger-route" -X PUT \
  -H "X-API-KEY: ${admin_key}" \
  -d '{
    "uri": "/anything",
    "plugins": {
      "rocketmq-logger": {
        "nameserver_list": [ "rocketmq-namesrv:9876" ],
        "topic": "TopicTest",
        "key": "key1",
        "timeout": 30,
        "meta_format": "default",
        "batch_max_size": 1,
        "include_req_body": true,
        "include_req_body_expr": [["arg_log_body", "==", "yes"]]
      }
    },
    "upstream": {
      "nodes": {
        "httpbin.org:80": 1
      },
      "type": "roundrobin"
    }
  }'
```

Send a request to the Route with a URL query string satisfying the condition:

```shell
curl -i "http://127.0.0.1:9080/anything?log_body=yes" -X POST -d '{"env": "dev"}'
```

Inspect the topic. The message body should include the request body:

```json
{
  "request": {
    "method": "POST",
    "body": "{\"env\": \"dev\"}",
    "size": 183
  }
}
```

Send a request to the Route without any URL query string:

```shell
curl -i "http://127.0.0.1:9080/anything" -X POST -d '{"env": "dev"}'
```

You should not observe the request body in the log.

:::note

If you have customized the `log_format` in addition to setting `include_req_body` or `include_resp_body` to `true`, the Plugin would not include the bodies in the logs.

As a workaround, you may be able to use the NGINX variable `$request_body` in the log format, such as:

```json
{
  "rocketmq-logger": {
    "log_format": {"body": "$request_body"}
  }
}
```

:::
