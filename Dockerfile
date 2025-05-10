ARG VERSION="3.13-alpine"
FROM python:$VERSION

ENV APP_HOME=/opt/service
RUN mkdir -p $APP_HOME

WORKDIR $APP_HOME

COPY app/ $APP_HOME/app/
COPY requirements.txt $APP_HOME/requirements.txt

RUN pip install --no-cache-dir -r $APP_HOME/requirements.txt

COPY config/ /config/

CMD ["python", "-m", "app.main"]