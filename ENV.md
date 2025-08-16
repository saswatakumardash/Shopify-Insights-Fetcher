# Environment variables

Use these key/value pairs in your deployment environment.

## Vercel (Gemini-only, copy/paste)

```
GEMINI_API_KEY=YOUR_GEMINI_KEY
GEMINI_MODEL=gemini-2.0-flash-exp
REQUEST_TIMEOUT_SECONDS=12
MAX_PAGES_TO_SCAN=3
USER_AGENT=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36

# Optional persistence
DATABASE_URL=mysql+pymysql://user:pass@host:3306/shopify_insights
PERSIST_ENABLED=true
```

## Alternative provider (Bing)

If you prefer Bing for auto-discovery, set this instead of Gemini:

```
BING_SEARCH_API_KEY=YOUR_BING_KEY
```

Keep the other tuning/persistence variables the same.
