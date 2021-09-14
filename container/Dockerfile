from python:3.9

WORKDIR /app

COPY pyproject.toml /app/
COPY bind_rest_api /app/bind_rest_api/
COPY config.env /app
COPY apikeys.pass /app
# make the default logging dir
RUN  mkdir /app/logs

RUN pip install poetry && poetry config virtualenvs.create false

RUN poetry install --no-dev

EXPOSE 8000
#CMD ["uvicorn","bind_rest_api.api.api:app","--host=0.0.0.0","--port=8000"]
CMD ["bindapi", "--host", "0.0.0.0", "--port", "8000"]

