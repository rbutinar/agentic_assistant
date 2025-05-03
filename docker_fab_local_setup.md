# 🐳 Agentic Assistant – Local Docker Setup for Microsoft Fabric CLI (`fab`)

This guide explains how to set up and reuse a Docker container named `agentic_assistant` for development with the Microsoft Fabric CLI (`fab`). It includes cleaning old containers, exposing ports for OAuth login, and handling CLI authentication inside Docker.

---

## 📝 TODO
- Translate this guide to English for broader accessibility.

---

## 1️⃣ Clean Any Existing Containers

Before starting, remove any existing container with the same name to avoid conflicts:

```bash
docker rm -f agentic_assistant
```

You can also clean up all stopped containers (optional):

```bash
docker container prune
```

---

## 2️⃣ Run the Docker Container with a Fixed Name and Wide Port Exposure

```bash
docker run --name agentic_assistant \
  -p 8000:8000 \
  -p 127.0.0.1:35000-39999:35000-39999 \
  -it my-app /bin/bash
```

Explanation:

- `--name agentic_assistant` → gives the container a fixed name
- `-p 8000:8000` → exposes the FastAPI/backend service
- `-p 127.0.0.1:35000-39999:35000-39999` → allows Fabric CLI login to succeed regardless of which random port it chooses
- `-it /bin/bash` → gives you an interactive shell inside the container

---

## 3️⃣ Authenticate Inside the Container (`fab auth login`)

**Before authenticating, enable plaintext fallback to avoid encrypted cache errors:**

```bash
fab config set encryption_fallback_enabled true
```

Then authenticate using the Fabric CLI:

```bash
fab auth login
```

- Choose interactive browser mode and complete the login in your browser.
- The wide port exposure in the previous step ensures the OAuth callback will work.

---

## 4️⃣ Reuse the Container in Future Sessions

Instead of rebuilding or re-running:

```bash
docker start -ai agentic_assistant
```

If your Docker image is configured to start the backend and frontend automatically, you do not need to run any additional commands. If you launched the container with `/bin/bash`, and the app is not running yet, you can start it manually:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

To attach another terminal:

```bash
docker exec -it agentic_assistant /bin/bash
```

To stop it when done:

```bash
docker stop agentic_assistant
```

---

## 5️⃣ Debugging & Troubleshooting

- If you see an encrypted cache error, always run the config command above before logging in.
- If you need to re-authenticate, you can remove the container and repeat the process.
- Use the shell to run `fab` commands, inspect logs, or debug as needed.

---

## 🧼 Optional Cleanup Commands

Remove all stopped containers:

```bash
docker container prune
```

Remove all unused images:

```bash
docker image prune -a
```

---

## 📝 Notes

- **Avoid `--network=host` on macOS** — it won’t work with localhost-based redirects due to Docker Desktop’s architecture.
- Once authenticated, your Fabric CLI session should persist unless the token expires.
- This setup is ideal for local development. In production or CI, use service principal login instead.