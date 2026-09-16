FROM python:3.12-slim
WORKDIR /app
COPY app.py /app/app.py
COPY app_v13.py /app/app_v13.py
COPY v13_support.py /app/v13_support.py
COPY app_v14.py /app/app_v14.py
COPY assets /app/assets
ENV PORT=3000
EXPOSE 3000
CMD ["python", "/app/app_v14.py"]
