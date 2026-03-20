# Flavorbot 

> Built using Bolt for Python for easy integration
## Overview

This is a Slack app built with the [Bolt for Python framework](https://docs.slack.dev/tools/bolt-python/) that showcases responding to events and interactive buttons. Or at least that's what the framework's readme says, but it's so much more than that. It is an intelligent integration of the Flavortown API that provides a usable UI within Slack for maximum convenience, this way you never have to leave your conversations to use Flavortown.

## Features

- **Home** Your main menu,from here you access all of Flavortown. To open it simply run the /home command. Use the search bar to find specific projects
- **Explore** Explore exciting projects made by the community for the community!
- **Projects** Check up and work on your amazing projects! To fully view them use the load button, but be mindful of ratelimits as it makes a request per project
- **Shop** Spend your cookies for amazing rewards! One of the perks of this program 😉. You can't actually order anything from here due to security limitations.
- **Leaderboard** Visit the leaderboard and see where you rank on there. You can see what you are doing right or wrong by comparing your projects to the most accomplished of us.
- **Users** Find users within your community and compare your cookies! This way you can see what the average user does. Use the search bar to find specific people.
- **User Profiles** Look at specific profiles and find out their cookies, slack IDs, spent time coding and their projects.
- **Devlogs** View details on the devlogs (body, comments, likes, coding time)
- **API Key Management** We securely encrypt your API keys and never share them with the client side for maximum security.


## Running locally

### 1. Setup environment variables

```env
# Replace with your tokens
SLACK_BOT_TOKEN=<your-bot-token>
SLACK_APP_TOKEN=<your-app-level-token>
SLACK_SIGNING_SECRET=<your-slack-signing-secret>
enc_key=<an-encryption-key-generated-by-you>
#Only Include if you are using the dynamodb database
aws_access_key_id=<an-access-id-for-aws>
aws_secret_access_key=<a-secret-access-key-for-aws>
```

### 2. Setup your local project

```zsh
# Clone this project onto your machine
git clone https://github.com/slack-samples/bolt-python-getting-started-app.git

# Change into this project
cd flavorbot/

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install the dependencies
pip install -r requirements.txt
```

### 3. Start servers

```zsh
python3 lambda_function.py
```

### 4. Expose your endpoint (I prefer ngrok)
```zsh
ngrok http 10000
```

## Project Structure

```
.
├── app.py      
├── db.py 
├── structures.py       
├── .env         
└── README.md
```

### Shop Filters
- **Region** US, EU, UK, India, Canada, Australia, Rest of World
- **Sort** By price/alphabetically
- **Reverse** Reverse the sort direction
- **Previous/Next** Paginate through items

## Notes

- All interactions are ephemeral (only visible to the user who triggered them).
