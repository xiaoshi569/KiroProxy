FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建数据目录
RUN mkdir -p /root/.kiro-proxy

# 暴露端口
EXPOSE 8080

# 启动服务
CMD ["python", "-m", "kiro_proxy.main"]
