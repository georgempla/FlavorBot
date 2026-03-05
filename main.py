import os, json
import aiohttp
from bs4 import BeautifulSoup
import db
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

log = logging.getLogger("flavorbot")

load_dotenv()

discord_token = os.getenv("discord_token")

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)
db.init_db()


async def make_user_request(userid, path, method="GET", text=False, **kwargs):
    flavor_id, api_key = db.get_api_key(userid)
    url = path if path.startswith("http") else f"https://flavortown.hackclub.com/api/v1/{path}"
    try:
        async with aiohttp.ClientSession() as session:
            request_method = getattr(session, method.lower())
            async with request_method(url, headers={"Authorization": "Bearer " + api_key}, **kwargs) as resp:
                resp.raise_for_status()
                if text:
                    return await resp.text()
                return await resp.json()
    except Exception as e:
        log.exception(f"fault on endpoint {path} with message: {e}")
        return {} if not text else ""


def seconds_to_hms(seconds):
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02}:{m:02}:{s:02}"

def discord_timestamp(iso_time):
    dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
    unix_ts = int(dt.timestamp())
    return f"<t:{unix_ts}:F>"

def get_entries(html):
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    for user_div in soup.select("div.user"):
        name_tag = user_div.select_one("h2 a")
        cookies_tag = user_div.select_one("p")

        if not name_tag or not cookies_tag:
            continue
        name = name_tag.text.strip()
        user_id = int(name_tag["href"].split("/")[-1])
        cookies = int(cookies_tag.text.split()[0])

        entries.append({
            "id": user_id,
            "name": name,
            "cookies": cookies
        })
    return entries

async def home_menu(interaction):
    embed = discord.Embed(title="Home Page",
                          description="Welcome to the flavortown Home Page! Here you can view the following categories:",
                          color=discord.Color.from_rgb(231, 212, 177))
    embed.add_field(name="Explore", value="Explore exciting projects made by the community for the community",
                    inline=False)
    embed.add_field(name="Projects", value="Check up and work on your projects", inline=False),
    embed.add_field(name="Shop", value="Spend your cookies for amazing rewards", inline=False)
    embed.add_field(name="Leaderboard", value="View the leaderboard and where you rank on there!", inline=False)
    try:
        flavor_id, api_key = db.get_api_key(interaction.user.id)
    except TypeError:
        return embed, apiButton()
    flavor_user = (await make_user_request(interaction.user.id, "users/me")).get("display_name", None)
    embed.set_footer(text=f"Welcome back {flavor_user}!")
    return embed, menuButton()

async def render_project(project_id, userid, mode, **kwargs):
    target_id = kwargs.get("target_id", None)

    project = await make_user_request(userid, f"projects/{project_id}")
    embed = discord.Embed(title=f"{project["id"]} - {project["title"]}",
                          description=f"{project["description"]}\nDevlog IDs:",
                          color=discord.Color.from_rgb(231, 212, 177))
    devlog_options = []
    for i in range(min(24, len(project["devlog_ids"]))):
        log_id = project["devlog_ids"][i]
        embed.add_field(name="", value=log_id,
                        inline=False)
        devlog_options.append(discord.SelectOption(label=f"Devlog - {log_id}", value=log_id))
    embed.add_field(name="",
                    value=f"Created at: {discord_timestamp(project["created_at"])}, Updated at: {discord_timestamp(project["updated_at"])}, Ship status: {project["ship_status"]}",
                    inline=False)
    return embed, projectView(project["repo_url"], project["demo_url"], devlog_options, project_id, mode, target_id=target_id)

async def render_user(target_user, user_id, **kwargs):
    load = kwargs.get("load", False)
    user = await make_user_request(user_id, f"users/{target_user}")
    if not user:
        return None, None
    options = []
    embed = discord.Embed(title=user["display_name"],
                          description="Here are their Projects",
                          color=discord.Color.from_rgb(231, 212, 177))

    projects = user.get("project_ids")
    if load:
        for i in range(min(len(projects), 22)):
            project = await make_user_request(user_id, f"projects/{projects[i]}")
            if not project:
                continue
            id = project.get("id")
            embed.add_field(name=id, value=f"{project.get("title")} - {project.get("description")}",
                            inline=False)
            options.append(discord.SelectOption(label=f"{project.get("title")} - {id}", value=id))
    else:
        for i in range(min(len(projects), 22)):
            embed.add_field(name="", value=projects[i],
                            inline=False)
            options.append(discord.SelectOption(label=f"Project - {projects[i]}", value=projects[i]))
    embed.add_field(name="", value=f"Known on slack with the id {user["slack_id"]}",
                    inline=False)
    embed.add_field(name="", value=f"Cookies: {user.get("cookies")} 🍪 | Votes: {user.get("vote_count")} | Likes: {user.get("like_count")}",
                    inline=False)
    embed.add_field(name="",
                    value=f"Time Logged All time: {seconds_to_hms(user.get("devlog_seconds_total"))} | Time Logged Today: {seconds_to_hms(user.get("devlog_seconds_today"))}",
                    inline=False)
    embed.set_footer(text=f"Remember to have fun!")
    return embed, myProjectSelectView(options, projects, target_user, 2)

async def render_shop(user_id, region, page, sort_mode, reverse):
    shop_items = await make_user_request(user_id, "store")
    if not shop_items:
        return None, None
    options = []
    embed = discord.Embed(title="Shop",
                          description="Here is the shop. View our wide range of items and click on any to view more details. Prices default to the US region change using the menu below,",
                          color=discord.Color.from_rgb(231, 212, 177))
    if sort_mode == "1":
        items = sorted((x for x in shop_items if x["enabled"]["enabled_"+region] and x["show_in_carousel"]), key=lambda x: x["ticket_cost"][region], reverse=reverse)
    else:
        items = sorted((x for x in shop_items if x["enabled"]["enabled_"+region] and x["show_in_carousel"]), key=lambda x: x["name"], reverse=reverse)

    for i in range(min(25, len(items)-(page-1)*25)):
        item = items[i + (page-1)*25]

        if item["enabled"]["enabled_"+region]:
            embed.add_field(name=item["name"], value=f"{item["description"]} - {int(item["ticket_cost"][region])} 🍪",
                            inline=False)
            options.append(discord.SelectOption(label=item["name"], value=item["id"]))

    embed.set_footer(text=f"Remember to have fun!")
    return embed, shopView(options, page, region, sort_mode, reverse)

async def render_item(item_id, userid, region, page, sort_mode, reverse):
    item = await make_user_request(userid, f"store/{item_id}")
    if not item:
        return None, None
    embed = discord.Embed(title=item["name"],
                          description=f"{item["long_description"]}",
                          color=discord.Color.from_rgb(231, 212, 177))
    price = item["ticket_cost"][region]
    embed.add_field(name="",
                    value=f"Price: {price} | ~{price/10} Hours worth of work",
                    inline=False)
    if item["max_qty"]:
        embed.add_field(name="",
                        value=f"You can only buy {item["max_qty"]} at a time",
                        inline=False)
    if item["sale_percentage"]:
        embed.add_field(name="",
                        value=f"This item is {item["sale_percentage"]}% off",
                        inline=False)
    if item["limited"]:
        embed.add_field(name="",
                        value=f"Only {item["stock"]} left in stock",
                        inline=False)
    if item["one_per_person_ever"]:
        embed.add_field(name="",
                        value="This item can only be bought once per person",
                        inline=False)
    if not item["buyable_by_self"]:
        embed.add_field(name="",
                        value="This item cannot be bought by itself",
                        inline=False)
    if not item["enabled"]["enabled_" + region]:
        embed.add_field(name="",
                        value=f"This item cannot be bought in this region ({region})",
                        inline=False)
    if item["type"] == "ShopItem::HQMailItem":
        embed.add_field(name="",
                        value=f"⚠️ This item is shipped from United Kingdom. Customs fees may apply",
                        inline=False)
    embed.set_image(url=item["image_url"])
    embed.set_footer(text=f"Remember to have fun! Note: Upgrades / Ordering are not visible due to API restrictions")

    return embed, itemReturnView(region, page, sort_mode, reverse)

async def render_myprojects(userid, load, **kwargs):
    projects = kwargs.get("projects", None)
    flavor_id, api_key = db.get_api_key(userid)
    embed = discord.Embed(title="Projects",
                          description="Here are your projects, use the menu below to view more details on any project and click the load button to view the titles and descriptions of your projects(Be mindful of ratelimits)!",
                          color=discord.Color.from_rgb(231, 212, 177))
    if not projects:
        user_data = await make_user_request(userid, "users/me")
        if not user_data:
            return None, None
        projects = user_data.get("project_ids")
    options = []

    if load:
        for i in range(min(len(projects), 25)):
            project = await make_user_request(userid, f"projects/{projects[i]}")
            if not project:
                continue
            id = project.get("id")
            embed.add_field(name=id, value=f"{project.get("title")} - {project.get("description")}",
                            inline=False)
            options.append(discord.SelectOption(label=f"{project.get("title")} - {id}", value=id))
    else:
        for i in range(min(len(projects), 25)):
            embed.add_field(name="", value=projects[i],
                            inline=False)
            options.append(discord.SelectOption(label=f"Project - {projects[i]}", value=projects[i]))

    embed.set_footer(text=f"Remember to have fun!")
    return embed, myProjectSelectView(options, projects, flavor_id, 1)

async def render_explore(userid, **kwargs):
    searchterm = kwargs.get("searchterm", None)
    if searchterm:
        projects_data = await make_user_request(userid, f"projects?query={searchterm}")
    else:
        projects_data = await make_user_request(userid, "projects")
    options = []

    embed = discord.Embed(title="Explore",
                          description="Here are some projects we picked for you, use the menu below to view more details on the project!",
                          color=discord.Color.from_rgb(231, 212, 177))
    projects = projects_data.get("projects", [])
    for i in range(min(len(projects), 25)):
        item = projects[i]
        id = item["id"]
        title = item["title"]
        desc = item["description"]
        desc = desc[:197] + "..." if len(desc) > 200 else desc
        embed.add_field(name=id, value=f"{title} - {desc}",
                        inline=False)
        options.append(discord.SelectOption(label=f"{id} - {title}", value=id))

    embed.set_footer(text=f"Remember to have fun!")
    return embed, projectSelectView(options, 0)

async def render_leaderboard(userid, page):
    html = await make_user_request(
        userid,
        f"https://flavortown.hackclub.com/leaderboard?page={page}&limit=25",
        text=True
    )
    options = []
    embed = discord.Embed(title="Leaderboard",
                          description="Here is the leaderboard!",
                          color=discord.Color.from_rgb(231, 212, 177))
    entries = get_entries(html)
    for i, entry in enumerate(entries):
        embed.add_field(name="", value=f"{(page - 1) * 25 + i + 1}. {entry["name"]} - {entry["cookies"]} 🍪",
                        inline=False)
        options.append(discord.SelectOption(label=f"User - {entry["name"]}", value=entry["id"]))

    embed.set_footer(text=f"Remember to have fun!")
    return embed, leaderboardView(options, page)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}(ID:{bot.user.id}")
    bot.add_view(apiButton())
    bot.add_view(menuButton())

    try:
        synched = await bot.tree.sync()
        print(f"Synched {len(synched)} commands")
    except Exception as e:
        print(f"Sync failed with reason: {e}")

class projectReturnView(discord.ui.View):
    def __init__(self, project_id, mode, **kwargs):
        self.project_id = project_id
        self.mode = mode
        self.target_id = kwargs.get("target_id", None)

        super().__init__(timeout=600)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, custom_id="project_back")
    async def explore_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        project_render = await render_project(self.project_id, interaction.user.id, self.mode, target_id=self.target_id)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=project_render[0], view=project_render[1])

class projectDevlogSelect(discord.ui.Select):
    def __init__(self, options, project_id, mode, **kwargs):
        self.project_id = project_id
        self.mode = mode
        self.target_id = kwargs.get("target_id", None)
        super().__init__(
            min_values=1,
            max_values=1,
            options=options,
            placeholder="Devlog id"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        devlog_id = self.values[0]
        devlog = await make_user_request(interaction.user.id, f"devlogs/{devlog_id}")
        if not devlog:
            return
        embed = discord.Embed(title=f"Devlog - {devlog["id"]}",
                              description=f"{devlog["body"]}\nStats:",
                              color=discord.Color.from_rgb(231, 212, 177))
        embed.add_field(name="", value=f"Comments: {devlog["comments_count"]}", inline=False)
        embed.add_field(name="", value=f"Likes: {devlog["likes_count"]}", inline=False)
        embed.add_field(name="", value=f"Coding Time: {seconds_to_hms(devlog["duration_seconds"])}")
        embed.add_field(name="", value=f"Created at: {discord_timestamp(devlog["created_at"])}, Updated at: {discord_timestamp(devlog["updated_at"])}", inline=False)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=projectReturnView(self.project_id, self.mode, target_id=self.target_id))

class projectView(discord.ui.View):
    def __init__(self, git_link, demo_link, devlog_options, project_id, mode, **kwargs):
        self.target_id = kwargs.get("target_id", None)
        super().__init__(timeout=600)
        if git_link:
            self.add_item(discord.ui.Button(
                label="Github",
                url=git_link
            ))
        if demo_link:
            self.add_item(discord.ui.Button(
                label="Demo",
                url=demo_link
            ))
        if devlog_options:
            self.add_item(projectDevlogSelect(devlog_options, project_id, mode, target_id=self.target_id))
        self.mode = mode
        self.project_id = project_id
        if mode != 1:
            self.remove_item(self.update_but)

    @discord.ui.button(label="Update Project", style=discord.ButtonStyle.secondary, custom_id="update")
    async def update_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(updateForm(False, self.project_id))

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, custom_id="project_back")
    async def explore_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if self.mode == 0:
            embed, view = await render_explore(interaction.user.id)
            await interaction.followup.edit_message(message_id=interaction.message.id, view=view, embed=embed)
        elif self.mode == 1:
            embed, view = await render_myprojects(interaction.user.id, False)
            await interaction.followup.edit_message(message_id=interaction.message.id, view=view, embed=embed)
        else:
            embed, view = await render_user(self.target_id, interaction.user.id)
            await interaction.followup.edit_message(message_id=interaction.message.id, view=view, embed=embed)


class projectSelect(discord.ui.Select):
    def __init__(self, options, mode, **kwargs):
        super().__init__(
            min_values=1,
            max_values=1,
            options=options,
            placeholder="Project"
        )
        self.mode = mode
        self.target_id = kwargs.get("target_id")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        project_id = self.values[0]
        project_render = await render_project(project_id, interaction.user.id, self.mode, target_id=self.target_id)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=project_render[0], view=project_render[1])

class projectSelectView(discord.ui.View):
    def __init__(self, options, mode):
        super().__init__(timeout=600)
        self.add_item(projectSelect(options, mode))

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, custom_id="homeback")
    async def explore_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        embed, view = await home_menu(interaction)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

    @discord.ui.button(label="Search", style=discord.ButtonStyle.primary, custom_id="search")
    async def search_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(searchProjectForm())

class updateForm(discord.ui.Modal, title="Enter the details of your project"):
    def __init__(self, create, project_id):
        super().__init__()
        self.create = create
        self.project_id = project_id
        self.title_input = discord.ui.TextInput(
            label="Title",
            placeholder="Flavorbot",
            style=discord.TextStyle.short,
            max_length=200,
            required=create
        )
        self.add_item(self.title_input)
        self.description_input = discord.ui.TextInput(
            label="Description",
            placeholder="Very cool description",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=create
        )
        self.add_item(self.description_input)
        self.repo_url_input = discord.ui.TextInput(
            label="Repo url",
            placeholder="https://www.github.com/...",
            style=discord.TextStyle.short,
            max_length=200,
            required=False
        )
        self.add_item(self.repo_url_input)
        self.demo_url_input = discord.ui.TextInput(
            label="Demo url",
            placeholder="A link to a very cool demo",
            style=discord.TextStyle.short,
            max_length=200,
            required=False
        )
        self.add_item(self.demo_url_input)
        self.readme_url_input = discord.ui.TextInput(
            label="Readme url",
            placeholder="A url to a very cool readme",
            style=discord.TextStyle.short,
            max_length=200,
            required=False
        )
        self.add_item(self.readme_url_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = {
            "demo_url": self.demo_url_input.value,
            "readme_url": self.readme_url_input.value
        }
        if self.title_input.value:
            data["title"] = self.title_input.value
        if self.description_input.value:
            data["description"] = self.description_input.value
        if self.repo_url_input.value:
            data["repo_url"] = self.repo_url_input.value
        if self.demo_url_input.value:
            data["demo_url"] = self.demo_url_input.value
        if self.readme_url_input.value:
            data["readme_url"] = self.readme_url_input.value

        if self.create:
            result = await make_user_request(interaction.user.id, "projects", method="POST", data=data)
        else:
            result = await make_user_request(interaction.user.id, f"projects/{self.project_id}", method="PATCH", data=data)

        if not result:
            log.error(f"Project update/create failed with data: {data}")
            return

        embed, view = await render_myprojects(interaction.user.id, False)
        await interaction.followup.edit_message(message_id=interaction.message.id, view=view, embed=embed)

class myProjectSelectView(discord.ui.View):
    def __init__(self, options, projects, target_id, mode):
        super().__init__(timeout=600)
        if len(options) > 0:
            self.add_item(projectSelect(options, mode, target_id=target_id))
        self.projects = projects
        self.target_id = target_id
        self.mode = mode
        if mode != 1:
            self.remove_item(self.create_but)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, custom_id="homeback")
    async def explore_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        embed, view = await home_menu(interaction)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

    @discord.ui.button(label="Load", style=discord.ButtonStyle.primary, custom_id="load")
    async def search_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if self.mode == 2:
            embed, view = await render_user(self.target_id, interaction.user.id, load=True)
            await interaction.followup.edit_message(message_id=interaction.message.id, view=view, embed=embed)
        else:
            embed, view = await render_myprojects(interaction.user.id, True, projects=self.projects)
            await interaction.followup.edit_message(message_id=interaction.message.id, view=view, embed=embed)

    @discord.ui.button(label="Create Project", style=discord.ButtonStyle.secondary, custom_id="create")
    async def create_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(updateForm(True, 0))


class userSelect(discord.ui.Select):
    def __init__(self, options, mode):
        super().__init__(
            min_values=1,
            max_values=1,
            options=options,
            placeholder="Users"
        )
        self.mode = mode

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = self.values[0]
        embed, view = await render_user(user_id, interaction.user.id)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

class leaderboardView(discord.ui.View):
    def __init__(self, options, page):
        super().__init__(timeout=600)
        self.add_item(userSelect(options, 1))
        self.page = page

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, custom_id="prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if self.page > 1:
            self.page -= 1
        embed, view = await render_leaderboard(interaction.user.id, self.page)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed,
                                                view=view)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, custom_id="homeback")
    async def explore_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        embed, view = await home_menu(interaction)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        self.page += 1
        embed, view = await render_leaderboard(interaction.user.id, self.page)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed,
                                                view=view)

class itemReturnView(discord.ui.View):
    def __init__(self, region, page, sort_mode, reverse):
        self.page = page
        self.region = region
        self.sort_mode = sort_mode
        self.reverse = reverse

        super().__init__(timeout=600)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, custom_id="back")
    async def return_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed, view = await render_shop(interaction.user.id, self.region, self.page, self.sort_mode, self.reverse)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

class regionSelect(discord.ui.Select):
    def __init__(self, page, sort_mode, reverse):
        super().__init__(
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label="United States", value="us"), discord.SelectOption(label="EU", value="eu"), discord.SelectOption(label="United Kingdom", value="uk"), discord.SelectOption(label="India", value="in"), discord.SelectOption(label="Canada", value="ca"), discord.SelectOption(label="Australia", value="au"), discord.SelectOption(label="Rest of World", value="xx")],
            placeholder="Regions"
        )
        self.page = page
        self.sort_mode = sort_mode
        self.reverse = reverse

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        region = self.values[0]
        embed, view = await render_shop(interaction.user.id, region, self.page, self.sort_mode, self.reverse)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

class sortSelect(discord.ui.Select):
    def __init__(self, page, region, reverse):
        super().__init__(
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label="Prices", value=1), discord.SelectOption(label="Alphabetical", value=0)],
            placeholder="Sort"
        )
        self.page = page
        self.region = region
        self.reverse = reverse

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        sort_mode = self.values[0]
        embed, view = await render_shop(interaction.user.id, self.region, self.page, sort_mode, self.reverse)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

class shopSelect(discord.ui.Select):
    def __init__(self, options, region, page, sort_mode, reverse):
        super().__init__(
            min_values=1,
            max_values=1,
            options=options,
            placeholder="Items"
        )
        self.page = page
        self.region = region
        self.sort_mode = sort_mode
        self.reverse = reverse

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        item_id = self.values[0]
        embed, view = await render_item(item_id, interaction.user.id, self.region, self.page, self.sort_mode, self.reverse)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

class shopView(discord.ui.View):
    def __init__(self, options, page, region, sort_mode, reverse):
        super().__init__(timeout=600)
        self.add_item(shopSelect(options, region, page, sort_mode, reverse))
        self.add_item(regionSelect(page, sort_mode, reverse))
        self.add_item(sortSelect(page, region, reverse))
        self.page = page
        self.region = region
        self.sort_mode = sort_mode
        self.reverse = reverse

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, custom_id="prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if self.page > 1:
            self.page -= 1
        embed, view = await render_shop(interaction.user.id, self.region, self.page, self.sort_mode, self.reverse)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, custom_id="homeback")
    async def explore_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        embed, view = await home_menu(interaction)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        self.page += 1
        embed, view = await render_shop(interaction.user.id, self.region, self.page, self.sort_mode, self.reverse)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

    @discord.ui.button(label="Reverse", style=discord.ButtonStyle.secondary, custom_id="reverse")
    async def reverse_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        self.reverse = not self.reverse
        embed, view = await render_shop(interaction.user.id, self.region, self.page, self.sort_mode, self.reverse)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)


class menuButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Explore", style=discord.ButtonStyle.primary, custom_id="explore_but")
    async def explore_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed, view = await render_explore(interaction.user.id)
        await interaction.followup.edit_message(message_id=interaction.message.id, view=view, embed=embed)

    @discord.ui.button(label="Projects", style=discord.ButtonStyle.secondary, custom_id="projects_but")
    async def projects_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed, view = await render_myprojects(interaction.user.id, False)
        await interaction.followup.edit_message(message_id=interaction.message.id, view=view, embed=embed)

    @discord.ui.button(label="Shop", style=discord.ButtonStyle.secondary, custom_id="shop_but")
    async def shop_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed, view = await render_shop(interaction.user.id, "us", 1, 1, False)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

    @discord.ui.button(label="Leaderboard", style=discord.ButtonStyle.success, custom_id="leaderboard_but")
    async def leaderboard_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed, view = await render_leaderboard(interaction.user.id, 1)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

    @discord.ui.button(label="Logout", style=discord.ButtonStyle.danger, custom_id="logout_but")
    async def logout_but(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        db.del_api_key(interaction.user.id)
        await interaction.followup.edit_message(message_id=interaction.message.id, view=apiButton())

class apiButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="API Key", style=discord.ButtonStyle.primary, custom_id="set_key")
    async def set_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(apiForm())

class searchProjectForm(discord.ui.Modal, title="Search for a specific project"):
    search_q = discord.ui.TextInput(
        label="Search",
        placeholder="...",
        style=discord.TextStyle.short,
        max_length=200,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed, view = await render_explore(interaction.user.id, searchterm=self.search_q.value)
        await interaction.followup.edit_message(message_id=interaction.message.id, view=view, embed=embed)

class apiForm(discord.ui.Modal, title="Submit your FlavorTown API Key"):
    key = discord.ui.TextInput(
        label="API Key",
        placeholder="xxxx...",
        style=discord.TextStyle.short,
        max_length=200,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(title="Home Page",
                              description="Welcome to the flavortown Home Page! Here you can view the following categories:",
                              color=discord.Color.from_rgb(231, 212, 177))
        embed.add_field(name="Explore", value="Explore exciting projects made by the community for the community",
                        inline=False)
        embed.add_field(name="Projects", value="Check up and work on your projects", inline=False),
        embed.add_field(name="Shop", value="Spend your cookies for amazing rewards", inline=False)
        embed.add_field(name="Leaderboard", value="View the leaderboard and where you rank on there!", inline=False)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://flavortown.hackclub.com/api/v1/users/me",
                    headers={"Authorization": "Bearer " + self.key.value}
                ) as resp:
                    resp.raise_for_status()
                    user_info = await resp.json()
        except Exception as e:
            log.exception(f"API key validation failed: {e}")
            return

        flavor_user = user_info.get("display_name")
        embed.set_footer(text=f"Welcome back {flavor_user}!")
        await interaction.followup.edit_message(message_id=interaction.message.id, view=menuButton(), embed=embed)
        db.store_key(interaction.user.id, int(user_info.get("id")), self.key.value)


@bot.tree.command(name="home", description="View the home page")
async def home(interaction: discord.Interaction):
    embed, view = await home_menu(interaction)
    await interaction.response.send_message(embed=embed, ephemeral=True, view=view)

bot.run(discord_token)
