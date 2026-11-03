FROM fluent/fluentd:v1.16-1

USER root
RUN apk add --no-cache build-base ruby-dev

ENV BUNDLE_GEMFILE=/fluentd/plugins/Gemfile

COPY plugins/Gemfile /fluentd/plugins/Gemfile
RUN gem install bundler --no-document \
    && bundle install --gemfile=/fluentd/plugins/Gemfile

COPY fluent.conf /fluentd/etc/fluent.conf
RUN mkdir -p /fluentd/buffer \
    && chown -R fluent:fluent /fluentd/buffer /fluentd/etc /fluentd/plugins

USER fluent
CMD ["bundle", "exec", "fluentd", "-c", "/fluentd/etc/fluent.conf", "-p", "/fluentd/plugins"]
