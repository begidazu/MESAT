FROM python:3.10-slim
WORKDIR /model
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "model.py", "--serve"]  # o el entrypoint que uses
