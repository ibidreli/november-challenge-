# Render Deployment Guide

This guide helps you deploy the November Challenge application to Render.

## Database Configuration

### Important: Use External Database URL

Render provides two types of database URLs:
- **Internal URL**: `postgresql://user:pass@dpg-xxxxx-a/dbname` (only works within Render's internal network)
- **External URL**: `postgresql://user:pass@dpg-xxxxx-a.region-postgres.render.com/dbname` (publicly accessible)

**The application now automatically converts internal Render URLs to external URLs**, but for best practices, you should set the external URL directly in your Render environment variables.

### Setting Environment Variables in Render

In your Render Web Service dashboard:

1. Go to **Environment** tab
2. Set the following variables:

```bash
# Database (use EXTERNAL URL from your Render PostgreSQL dashboard)
DATABASE_URL=postgresql://admin:E9XMFQ4IIpA6NjTCiHHXuRw2YVN6WC5R@dpg-d3nnp7mr433s73bmb96g-a.oregon-postgres.render.com/novemberchallenge

# Postgres settings (optional - mainly for reference)
POSTGRES_DB=novemberchallenge
POSTGRES_HOST=dpg-d3nnp7mr433s73bmb96g-a.oregon-postgres.render.com
POSTGRES_PASSWORD=E9XMFQ4IIpA6NjTCiHHXuRw2YVN6WC5R
POSTGRES_PORT=5432
POSTGRES_USER=admin

# Database requirements
REQUIRE_POSTGRES=1
ALLOW_SQLITE_FALLBACK=0

# Challenge month (10 for October, 11 for November)
CHALLENGE_MONTH=10

# Strava OAuth configuration
STRAVA_CLIENT_ID=180756
STRAVA_CLIENT_SECRET=c3b746f060158cdb5efb7efb0ddbef576180e7e6
STRAVA_REDIRECT_URI=https://november-challenge.onrender.com/auth/callback
```

### Important Notes

1. **DATABASE_URL**: Copy the **External Database URL** from your Render PostgreSQL service dashboard
   - Find it under "Connections" → "External Database URL"
   - It should end with `.oregon-postgres.render.com` (or another region)

2. **REQUIRE_POSTGRES=1**: Ensures the app fails fast if PostgreSQL is not configured correctly

3. **ALLOW_SQLITE_FALLBACK=0**: Prevents falling back to SQLite in production

4. **STRAVA_REDIRECT_URI**: Must match your backend URL + `/auth/callback`

## Strava OAuth Configuration

Make sure your Strava application settings match:

1. Go to https://www.strava.com/settings/api
2. Set **Authorization Callback Domain** to your Render domain: `november-challenge.onrender.com`
3. The full redirect URI in your app should be: `https://november-challenge.onrender.com/auth/callback`

## CORS Configuration

If your frontend is hosted separately (e.g., at `november-challenge-1.onrender.com`), you may need to update CORS settings in `backend/main.py`.

## Troubleshooting

### Database Connection Issues

If you see errors like:
- "could not translate host name"
- "Connection refused"
- "No address associated with hostname"

**Solution**: Ensure you're using the **External Database URL** (with the full domain like `.oregon-postgres.render.com`)

### Strava OAuth Redirect Issues

If the Strava callback doesn't work:

1. Check `STRAVA_REDIRECT_URI` matches exactly what's in Strava API settings
2. Ensure the redirect URI uses `https://` (not `http://`)
3. Check Render logs for any errors during the callback

### Check Database Connection

Use the `/debug/db_info` endpoint to verify your database configuration:

```bash
curl https://november-challenge.onrender.com/debug/db_info
```

This will show:
- Which database URL is being used (with password masked)
- Database type (sqlite vs postgres)
- Table counts

## Deployment Checklist

- [ ] PostgreSQL database created in Render
- [ ] External Database URL copied to `DATABASE_URL` environment variable
- [ ] `REQUIRE_POSTGRES=1` set
- [ ] `ALLOW_SQLITE_FALLBACK=0` set
- [ ] Strava Client ID and Secret configured
- [ ] Strava Redirect URI matches your Render backend URL
- [ ] Strava API settings updated with correct callback domain
- [ ] Web service deployed and running
- [ ] Test `/healthz` endpoint returns `{"status": "ok"}`
- [ ] Test `/debug/db_info` shows postgres connection
- [ ] Test Strava login flow works
