FROM python:3.14-slim-trixie

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
RUN pip install --no-cache-dir -e .

EXPOSE 8081
    
CMD ["uvicorn", "src.users_api.main:app", "--host", "0.0.0.0", "--port", "8081"]