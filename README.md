# ⚔️ Ghostloom - Role Playing Adventures

A mystical role-playing site built with Vite + React and Supabase authentication.

## ✨ Features

- 🏰 **Fantasy-themed UI** with dark, mystical design
- 🔐 **Secure Authentication** powered by Supabase
- ⚡ **Fast Development** with Vite and React
- 📱 **Responsive Design** that works on all devices
- 🎮 **Role-playing Elements** with character status and adventure options

## 🚀 Quick Start

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- A Supabase account

### Setup

1. **Clone and install dependencies:**
   ```bash
   npm install
   ```

2. **Set up Supabase:**
   - Create a new project at [supabase.com](https://supabase.com)
   - Go to Settings > API to get your project URL and anon key
   - Copy `env.example` to `.env` and fill in your Supabase credentials:
     ```bash
     cp env.example .env
     ```
   - Update `.env` with your Supabase URL and anon key

3. **Start the development server:**
   ```bash
   npm run dev
   ```

4. **Open your browser:**
   Navigate to `http://localhost:5173` to see your mystical realm!

## 🎮 Usage

1. **Create an Account:** Click "Create Account" to begin your adventure
2. **Sign In:** Use your email and password to enter the realm
3. **Explore:** Once logged in, you'll see your character dashboard with:
   - Character status and level
   - Adventure options (Combat, Quests, Inventory)
   - Ability to sign out when your adventure is complete

## 🛠️ Development

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## 🎨 Customization

The app features a fantasy theme with:
- Dark gradient backgrounds
- Gold and mystical color schemes
- Role-playing game elements and icons
- Glassmorphism UI components

You can customize the theme by modifying the CSS variables in `src/index.css`.

## 🔧 Tech Stack

- **Frontend:** React 18 + TypeScript
- **Build Tool:** Vite
- **Authentication:** Supabase
- **Styling:** CSS with glassmorphism effects
- **Routing:** React Router (ready for expansion)

## 📜 License

This project is open source and available under the [MIT License](LICENSE).

---

*"In the mystical realm of Ghostloom, every login is a step into legend..."*