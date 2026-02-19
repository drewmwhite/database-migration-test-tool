# Docker SQL Server Setup Guide

A step-by-step guide to running SQL Server in Docker with SSMS — designed for spinning up and down for local development and data migration projects.

---

## Prerequisites

- Docker Desktop installed and running
- SSMS installed on your Windows machine (SSMS runs on the host, not in the container)

---

## Step 1: Pull the SQL Server Docker Image

```bash
docker pull mcr.microsoft.com/mssql/server:2022-latest
```

> Swap `2022-latest` for `2019-latest` if you prefer an older version.

---

## Step 2: Run the Container

```bash
docker run -e 'ACCEPT_EULA=Y' \
  -e 'MSSQL_SA_PASSWORD=YourStrong!Passw0rd' \
  -e 'MSSQL_ENABLE_HADR=0' \
  -p 1433:1433 \
  --name sql_server_dev \
  --hostname sql_server_dev \
  -d mcr.microsoft.com/mssql/server:2022-latest
```

| Flag | Purpose |
|---|---|
| `-e 'ACCEPT_EULA=Y'` | Accepts the license agreement (required) |
| `-e 'MSSQL_SA_PASSWORD=...'` | Sets the SA password (must meet complexity requirements) |
| `-e 'MSSQL_ENABLE_HADR=0'` | Prevents the SA account from being disabled on first run (SQL Server 2022 quirk) |
| `-p 1433:1433` | Maps host port 1433 to container port 1433 |
| `--name sql_server_dev` | Gives the container a friendly name |
| `-d` | Runs detached (in the background) |

> **Note:** Always use single quotes around `-e` values on Linux. Double quotes cause the shell to interpret special characters like `!`, which will silently corrupt your password.

---

## Step 3: Verify the Container is Running

```bash
docker ps
```

You should see `sql_server_dev` in the list with status `Up`. If something went wrong, check the logs:

```bash
docker logs sql_server_dev
```

---

## Step 4: Connect via SSMS

Open SSMS and use the following connection details:

| Field | Value |
|---|---|
| Server type | Database Engine |
| Server name | `localhost,1433` |
| Authentication | SQL Server Authentication |
| Login | `sa` |
| Password | `YourStrong!Passw0rd` |

> **Note:** SSMS uses a comma before the port, not a colon — `localhost,1433`.

### Connection Strings

**ADO.NET**
```
Server=localhost,1433;Database=YourDatabase;User Id=sa;Password=YourStrong!Passw0rd;TrustServerCertificate=True;
```

**ODBC**
```
Driver={ODBC Driver 18 for SQL Server};Server=localhost,1433;Database=YourDatabase;UID=sa;PWD=YourStrong!Passw0rd;TrustServerCertificate=yes;
```

**JDBC**
```
jdbc:sqlserver://localhost:1433;databaseName=YourDatabase;user=sa;password=YourStrong!Passw0rd;trustServerCertificate=true;
```

> **Note:** `TrustServerCertificate=True` is needed because the container uses a self-signed certificate. Replace `YourDatabase` with your actual database name.

---

## Step 5: Persist Your Data

By default, data is lost when the container is removed. Mount a volume so your databases survive restarts:

```bash
docker run -e 'ACCEPT_EULA=Y' \
  -e 'MSSQL_SA_PASSWORD=YourStrong!Passw0rd' \
  -e 'MSSQL_ENABLE_HADR=0' \
  -p 1433:1433 \
  --name sql_server_dev \
  --hostname sql_server_dev \
  -v sqlserver_data:/var/opt/mssql \
  -d mcr.microsoft.com/mssql/server:2022-latest
```

The `-v sqlserver_data:/var/opt/mssql` flag creates a named Docker volume that persists even when the container is stopped or removed.

---

## Step 6: Spin Up and Down

| Action | Command |
|---|---|
| Stop the container (data preserved) | `docker stop sql_server_dev` |
| Start the container back up | `docker start sql_server_dev` |
| Remove the container (volume persists) | `docker rm sql_server_dev` |
| Remove the volume too (full reset) | `docker volume rm sqlserver_data` |

---

## Step 7: Docker Compose (Recommended)

For a migration project you'll want to check this into source control. Create a `docker-compose.yml` file in your project root:

```yaml
version: '3.8'

services:
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    container_name: sql_server_dev
    environment:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: "YourStrong!Passw0rd"
      MSSQL_ENABLE_HADR: "0"
    ports:
      - "1433:1433"
    volumes:
      - sqlserver_data:/var/opt/mssql

volumes:
  sqlserver_data:
```

Then use these commands to manage the environment:

| Action | Command |
|---|---|
| Start | `docker compose up -d` |
| Stop (keeps data) | `docker compose stop` |
| Tear down (remove containers) | `docker compose down` |
| Tear down + delete volume (full reset) | `docker compose down -v` |

---

## Tips for Your Migration Project

**Mount your scripts folder**

Add a volume for your SQL scripts in `docker-compose.yml` so you can run them directly inside the container:

```yaml
volumes:
  - sqlserver_data:/var/opt/mssql
  - ./scripts:/scripts
```

**Run a script inside the container**

```bash
docker exec -it sql_server_dev /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P 'YourStrong!Passw0rd' \
  -i /scripts/your_script.sql
```

**Two databases for migration testing**

Both a source and target database can live in the same container instance — just create two separate databases in SSMS.

**Keep secrets out of source control**

Never commit your SA password. Use a `.env` file with Docker Compose and add it to `.gitignore`:

```env
# .env
MSSQL_SA_PASSWORD=YourStrong!Passw0rd
```

Then reference it in `docker-compose.yml`:

```yaml
environment:
  ACCEPT_EULA: "Y"
  MSSQL_SA_PASSWORD: ${MSSQL_SA_PASSWORD}
  MSSQL_ENABLE_HADR: "0"
```

---

## Troubleshooting

### "Login failed for user 'sa'" (Error 18456, State 7)

This is a known SQL Server 2022 Docker quirk where the SA account is created in a disabled state on first run. The container is healthy and accepting connections — it's just the login that's locked out. You'll see this in the logs:

```
Login failed for user 'sa'. Reason: An error occurred while evaluating the password. [CLIENT: 172.17.0.1]
```

The fix is to include `-e 'MSSQL_ENABLE_HADR=0'` in your `docker run` command (already included in the commands above). If you're already hitting this on an existing container, the cleanest fix is a full reset:

```bash
docker stop sql_server_dev
docker rm sql_server_dev
docker volume rm sqlserver_data
```

Then re-run the container command from Step 5. After startup, confirm it's healthy:

```bash
docker logs sql_server_dev | tail -20
```

You should see `SQL Server is now ready for client connections` with no login errors at the bottom.

### Password being silently corrupted (special characters)

On Linux, double quotes allow the shell to interpret special characters. The `!` in `YourStrong!Passw0rd` will be stripped out silently, leaving you with a password that doesn't meet SQL Server's complexity requirements. Always use **single quotes** around `-e` values:

```bash
# Wrong - shell interprets !
-e "MSSQL_SA_PASSWORD=YourStrong!Passw0rd"

# Correct - single quotes pass the value as-is
-e 'MSSQL_SA_PASSWORD=YourStrong!Passw0rd'
```

### Nuclear Option — Wipe Everything and Start Fresh

If things are in a broken state and you want a completely clean slate:

```bash
# Stop and remove the container
docker stop sql_server_dev
docker rm sql_server_dev

# Remove the data volume
docker volume rm sqlserver_data

# Remove the pulled image entirely (forces a fresh pull)
docker rmi mcr.microsoft.com/mssql/server:2022-latest

# Optional: prune any other dangling Docker resources
docker system prune -f

# Pull a fresh image and start again from Step 1
docker pull mcr.microsoft.com/mssql/server:2022-latest
```

After this, follow from Step 5 to recreate the container. Everything — container, data, and image — will be gone.

### Confirm the container is reachable before connecting via SSMS

Always use `localhost,1433` (comma, not colon) in SSMS. The colon format will result in a network error that has nothing to do with your credentials.