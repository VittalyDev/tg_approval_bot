FROM python:3.12-slim
WORKDIR /app
COPY app.py /app/app.py
COPY assets /app/assets
ENV PORT=3000
EXPOSE 3000
CMD ["python", "/app/app.py"]
