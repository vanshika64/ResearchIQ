# ResearchIQ

ResearchIQ is a split frontend/backend medical-literature assistant. Streamlit provides the UI, FastAPI serves the API, Supabase handles email/Google authentication, Hugging Face Sentence Transformers indexes and retrieves PDF passages, and Groq generates source-grounded analyses.

## Configuration

The backend reads the project-root `.env` file regardless of its working directory. This also avoids falling back to placeholder Supabase settings when the server is started inside `backend/`. Keep real credentials in that file and never commit it. Configure `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `GROQ_API_KEY`, `LLM_PROVIDER=groq`, and `EMBEDDINGS_PROVIDER=huggingface`. The service role key stays server-side and is not needed for the current login flow.

Enable Email and Google under Supabase **Authentication → Providers**. Set `FRONTEND_URL=http://localhost:8501` and add that exact URL to Supabase **Authentication → URL Configuration → Redirect URLs**. The app sends it as the email confirmation redirect and offers a resend button. Supabase will confirm the address and return to the app; the user then signs in with their password. Configure `CORS_ORIGINS` for the frontend origin(s).

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

The first upload downloads the Hugging Face embedding model unless `HF_LOCAL_FILES_ONLY=true` and a local model copy is already cached. It stores normalized chunk vectors with each user's paper records in the configured database. Tables are created automatically. Papers uploaded before the chunk index existed must be uploaded again to be searchable.

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
