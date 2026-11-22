# ResearchIQ

ResearchIQ is a split frontend/backend medical-literature assistant. Streamlit provides the UI, FastAPI serves the API, Supabase handles email/Google authentication, Hugging Face Sentence Transformers indexes and retrieves PDF passages, and Groq generates source-grounded analyses.

## Configuration

The backend reads the project-root `.env` file regardless of its working directory. This also avoids falling back to placeholder Supabase settings when the server is started inside `backend/`. Keep real credentials in that file and never commit it. Configure `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `GROQ_API_KEY`, `LLM_PROVIDER=groq`, and `EMBEDDINGS_PROVIDER=huggingface`. The service role key stays server-side and is not needed for the current login flow.

Enable Email and Google under Supabase **Authentication → Providers**. Set the backend's `FRONTEND_URL` to the frontend origin: `http://localhost:8501` for local development, and `https://research-iq1.streamlit.app` on Render. In Supabase **Authentication → URL Configuration → Redirect URLs**, add these exact callback URLs (the `auth_flow` query parameter must be preserved):

- `https://research-iq1.streamlit.app?auth_flow=google`
- `https://research-iq1.streamlit.app?auth_flow=email`
- `http://localhost:8501?auth_flow=google`
- `http://localhost:8501?auth_flow=email`

If you open the local frontend as `http://127.0.0.1:8501`, also allow the matching `127.0.0.1` URLs with both `auth_flow=google` and `auth_flow=email`. Google Cloud's **Authorized JavaScript origins** should contain the frontend origins (the production Streamlit origin and, for local development, `http://localhost:8501`). Its **Authorized redirect URI** is Supabase's callback, `https://<your-project-ref>.supabase.co/auth/v1/callback`; the app's `auth_flow` URLs belong in Supabase's redirect allowlist, not Google's JavaScript origins. Set `CORS_ORIGINS` to the frontend origins you use, including `https://research-iq1.streamlit.app` for the deployed app.

For Streamlit Cloud Secrets, set `RESEARCHIQ_API_URL = "https://researchiq-2oak.onrender.com"`. `BACKEND_URL` is also accepted as an alias. The backend URL must be the live Render service origin, with no `/api` path appended.

Set a long, random `SESSION_COOKIE_PASSWORD` in the project-root `.env`; the frontend uses it to encrypt the Supabase refresh token so it can restore a login after a browser refresh. Keep this value stable across app restarts and private to the server.

## Run the backend

From the project root, create/activate the local environment and install both dependency sets once:

```powershell
cd "D:\Langchain Projects\ResearchIQ2"
if (-not (Test-Path .\venv\Scripts\Activate.ps1)) { python -m venv venv }
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

In PowerShell terminal 1, with the environment activated:

```powershell
cd backend
uvicorn main:app --reload --port 8000
```

The backend uses Hugging Face `sentence-transformers/all-MiniLM-L6-v2` embeddings. On Render, set the service root directory to `backend`, use `pip install -r requirements.txt && python preload_embedding_model.py` as the build command, and set `HF_LOCAL_FILES_ONLY=true` in the service environment. The build downloads and warms the model into `backend/.hf_cache`, which is included in the deployment so paper uploads do not need to download it at runtime. Locally, the model downloads on first use. Paper chunks and normalized vectors are stored with each user's paper records in the configured database. Tables are created automatically. Papers uploaded before the chunk index existed must be uploaded again to be searchable.

## Run the frontend

In PowerShell terminal 2, activate the same environment and start Streamlit:

```powershell
cd "D:\Langchain Projects\ResearchIQ2"
.\venv\Scripts\Activate.ps1
cd frontend
streamlit run streamlit_app.py
```

Open <http://localhost:8501>. The app supports account creation/sign-in, Google OAuth, private paper libraries, semantic search, cited questions, structured summaries, comparisons, cautious research-gap suggestions, Markdown reports, and interaction history.

PDFs must contain selectable text and be under 30 MB. Scanned image PDFs need OCR and are rejected with an explanation. Retrieved excerpts include paper title, filename, and page. Configure Postgres, HTTPS, backups, and private object storage before deployment.
