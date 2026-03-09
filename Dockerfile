FROM python:3.9-bullseye

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p json_input ics_output 空课表统计结果Excel

EXPOSE 5000

CMD ["python", "app.py"]