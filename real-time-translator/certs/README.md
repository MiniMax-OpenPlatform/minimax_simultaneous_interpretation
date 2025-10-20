# SSL证书生成说明

此目录用于存放SSL证书文件。为了安全考虑，证书文件不包含在Git仓库中，需要在本地生成。

## 生成自签名证书

运行以下命令生成SSL证书：

```bash
# 确保在项目根目录
cd real-time-translator

# 创建certs目录（如果不存在）
mkdir -p certs

# 生成自签名证书
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/C=US/ST=CA/L=SF/O=RealTimeTranslator/CN=localhost" -addext "subjectAltName=IP:127.0.0.1,DNS:localhost"
```

## 为远程访问生成证书

如果需要从其他机器访问，请替换IP地址：

```bash
# 获取本机IP
ip route get 1 | awk '{print $7; exit}'

# 使用你的IP地址生成证书
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/C=US/ST=CA/L=SF/O=RealTimeTranslator/CN=YOUR_IP" -addext "subjectAltName=IP:YOUR_IP,IP:127.0.0.1,DNS:localhost"
```

## 文件说明

- `cert.pem`: SSL证书文件
- `key.pem`: 私钥文件

这些文件将被.gitignore忽略，不会被提交到Git仓库中。