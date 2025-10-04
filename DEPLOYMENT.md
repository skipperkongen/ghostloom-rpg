# 🚀 DigitalOcean Static Site Deployment Guide

This guide will help you deploy your Ghostloom React app to DigitalOcean as a static site.

## 📋 Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- A DigitalOcean account
- Your Supabase project configured

## 🏗️ Build Instructions

### 1. Environment Setup

First, ensure you have your environment variables configured:

```bash
# Copy the example environment file
cp env.example .env

# Edit .env with your Supabase credentials
nano .env
```

Your `.env` file should contain:
```env
VITE_SUPABASE_URL=your_supabase_project_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Build for Production

```bash
npm run build
```

This command will:
- Run TypeScript compilation (`tsc`)
- Build the Vite project for production
- Output optimized files to the `dist/` directory

### 4. Verify Build

After building, you can preview the production build locally:

```bash
npm run preview
```

This will serve the built files from `dist/` at `http://localhost:4173`

## 🌊 DigitalOcean Deployment Options

### Option 1: DigitalOcean App Platform (Recommended)

1. **Connect your repository:**
   - Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
   - Click "Create App"
   - Connect your GitHub/GitLab repository

2. **Configure the app:**
   - **Source Directory:** `/` (root)
   - **Build Command:** `./deploy.sh --platform`
   - **Output Directory:** `dist`
   - **Environment Variables:** Add your Supabase variables:
     - `VITE_SUPABASE_URL`
     - `VITE_SUPABASE_ANON_KEY`

3. **Deploy:**
   - Click "Create Resources"
   - DigitalOcean will automatically build and deploy your app
   - The `--platform` flag tells the deploy script to skip .env file checks and use platform environment variables

### Option 2: DigitalOcean Spaces + CDN

1. **Build locally:**
   ```bash
   npm run build
   ```

2. **Upload to Spaces:**
   - Create a DigitalOcean Space
   - Upload the contents of the `dist/` folder
   - Enable CDN for better performance

3. **Configure custom domain (optional):**
   - Point your domain to the Spaces endpoint
   - Enable SSL certificate

### Option 3: DigitalOcean Droplet (Manual)

1. **Create a Droplet:**
   - Choose Ubuntu 22.04 LTS
   - Add your SSH key

2. **Set up the server:**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install Node.js
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt-get install -y nodejs

   # Install nginx
   sudo apt install nginx -y

   # Clone your repository
   git clone https://github.com/yourusername/ghostloom.git
   cd ghostloom

   # Install dependencies and build
   npm install
   npm run build

   # Configure nginx
   sudo nano /etc/nginx/sites-available/ghostloom
   ```

3. **Nginx configuration:**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       root /home/ubuntu/ghostloom/dist;
       index index.html;

       location / {
           try_files $uri $uri/ /index.html;
       }

       # Enable gzip compression
       gzip on;
       gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
   }
   ```

4. **Enable the site:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/ghostloom /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

## 🔧 Build Script for Automation

The project includes a deployment script (`deploy.sh`) that supports different deployment modes:

### Usage Options:

```bash
# Local deployment (requires .env file)
./deploy.sh

# DigitalOcean App Platform deployment (uses platform environment variables)
./deploy.sh --platform

# Skip environment variable validation
./deploy.sh --skip-env-check

# Show help
./deploy.sh --help
```

### Key Features:

- ✅ **Flexible environment handling**: Works with both `.env` files and platform environment variables
- ✅ **Automatic dependency installation**
- ✅ **Linting with optional override**
- ✅ **Production build optimization**
- ✅ **Build size reporting**
- ✅ **Deployment mode detection**

Make it executable:
```bash
chmod +x deploy.sh
```

## 🔍 Troubleshooting

### Common Issues:

1. **Environment variables not found:**
   - **For local deployment**: Ensure `.env` file exists and contains `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
   - **For platform deployment**: Set environment variables in DigitalOcean App Platform dashboard
   - Variables must start with `VITE_` to be accessible in the browser
   - Use `./deploy.sh --platform` for DigitalOcean App Platform to skip .env file requirements

2. **Build fails with TypeScript errors:**
   - Run `npm run lint` to check for issues
   - Fix any TypeScript errors before building

3. **404 errors on refresh (SPA routing):**
   - Ensure your server is configured to serve `index.html` for all routes
   - Use the nginx configuration above for proper SPA support

4. **Supabase connection issues:**
   - Verify your Supabase URL and anon key are correct
   - Check that your Supabase project is active
   - Ensure your domain is added to Supabase's allowed origins

## 📊 Performance Optimization

Your Vite build already includes:
- ✅ Code splitting
- ✅ Tree shaking
- ✅ Minification
- ✅ Asset optimization

Additional optimizations you can add:

1. **Enable gzip compression** (included in nginx config above)
2. **Set up caching headers** for static assets
3. **Use a CDN** for global distribution
4. **Enable HTTPS** for security

## 🔐 Security Considerations

- Never commit your `.env` file to version control
- Use environment variables for all sensitive configuration
- Enable HTTPS in production
- Regularly update dependencies for security patches

## 📈 Monitoring

Consider setting up:
- Uptime monitoring
- Error tracking (Sentry, LogRocket)
- Performance monitoring
- Analytics (Google Analytics, Plausible)

---

*Happy deploying! May your mystical realm reach adventurers worldwide! ⚔️*
