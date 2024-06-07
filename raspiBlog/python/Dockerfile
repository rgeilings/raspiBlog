FROM python:3.9-slim

# Installeer vereiste packages inclusief tzdata
RUN apt-get update && apt-get install -y \
    tzdata \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Genereer en configureer de Nederlandse locale
RUN echo "nl_NL.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen nl_NL.UTF-8 && \
    update-locale LANG=nl_NL.UTF-8

# Stel de tijdzone in naar Amsterdam
ENV TZ=Europe/Amsterdam

# Configureer tzdata
RUN ln -snf /usr/share/zoneinfo/Europe/Amsterdam /etc/localtime && echo "Europe/Amsterdam" > /etc/timezone

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
