FROM fluent/fluentd:v1.16-1

USER root

RUN apk add --no-cache --update build-base
RUN gem install fluent-plugin-http

USER fluent
