FROM alpine:3 AS downloader
RUN apk add --no-cache curl \
    && curl -fL "https://jdbc.postgresql.org/download/postgresql-42.7.4.jar" \
       -o /postgresql-jdbc.jar

FROM apache/hive:4.2.0
USER root
COPY --from=downloader /postgresql-jdbc.jar /opt/hive/lib/postgresql-jdbc.jar
USER hive