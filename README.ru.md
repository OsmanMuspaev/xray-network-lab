# Xray Network Lab

[English](README.md) · Русский

Стенд разворачивает клиент и сервер Xray с VLESS, REALITY и Vision. Скрипты сравнивают прямой маршрут с туннелем до одного HTTP-сервиса и измеряют скорость, задержку и нагрузку на сервер.

[Методика и результаты](REPORT.ru.md)

## Локальная проверка

Здесь нужны Docker Compose 2.24.4 или новее, Python 3, OpenSSL и curl. Образы должны быть доступны Docker. После загрузки образов тестовый трафик и рукопожатия остаются внутри лаборатории. Конфигурации и сертификат создаются отдельно в `private-lab/`.

```sh
python3 configure.py --lab
docker compose -f compose.yaml -f compose.lab.yaml --profile client up -d
```

Сервер Xray доступен внутри Docker; SOCKS и прямой HTTP-порт опубликованы на loopback. Для адреса `172.30.184.10:18080` есть отдельное разрешение TCP только в лабораторной конфигурации. Подсеть Compose `172.30.184.0/24` должна быть свободна.

В одном терминале запусти сбор ресурсов, в другом — замер. После замера останови сборщик через Ctrl+C и выключи контейнеры.

```sh
container_id=$(docker compose -f compose.yaml -f compose.lab.yaml --profile client ps -q tunnel)
python3 collect_stats.py "$container_id" --output lab-resources-new.csv
```

```sh
python3 benchmark.py http://127.0.0.1:18080 \
  --local-tunnel-url http://172.30.184.10:18080 \
  --parallel 1 4 16 --duration 5 --repeats 3 --output lab-results-new.csv
docker compose -f compose.yaml -f compose.lab.yaml --profile client down
```

## Запуск сервера

Нужны Docker с Compose и Python 3. На VPS открой входящий TCP-порт 443. Если 443 занят, передай выбранный порт как `--port` генератору и `PORT` для Compose. На машине для замеров также нужен `curl` с SOCKS5.

```sh
python3 configure.py SERVER_IP TLS_HOST
docker compose run --rm tunnel tls ping TLS_HOST
docker compose up -d tunnel
docker compose logs --tail 20 tunnel
```

Вместо `SERVER_IP` подставь публичный адрес VPS. `TLS_HOST` — DNS-имя TLS-сервиса, доступного с VPS. До запуска посмотри, проходит ли к нему рукопожатие TLS 1.3 с указанным SNI. Параметры клиента и сервера должны совпадать.

Ссылка для импорта лежит в `private/profile.txt`. Передавай её только тому, кто будет проверять доступ. Для запуска клиента через Docker перенеси `private/client.json` на отдельную машину, положи рядом тот же Compose-файл и выполни `docker compose --profile client up -d client`. SOCKS слушает на `127.0.0.1:1080`. `private/server.json` содержит приватный ключ сервера, его оставь на VPS.

## Как прогнать замеры

На отдельном тестовом узле подними `target.py`. Он отдаёт короткий ответ на `/ping` и фиксированный файл на `/download`. Для сетевого замера этот узел должен быть доступен и клиенту, и VPS. Используй свой узел и ограничь доступ к тестовому порту адресами измерителей.

```sh
# На тестовом узле
python3 target.py --bind TEST_HOST_IP

# На машине с клиентом
python3 benchmark.py http://TEST_HOST_IP:18080 --parallel 1 4 16 --duration 30 --repeats 3
```

Вторая команда запускается со стороны клиента. В каждом режиме одновременно идут скачивания и короткие запросы для измерения задержки. В CSV попадают объём успешных скачиваний в пересчёте на МиБит/с, p95 коротких запросов и число ошибок. Сбор CPU и RAM запусти на VPS перед прогоном и останови через Ctrl+C после него:

```sh
python3 collect_stats.py "$(docker compose ps -q tunnel)" --output resources.csv
```

Часы клиента и VPS должны быть синхронизированы. Сопоставляй `timestamp_utc` с интервалом `started_utc` — `finished_utc` из результатов. Для нового запуска задай новое имя CSV: скрипты сохраняют предыдущие измерения.

Для проверки из разных сетей повтори тот же сценарий и запиши оператора, тип подключения и время. По одной просадке скорости или одному таймауту нельзя установить, что сработал DPI.
