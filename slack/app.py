import json
import os

import aiohttp
from dotenv import load_dotenv
import logging
from slack_bolt.async_app import AsyncApp
load_dotenv()
from db import get_api_key,del_api_key,store_key,init_db
from structures import build_home,build_explore,build_item,build_leaderboard,build_projects,build_project,build_shop,build_devlog,build_users

init_db()
# This sample slack application uses SocketMode
# For the companion getting started setup guide,
# see: https://docs.slack.dev/tools/bolt-python/getting-started


# Initializes your app with your bot token

app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"), signing_secret=os.getenv("SLACK_SIGNING_SECRET"))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("flavorbot")
async def make_user_request(userid, path, method="GET", text=False, **kwargs):
    result = get_api_key(userid)
    if not result:
        return {} if not text else ""
    flavor_id, api_key = result
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



@app.command("/home")
async def home(ack,respond,body):
    await ack()
    user_id = body['user_id']


    try:
        user_id, api_key = get_api_key(user_id)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        "https://flavortown.hackclub.com/api/v1/users/me",
                        headers={"Authorization": "Bearer " + api_key}
                ) as resp:
                    resp.raise_for_status()
                    user_info = await resp.json()
        except Exception as e:
            log.exception(f"API key validation failed: {e}")
            return
        message = await build_home(True,user_info.get('display_name'))
    except TypeError:

        message = await build_home()

    await respond(text="Home Page",response_type="ephemeral",blocks=message)
@app.action("btn_logout")
async def logout(ack,body,respond):
    await ack()
    user_id = body.get("user", {}).get("id")
    del_api_key(user_id)
    await respond(text="Home Menu",replace_original=True,response_type="ephemeral",blocks=await build_home())
@app.action("search_explore")
@app.action("btn_explore")
async def explore(ack,body,respond):
    await ack()
    user_id = body.get("user",{}).get("id")
    search = body.get("state",{}).get("values",{}).get("search",{}).get("search_explore",{}).get("value")
    await respond(text="Explore",replace_original=True,response_type="ephemeral",blocks=await build_explore(user_id,search))
@app.action("home_back")
async def return_home(ack,body,respond):
    await ack()
    user_id = body.get("user", {}).get("id")
    user_info = await make_user_request(user_id,"/users/me")
    await respond(text="Home",replace_original=True,response_type="ephemeral",blocks=await build_home(True,user_info.get("display_name")))
@app.action("project_select")
async def handle_some_action(ack, body,respond):
    await ack()
    user_id = body.get("user",{}).get("id")
    selected = body.get("state",{}).get("values",{}).get("select",{}).get("project_select",{}).get("selected_option",{}).get("value").split(" ")
    if len(selected) == 2:
        project, back_type = selected
        await respond(text="Project", replace_original=True, response_type="ephemeral",blocks=await build_project(user_id,project, back_type))
    else:
        project, back_type,target_id,page = selected
        await respond(text="Project", replace_original=True, response_type="ephemeral",
                      blocks=await build_project(user_id, project, back_type,target_id,page))

@app.action("link_btn")
@app.action("link1_btn")
@app.action("link2_btn")
async def handle_link(ack):
    await ack()
@app.action("devlog_select-action")
async def handle_devlog_select(ack,body,respond):
    await ack()
    user_id = body.get("user", {}).get("id")
    selected = body.get("state", {}).get("values", {}).get("devlog_select", {}).get("devlog_select-action", {}).get(
        "selected_option", {}).get("value").split(" ")
    if len(selected) == 3:
        devlog,project,back_type = selected
        await respond(text="Home", replace_original=True, response_type="ephemeral",blocks=await build_devlog(user_id,devlog,project,back_type))
    else:
        devlog,project,back_type,target_id,page = selected
        await respond(text="Home", replace_original=True, response_type="ephemeral",blocks=await build_devlog(user_id,devlog,project,back_type,target_id,page))


@app.action("project_back")
async def project_back(ack,body,respond):
    await ack()
    found = body.get("actions",[{}])[0].get("value").split(" ")
    if len(found) == 2:
        project, back_type = found
        user_id = body.get("user", {}).get("id")
        await respond(text="Home", replace_original=True, response_type="ephemeral",blocks=await build_project(user_id,project, back_type))
    else:
        project, back_type,target_id,page = found
        user_id = body.get("user", {}).get("id")
        await respond(text="Home", replace_original=True, response_type="ephemeral",
                      blocks=await build_project(user_id, project, back_type,target_id,page))

@app.action("load_projects")
async def load_projects(ack,body,respond):
    await ack()
    loaded=json.loads(body.get("actions",[{}])[0].get("value"))
    projects = loaded[0]
    target_id,page,back_type = loaded[1]
    if page == -1:
        target_id,page = None,None
    user_id = body.get("user", {}).get("id")
    await respond(text="Projects",replace_original=True,response_type="ephemeral",blocks=await build_projects(user_id,projects,target_id,page,back_type))
@app.action("btn_shop")
async def open_shop(ack,body,respond):
    await ack()
    user_id = body.get("user", {}).get("id")
    await respond(text="Shop",replace_original=True,response_type="ephemeral",blocks=await build_shop(user_id))
@app.action("shop_back")
@app.action("shop_prev")
@app.action("shop_next")
@app.action("toggle_reverse")
async def filter_shop(ack,body,respond):
    await ack()
    user_id = body.get("user", {}).get("id")
    region,page,sort_mode,reverse=body.get("actions",[{}])[0].get("value").split(" ")

    await respond(text="Shop", replace_original=True, response_type="ephemeral", blocks=await build_shop(user_id,region,int(page),sort_mode,reverse == "True"))
@app.action("sort_mode_select")
@app.action("region_select")
async def filter_select_shop(ack,body,respond):
    await ack()
    user_id = body.get("user", {}).get("id")
    region, page, sort_mode, reverse = body.get("actions", [{}])[0].get("selected_option").get("value").split(" ")
    await respond(text="Shop", replace_original=True, response_type="ephemeral", blocks=await build_shop(user_id,region,int(page),sort_mode,reverse == "True"))
@app.action("shop_item_select")
async def filter_select_shop(ack,body,respond):
    await ack()
    user_id = body.get("user", {}).get("id")
    item,region, page, sort_mode, reverse = body.get("actions", [{}])[0].get("selected_option").get("value").split(" ")
    await respond(text="Shop", replace_original=True, response_type="ephemeral", blocks=await build_item(item,region, page, sort_mode, reverse,user_id))


@app.action("btn_login")
async def user_login(ack,body,respond):
    await ack()
    user_id = body.get("user",{}).get("id")
    api_key = body.get("state",{}).get("values",{}).get("block_id",{}).get("box_login",{}).get("value")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    "https://flavortown.hackclub.com/api/v1/users/me",
                    headers={"Authorization": "Bearer " + api_key}
            ) as resp:
                resp.raise_for_status()
                user_info = await resp.json()
    except Exception as e:
        log.exception(f"API key validation failed: {e}")
        return
    store_key(user_id,user_info.get('id'),api_key)
    message = await build_home(True,user_info.get("display_name"))
    await respond(text="Home Menu",replace_original=True,response_type="ephemeral",blocks=message)
@app.action("btn_projects")
async def open_projects(ack,body,respond):
    await ack()
    user_id = body.get("user", {}).get("id")

    await respond(text="Projects",replace_original=True,response_type="ephemeral",blocks=await build_projects(user_id))


@app.action("btn_leaderboard")
async def open_leaderboard(ack,body,respond):
    await ack()
    user_id = body.get("user", {}).get("id")

    await respond(text="Leaderboard",replace_original=True,response_type="ephemeral",blocks=await build_leaderboard(user_id))
@app.action("lb_next")
@app.action("lb_prev")
async def modify_leaderboard(ack,body,respond):
    await ack()
    user_id = body.get("user", {}).get("id")
    page = int(body.get("actions", [{}])[0].get("value"))
    await respond(text="Leaderboard",replace_original=True,response_type="ephemeral",blocks=await build_leaderboard(user_id,page))
@app.action("btn_user_select")
@app.action("user_select")
async def open_user(ack,body,respond):
    await ack()
    user_id = body.get("user", {}).get("id")

    user, page,back_type = (body.get("actions", [{}])[0].get("selected_option",{}).get("value")or body.get("actions", [{}])[0].get("value")).split(" ")
    await respond(text="Leaderboard",replace_original=True,response_type="ephemeral",blocks=await build_projects(user_id,None,user,page,back_type))


@app.action("btn_users")
async def open_users(ack,body,respond):
    await ack()
    user_id = body.get("user",{}).get("id")
    await respond(text="Users",replace_original=True,response_type="ephemeral",blocks=await build_users(user_id))

@app.action("search_users")
async def open_users(ack,body,respond):
    await ack()
    search = body.get("actions", [{}])[0].get("value")
    user_id = body.get("user",{}).get("id")
    await respond(text="Users",replace_original=True,response_type="ephemeral",blocks=await build_users(user_id,1,search))

@app.action("users_next")
@app.action("users_prev")
async def modify_users(ack,body,respond):
    await ack()
    user_id = body.get("user", {}).get("id")
    page = int(body.get("actions", [{}])[0].get("value"))
    await respond(text="Users",replace_original=True,response_type="ephemeral",blocks=await build_users(user_id,page))

@app.command("/hello")
async def command_hello(ack,respond,body,command):

    await ack()
    await respond(f"Hey there <@{body['user_id']}> how are you?",response_type="ephemeral")

if __name__ == "__main__":
    app.start(10000)
