# FlavorBot

A discord.py bot for interacting with the [flavortown](https://flavortown.hackclub.com) platform. Browse projects, manage your own, explore items in the shop and see the leaderboard, all with one discord command.

## Features

- **Home** The main area, here you can view and navigate to all the diffrent sections of the platform. Just log in and enjoy.
- **Explore** Browse projects by the community for the community and even search through them.
- **Projects** View and manage all of your projects. Load their descriptions, create new ones, or update existing ones.
- **Shop** Browse the FlavorTown store and use region filters, price/alphabetical sorting, reversing order, and pagination
- **Leaderboard** View the cookie leaderboard with pagination and click through at any user's profile
- **User Profiles** View any user's projects, stats(cookies, votes, likes), logged time and Slack ID.
- **Devlogs** View devlog details (body, comments, likes, coding time) from within a project view.
- **API Key Management** Securely submit and store your FlavorTown API key. Logout supported.

## Demo
To test out this bot use this invite link: https://discord.gg/9TFfvAsktj

## Prerequisites

- Python 3.11+
- A Discord bot token
- A FlavorTown API key

## Installation

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd <your-repo>
   ```

2. Install dependencies:
   ```bash
   pip install discord.py aiohttp python-dotenv beautifulsoup4 cryptography
   ```

3. Create a `.env` file in the project root:
   ```
   discord_token=your_discord_bot_token_here
   enc_key=your_encryption_key
   ```

4. Make sure `db.py` is present and initialises correctly.

5. Run the bot:
   ```bash
   python main.py
   ```

## Usage

Use the `/home` slash command to open the home page. From there, all navigation is done through buttons and dropdown menus in ephemeral (private) messages.

### Logging In
Click **API Key** and submit your FlavorTown API key. The bot will validate it and store it linked to your Discord account.

### Navigation
| Button | Description |
|---|---|
| Explore | Browse all community projects, with search |
| Projects | View and manage your own projects |
| Shop | Browse the store by region and sort order |
| Leaderboard | View the cookie leaderboard |
| Logout | Remove your stored API key |

### Shop Filters
- **Region** US, EU, UK, India, Canada, Australia, Rest of World
- **Sort** By price or alphabetically
- **Reverse** Flip the sort direction
- **Previous / Next** - Paginate through items

## Project Structure

```
.
├── main.py       # Bot logic, commands, views, and API interactions
├── db.py         # Database layer 
├── .env          # Discord token (not committed)
└── README.md
```

## Notes

- All interactions are ephemeral (only visible to the user who triggered them).
- The bot uses persistent views (`timeout=None`) for the login and main menu buttons, meaning they survive bot restarts.
- Be mindful of FlavorTown API rate limits when using the **Load** button in Projects, as it fires one request per project.