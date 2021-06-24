FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-alpine3.10

ENV PYTHONUNBUFFERED 1

COPY requirements.txt .

#RUN wget http://dl-cdn.alpinelinux.org/alpine/v3.10/main
RUN sed -i 's/http/https/g' /etc/apk/repositories

#RUN apk update
#RUN apk add --update --no-cache postgresql-libs
#RUN apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev
#RUN python3 -m pip install -r requirements.txt --no-cache-dir
# RUN apk --purge del .build-deps
RUN \
 apk add --no-cache postgresql-libs && \
 apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
 python3 -m pip install -r requirements.txt --no-cache-dir && \
 apk --purge del .build-deps

ADD . /app

CMD ["uvicorn", "app.main:app", "--port", "8000", "--host", "0.0.0.0"]
