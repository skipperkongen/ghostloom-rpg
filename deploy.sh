#!/bin/bash
# 🚀 Ghostloom Deployment Script
# This script builds the project for production deployment

set -e  # Exit on any error

echo "⚔️  Ghostloom Deployment Script"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found!"
    print_status "Please copy env.example to .env and configure your Supabase credentials:"
    echo "  cp env.example .env"
    echo "  # Then edit .env with your Supabase URL and anon key"
    exit 1
fi

# Check if required environment variables are set
if ! grep -q "VITE_SUPABASE_URL=" .env || ! grep -q "VITE_SUPABASE_ANON_KEY=" .env; then
    print_error "Missing required environment variables in .env file!"
    print_status "Please ensure your .env file contains:"
    echo "  VITE_SUPABASE_URL=your_supabase_project_url"
    echo "  VITE_SUPABASE_ANON_KEY=your_supabase_anon_key"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed!"
    print_status "Please install Node.js (v16 or higher) from https://nodejs.org/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    print_warning "Node.js version is $NODE_VERSION. Recommended version is 16 or higher."
fi

print_status "Node.js version: $(node -v)"
print_status "npm version: $(npm -v)"

# Clean previous build
if [ -d "dist" ]; then
    print_status "Cleaning previous build..."
    rm -rf dist
fi

# Install dependencies
print_status "Installing dependencies..."
npm install

# Run linting
print_status "Running linter..."
if npm run lint; then
    print_success "Linting passed!"
else
    print_warning "Linting found issues. Please fix them before deploying."
    read -p "Continue with build anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Build cancelled. Please fix linting issues first."
        exit 1
    fi
fi

# Build for production
print_status "Building for production..."
if npm run build; then
    print_success "Build completed successfully!"
else
    print_error "Build failed!"
    exit 1
fi

# Check if build output exists
if [ -d "dist" ]; then
    print_success "Build output created in dist/ directory"
    
    # Show build size
    BUILD_SIZE=$(du -sh dist/ | cut -f1)
    print_status "Build size: $BUILD_SIZE"
    
    # List main files
    print_status "Main build files:"
    ls -la dist/
    
    echo ""
    print_success "🎉 Build completed successfully!"
    print_status "Your app is ready for deployment!"
    echo ""
    print_status "Next steps:"
    echo "  1. Upload the contents of the dist/ folder to your hosting provider"
    echo "  2. Ensure your server serves index.html for all routes (SPA routing)"
    echo "  3. Configure your domain to point to the deployed files"
    echo ""
    print_status "For DigitalOcean deployment options, see DEPLOYMENT.md"
    
else
    print_error "Build output not found! Build may have failed."
    exit 1
fi
