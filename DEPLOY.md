# 部署到公网（阿里云 ECS · 1.6GiB）

本方案**直接部署**（不依赖 Docker），最省内存、最能复用你服务器上已有的 MySQL：

- 后端：用 systemd 服务跑 `uvicorn`，只监听 `127.0.0.1:8000`
- 前端：在**本地 Windows** 构建出 `dist/`，传到服务器由 **Nginx** 托管（服务器上不必装 Node）
- 数据库：复用服务器已有的 MySQL（`127.0.0.1:3306`），不再单独起实例
- 缓存：Redis 可选，未启动会自动降级，**先不装**

---

## 一、服务器前置（已在清理旧服务时完成）
- 停掉旧 demo：`blog.service`、`flask-student.service`、`apache2`（端口 80 已空出）
- 确认 `mysql.service` 在跑：`systemctl status mysql`
- 内存约 660MiB 可用，足够（再杀 vscode-server 可腾 ~700MB）

---

## 二、在服务器上准备目录与后端
```bash
# 1. 安装后端依赖（一次性的系统库 + Python 包）
apt update
apt install -y python3-venv python3-pip mysql-client   # 若 pip 装包慢可换国内源
# 建议加 1~2GB swap 兜底（已有 2GiB swap 可忽略）
# sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile

# 2. 拉代码（首次）
apt install -y git
git clone https://github.com/yuegu04/Anime_recommend.git /opt/anime
cd /opt/anime/back-api

# 3. 建虚拟环境并装依赖（如果之后代码更新，只需重新 git pull + 重跑 pip install）
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

## 三、配置数据库
```bash
# 登录 MySQL（用你服务器上 MySQL 的 root 密码；若未设密码，可能需先 ALTER USER 设密码）
mysql -u root -p
```
```sql
CREATE DATABASE IF NOT EXISTS media_recommend CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 建议新建专用账号（更安全），也可直接用 root：
-- CREATE USER 'anime'@'localhost' IDENTIFIED BY '强密码';
-- GRANT ALL PRIVILEGES ON media_recommend.* TO 'anime'@'localhost';
-- FLUSH PRIVILEGES;
EXIT;
```
```bash
# 4. 写服务端 .env
cp /opt/anime/deploy/env.server.example /opt/anime/back-api/.env
nano /opt/anime/back-api/.env     # 填入 DB_PWD、JWT_SECRET、CORS_ORIGINS
```

## 四、初始化数据表 + 导入数据
```bash
cd /opt/anime/back-api
source venv/bin/activate
python import_media.py            # 创建表并导入 anime.csv / filtered_anime.csv
deactivate
```
> 首次运行后端时 `app.recommend` 会加载/训练推荐模型，启动可能慢 1~2 分钟，属正常。

## 五、注册并启动后端服务（systemd）
```bash
cp /opt/anime/deploy/anime-backend.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now anime-backend.service
journalctl -u anime-backend.service -f    # 看日志，确认 "运行正常"
curl http://127.0.0.1:8000/               # 应返回 {"msg":"推荐系统后端服务运行正常"}
```

## 六、构建前端并上传（在本地 Windows 执行）
> 在服务器上构建会吃内存，建议在你的 Windows 开发机完成，再传 `dist/`。

```powershell
cd c:\Users\gongy\Desktop\media_recommend\front-media
npm install
npm run build          # 产出 dist/
```
把 `dist/` 传到服务器 `/var/www/anime`（需先建目录）：
```powershell
# 在 Windows 上用 scp（替换成你的服务器 IP / 密钥）
scp -r dist\* root@你的服务器IP:/var/www/anime
```
> 若用环境变量的其他方式，可在构建前设置 `VITE_API_BASE`（默认留空即走同源相对路径，配合 Nginx 反代，无需设置）。

## 七、安装并配置 Nginx（服务器执行）
```bash
apt install -y nginx
cp /opt/anime/deploy/nginx-anime.conf /etc/nginx/sites-available/anime
ln -sf /etc/nginx/sites-available/anime /etc/nginx/sites-enabled/anime
# 去掉默认站点，避免冲突
rm -f /etc/nginx/sites-enabled/default
nginx -t                    # 配置语法检查
systemctl enable --now nginx
```

## 八、验收
浏览器打开 `http://你的服务器IP`：
- 能看到前端页面、能搜索/看推荐 → 成功
- 后端日志无报错：`journalctl -u anime-backend.service -n 50`

---

## 九、日常运维
```bash
# 更新代码（后端）
cd /opt/anime && git pull
cd back-api && source venv/bin/activate && pip install -r requirements.txt && deactivate
systemctl restart anime-backend.service

# 更新前端：本地重新 npm run build，再 scp dist 到 /var/www/anime

# 看后端日志
journalctl -u anime-backend.service -f

# 重启整机后自动拉起：anime-backend / mysql / nginx 都已 enable
```

## 十、可选：域名 + HTTPS（备案后）
1. 域名解析 A 记录指向服务器公网 IP，并完成 ICP 备案
2. 改 `nginx-anime.conf` 里的 `server_name _;` 为你的域名，启用文件末尾的 443 段
3. `apt install -y certbot python3-certbot-nginx && certbot --nginx -d 你的域名`
4. 更新 `/opt/anime/back-api/.env` 的 `CORS_ORIGINS` 为 `https://你的域名`，重启后端

## 十一、内存不够时的兜底
- 编辑 `anime-backend.service` 把 `MemoryMax` 调小（如 `768M`），或 `--workers 1` 已是最小
- 不编辑代码时停掉 VS Code 远程：`pkill -f vscode-server`（重连会自动拉起）
- 确认没装 Redis、没起第二个 MySQL
