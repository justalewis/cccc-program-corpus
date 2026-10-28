# Datasette over the release database. Built by deploy/deploy.sh; secrets come from `fly secrets`.
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir datasette==0.65.5 datasette-vega==0.6.2
COPY cccc.db metadata.json ./
RUN datasette inspect cccc.db --inspect-file inspect-data.json
ENV PORT=8080
EXPOSE 8080
CMD datasette serve --host 0.0.0.0 --port $PORT -i cccc.db --inspect-file inspect-data.json --metadata metadata.json \
    --cors --setting sql_time_limit_ms 3000 --setting default_page_size 50 --setting facet_time_limit_ms 1000
