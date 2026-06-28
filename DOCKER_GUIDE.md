# Docker Guide — Running This Project in a Container

A first-time-friendly guide. By the end you'll have built an image and run the
agent as a container, and you'll understand what each step did.

---

## The mental model

- A **Dockerfile** is a recipe — the instructions to build your app's environment.
- An **image** is the finished package — built once from the recipe, containing
  Python + your code + all dependencies. Like a frozen, ready-to-cook meal.
- A **container** is a running instance of an image. You can start, stop, and
  run many containers from one image.

Recipe (Dockerfile) → bake → Image → run → Container.

---

## Step 0 — Install Docker (one time)

Install **Docker Desktop** from docker.com (Windows/Mac) and start it. Verify:

```bash
docker --version
```

If that prints a version number, you're ready.

---

## Step 1 — Build the image

From inside the `compliance-agent/` folder (where the `Dockerfile` is):

```bash
docker build -t compliance-agent .
```

- `-t compliance-agent` names the image "compliance-agent".
- The `.` means "use the Dockerfile in the current folder."

**What happens:** Docker reads the Dockerfile line by line — installs Python,
installs your `requirements.txt`, copies your code, and runs `ingest.py` to
build the vector store *inside* the image. The first build takes a few minutes
(it downloads the embedding model). Later builds are faster because Docker
caches unchanged layers.

When it finishes:
```bash
docker images
```
You'll see `compliance-agent` in the list.

---

## Step 2 — Run the container

```bash
docker run -p 8000:8000 --env-file .env compliance-agent
```

- `-p 8000:8000` connects port 8000 inside the container to port 8000 on your
  machine, so you can reach it in your browser.
- `--env-file .env` passes your `GROQ_API_KEY` into the container (the image
  itself never contains your secret key — good practice).

Now open **http://127.0.0.1:8000/docs** in your browser. You get the same
interactive API as before — but now it's running fully inside the container,
with zero Python setup needed on the host.

To stop it: press `Ctrl+C` in the terminal.

---

## Step 3 — Prove the point (the "why")

The magic of Docker: **this exact image runs identically on any machine** —
your laptop, a colleague's laptop, or a cloud server (AWS/GCP). No "install
Python 3.12, make a venv, pip install, run ingest in the right order." It's all
baked into the image. That's why every production AI service ships as a container.

---

## Common commands you'll actually use

| Command | What it does |
|---|---|
| `docker build -t compliance-agent .` | Build (or rebuild) the image |
| `docker run -p 8000:8000 --env-file .env compliance-agent` | Run it |
| `docker ps` | List running containers |
| `docker ps -a` | List all containers (incl. stopped) |
| `docker stop <id>` | Stop a running container |
| `docker images` | List your images |
| `docker logs <id>` | See a container's output |
| `docker run -it compliance-agent bash` | Open a shell *inside* the container to look around |

---

## Peeking inside the running container (optional, very instructive)

Want to see your chunks from *inside* the container?

```bash
docker run -it compliance-agent bash      # opens a shell inside
python src/inspect_store.py                     # now run the inspector in there
exit                                      # leave the container
```

This shows you the same vector store, but proves it's living inside the image.

---

## Troubleshooting

- **"Cannot connect to the Docker daemon"** → Docker Desktop isn't running.
  Start it and retry.
- **Port already in use** → something else is on 8000. Use a different host
  port: `docker run -p 8080:8000 ...` then open `http://127.0.0.1:8080/docs`.
- **Agent returns errors about the API key** → check your `.env` exists and
  `--env-file .env` is in the run command.
