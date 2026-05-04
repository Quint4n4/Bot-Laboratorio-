# ARIA Dashboard

Dashboard web minimalista para el asistente personal ARIA (Telegram bot).
Muestra agenda, completados, conversaciones y sugerencias proactivas.

## Stack

- **Streamlit** — UI declarativa en Python puro
- **SQLAlchemy** — lectura de la misma base Postgres del bot
- **Plotly** — charts (heatmap, donut, line)
- **HMAC magic-link auth** — el bot genera URLs firmadas, el dashboard las valida

## Estructura

```
dashboard/
├── app.py                       Entry point (auth + navigation)
├── auth.py                      HMAC tokens
├── db.py                        Modelos SQLAlchemy (espejo del bot)
├── theme.py                     Paleta + CSS global
├── recurrence_helper.py         describe_rule (espejo de bot-agenda/recurrence.py)
├── pages/
│   ├── home.py                  KPIs + agenda hoy + sugerencias
│   ├── agenda.py                Filtro por categoría, próximos 30 días
│   ├── completados.py           Heatmap + donut + lista
│   └── conversaciones.py        Log de chats con búsqueda
├── .streamlit/config.toml       Theme settings
└── requirements.txt
```

## Variables de entorno requeridas

| Variable | Para qué |
|---|---|
| `DB_URL_REAL` | URL Postgres compartida con el bot (Supabase pooler 6543) |
| `DASHBOARD_SECRET` | Secreto HMAC; debe coincidir con el del bot |

## Deploy en Streamlit Community Cloud

1. Push el repo a GitHub (ya está en `main`)
2. https://share.streamlit.io → **New app**
3. Repo: `Quint4n4/Bot-Laboratorio-`
4. Branch: `main`
5. Main file path: `dashboard/app.py`
6. Advanced settings → **Secrets**:
   ```
   DB_URL_REAL = "postgresql://postgres.xxxxx:PASSWORD@aws-x-xx.pooler.supabase.com:6543/postgres"
   DASHBOARD_SECRET = "<misma cadena que en Railway>"
   ```
7. Deploy. La URL queda algo como `https://aria-dashboard.streamlit.app`

## Uso desde el bot

El usuario manda `/dashboard` en Telegram. El bot genera un enlace firmado:

```
https://aria-dashboard.streamlit.app/?token=<id>:<expires>:<hmac>
```

El token expira en 24h. Si caduca, el dashboard muestra "Sesión no válida"
y le pide al usuario un link nuevo.

## Probar localmente

```bash
cd dashboard
pip install -r requirements.txt
export DB_URL_REAL="..."
export DASHBOARD_SECRET="dev-secret-string"
streamlit run app.py
```

Luego entra a `http://localhost:8501/?token=<token>` con un token generado vía:

```python
from auth import make_token
print(make_token("TU_TELEGRAM_ID"))
```

## Diseño

- **Estilo**: Exaggerated Minimalism — mucho whitespace, jerarquía por tamaño/peso
- **Paleta**: monocromo (#FAFAFA → #0A0A0A) + acento azul (#3B82F6)
- **Tipografía**: Inter (UI) + JetBrains Mono (números tabulares)
- **Categorías**: 7 dots de color identificadores (no saturan, no compiten con el contenido)
