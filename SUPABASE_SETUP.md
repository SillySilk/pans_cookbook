# Supabase Setup for Pans Cookbook

This guide walks you through setting up Supabase PostgreSQL for your cookbook application.

## Quick Setup (Recommended)

### Step 1: Create Supabase Account
1. Go to [supabase.com](https://supabase.com)
2. Sign up with GitHub/Google
3. Create a new project
4. Choose a project name: `pans-cookbook`
5. Choose a database password (save this!)
6. Select a region (closest to you)

### Step 2: Get Connection Details
After project creation, go to **Settings** → **Database**:

1. **Database URL**: Copy the "Connection string" 
   - Format: `postgresql://postgres:[password]@[host]:5432/postgres`
2. **Direct URL**: This is what you'll use

### Step 3: Set Environment Variables

#### For Local Development:
Create a `.env` file in your cookbook directory:
```env
DATABASE_URL=postgresql://postgres:[YOUR_PASSWORD]@[YOUR_HOST]:5432/postgres
DATABASE_TYPE=postgresql
```

#### For Streamlit Cloud:
Go to your Streamlit Cloud app settings and add:
```toml
[secrets]
DATABASE_URL = "postgresql://postgres:[YOUR_PASSWORD]@[YOUR_HOST]:5432/postgres"
```

### Step 4: Install Dependencies
```bash
pip install psycopg2-binary supabase
```

### Step 5: Test Connection
Run your Streamlit app - it should automatically detect PostgreSQL and show:
```
🗄️ Using database: PostgreSQL (Production/Cloud)
   Host: [your-host].supabase.co
🔧 Initialized POSTGRESQL database service
```

## Manual PostgreSQL Setup (Alternative)

If you prefer local PostgreSQL:

### Install PostgreSQL
- **Windows**: Download from [postgresql.org](https://www.postgresql.org/download/windows/)
- **macOS**: `brew install postgresql`
- **Linux**: `sudo apt install postgresql postgresql-contrib`

### Create Database
```sql
CREATE DATABASE pans_cookbook;
CREATE USER cookbook_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE pans_cookbook TO cookbook_user;
```

### Set Environment Variable
```env
DATABASE_URL=postgresql://cookbook_user:your_password@localhost:5432/pans_cookbook
```

## Features You Get with PostgreSQL

### ✅ Reliability
- **ACID compliance** - No more data loss
- **Consistent connections** - All app components use same database
- **Concurrent users** - Multiple people can use the app simultaneously

### ✅ Performance
- **Optimized queries** - Built-in query optimization
- **Indexing** - Fast searches on ingredients and recipes
- **JSON support** - Efficient storage for recipe metadata

### ✅ Scalability
- **Cloud deployment** - Works perfectly on Streamlit Cloud
- **Data persistence** - Your data survives app restarts
- **Backup & restore** - Built-in data protection

### ✅ Development Experience
- **Web dashboard** - View/edit data directly in Supabase
- **Real-time** - Live updates across sessions
- **SQL access** - Run custom queries when needed

## Troubleshooting

### Connection Issues
1. **Check credentials** - Verify password and host
2. **Check firewall** - Ensure port 5432 is accessible
3. **Check SSL** - Supabase requires SSL connections

### Migration from SQLite
The app will automatically:
1. Detect PostgreSQL availability
2. Create the schema
3. Start fresh with clean data
4. Allow CSV import of your ingredients

### Environment Detection
The app automatically chooses database type:
1. **PostgreSQL** if `DATABASE_URL` is set
2. **PostgreSQL** on Streamlit Cloud
3. **SQLite** for local development fallback

## Next Steps

1. **Set up Supabase** (5 minutes)
2. **Add environment variable** 
3. **Restart your app**
4. **Import your ingredients via CSV**
5. **Add recipes manually or via scraping**

Your cookbook app will now have enterprise-grade reliability!

## Cost
- **Supabase Free Tier**: 500MB database, 50MB file storage
- **Perfect for cookbook app**: Handles thousands of recipes and ingredients
- **Upgrade later**: Only $25/month for unlimited if you grow beyond free tier

The free tier is more than sufficient for a personal cookbook application.