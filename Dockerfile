# One container runs everything: the FastAPI server AND all 3 MCP
# servers. This works because our MCP servers use stdio transport —
# meaning the API process spawns them as its own subprocesses, not as
# separate networked services. So they don't need separate containers.
 
FROM python:3.11-slim
 
WORKDIR /app
 
# uv is this project's dependency manager.
RUN pip install --no-cache-dir uv
 
# Copy dependency files FIRST, before the rest of the code. Docker caches
# layers — this means `docker build` only re-installs dependencies when
# pyproject.toml/uv.lock actually change, not on every single code edit.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
 
# Now copy everything else.
COPY . .

# Seed the mock CRM database inside the container. The .dockerignore
# (correctly) excludes the local crm.db, so we generate a fresh one here.
# On Render's free tier there's no persistent disk — this gets re-seeded
# on every deploy, which is fine for a demo project.
RUN python mcp_servers/db_setup.py
 
ENV PATH="/app/.venv/bin:$PATH"
 
EXPOSE 8000
 
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
 
