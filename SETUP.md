# Cursor commands in agent mode

```txt
Setup supabase locally within this project using the supabase CLI using npx
```

```txt
Run the database migration command of Supabase CLI.

Once a new migration file has been created, create the tables to hold the data present in @useFinancialData.ts. Also add seed data for it in the `supabase/seed.sql` file.

Reset the Supabase database once everything is done.
```

```txt
Simplify the dashboard and keep only the header/title, info about email that is logged in, the log out button and the footer 
```

```txt
Create a minimal RPG experience. Not about balance, dice mechanics, stats, or world lore — just:
**Can a player talk to an AI gamemaster and experience meaningful choice, chance, and consequence?**

## ⚙️ 2. Core Loop — The “Minimal Playable”

**One player. One class. One stat. One roll.**

| Element           | Simplest Playable Version                                |
| ----------------- | -------------------------------------------------------- |
| **Character**     | 1 variable: `skill` (number 1–6).                        |
| **Action**        | Player describes intent (e.g. “hack the door”).          |
| **AI Resolution** | AI rolls 1d6. Success if roll ≤ skill.                   |
| **Narration**     | AI describes outcome (success/failure with consequence). |
| **Progression**   | After 3 successful actions, “mission complete.”          |

That’s literally enough to *feel* like an RPG.

---

## 🎮 3. Example Round (Play Loop)

1. **AI (Game Master):**
   “You stand before a locked terminal in a dark corridor. What do you do?”

2. **Player:**
   “I try to hack it.”

3. **AI:**
   *Rolls d6 → 3. Player skill = 4 → success.*
   “The screen flickers to life. You gain access to the system logs. You sense someone is watching...”

4. **Continue until 3 successes → mission ends.**
```