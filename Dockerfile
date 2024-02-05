# Взять официальный базовый образ Python с платформы Docker
FROM python:alpine3.19
LABEL maintainer="rublock"

# Задать переменные среды
ENV PYTHONUNBUFFERED 1

# Скопировать код в работчий каталог в образ
COPY ./requirements.txt ./requirements.txt
COPY .app/ .app/

# Задать рабочий каталог
WORKDIR /app
EXPOSE 8000

# Установка python, venv, зависимостей, регистарция пользователя
RUN python -m venv /python && \
    /python/bin/pip install --upgrade pip && \
    /python/bin/pip install -r requirements.txt && \
    adduser --disabled-password --no-create-home admin

# Путь к локальному виртуальному окружению
ENV PATH="/python/bin:$PATH"

# Переключаемся на локального пользователя
USER admin


#CMD ["uwsgi", "--master", "--ini", "/config/uwsgi/uwsgi.ini"]
