import asyncio
import json

import aiohttp
from datetime import datetime
from bs4 import BeautifulSoup
from db import get_api_key
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("flavorbot")
async def make_user_request(userid, path, method="GET", text=False, **kwargs):
    result = get_api_key(userid)
    print(result)
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
def slack_timestamp(iso_time):
    dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
    return dt.strftime("%B %d, %Y at %I:%M %p UTC")
def seconds_to_hms(seconds):
    if not seconds:
        seconds = 0
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02}:{m:02}:{s:02}"
def get_entries(html):
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    for user_div in soup.select("div.user"):
        name_tag = user_div.select_one("h2 a")
        cookies_tag = user_div.select_one("p")
        img_tag = user_div.select_one("img")

        if not name_tag or not cookies_tag:
            continue
        name = name_tag.text.strip()
        print()
        user_id = int(name_tag["href"].split("/")[-1])
        cookies = int(cookies_tag.text.split()[0])

        entries.append({
            "id": user_id,
            "name": name,
            "cookies": cookies,
            "icon":img_tag["src"]
        })

    return entries
async def build_home(loggedin=False, username="TestUser"):
    message = [
        {"type": "header","text": {"type": "plain_text","text": "Home Page"}},
		{"type": "section","text": {"type": "mrkdwn","text": "Welcome to the flavortown Home Page! Here you can view the following categories:"}},
		{"type": "divider"},
		{"type": "section","text": {"type": "mrkdwn","text": "*Explore*\n Explore exciting projects made by the community for the community!"},"accessory": {"type": "image","image_url": "https://cdn.hackclub.com/019cf0f5-a725-770c-9159-f2235f73d3b2/explore_icon.png","alt_text": "explore icon"}},
		{"type": "divider"},
		{"type": "section","text": {"type": "mrkdwn","text": "*Projects*\n Check up and work on your amazing projects!"},"accessory": {"type": "image","image_url": "https://user-cdn.hackclub-assets.com/019cf0fe-86b6-70d1-9e2e-662086f4b8c4/projects.png","alt_text": "projects icon"}},
		{"type": "divider"},
		{"type": "section","text": {"type": "mrkdwn","text": "*Shop*\n Spend your cookies for amazing rewards! One of the perks of this program 😉"},"accessory": {"type": "image","image_url": "https://cdn.hackclub.com/019cf0fe-e40d-7d0f-aa93-921cc8154f57/shop.png","alt_text": "shop icon"}},
		{"type": "divider"},
		{"type": "section","text": {"type": "mrkdwn","text": "*Leaderboard*\n Visit the leaderboard and see where you rank on there."},"accessory": {"type": "image","image_url": "https://cdn.hackclub.com/019d0c0e-32a8-7924-8971-f618a8eb4f44/leaderboard.png","alt_text": "leaderboard icon"}},
		{"type": "divider"},
        {"type": "section",
         "text": {"type": "mrkdwn", "text": "*Users*\n Find users within your community and compare your cookies!"},
         "accessory": {"type": "image",
                       "image_url": "https://cdn.hackclub.com/019d0c0d-ee76-7649-97c1-38f87b534cb4/users.png",
                       "alt_text": "users icon"}},
        {"type": "divider"}
    ]
    if loggedin:
        message.append({
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"Welcome back {username}!"
			}
		})
        message.append(
            {"type": "actions",
             "elements": [
                 {"type": "button", "text": {"type": "plain_text", "text": "Explore", "emoji": True},
                  "value": "open_explore", "action_id": "btn_explore"},
                 {"type": "button", "text": {"type": "plain_text", "text": "Projects", "emoji": True},
                  "value": "open_projects", "action_id": "btn_projects"},
                 {"type": "button", "text": {"type": "plain_text", "text": "Shop", "emoji": True}, "value": "open_shop",
                  "action_id": "btn_shop"
                  },
                 {"type": "button", "text": {"type": "plain_text", "text": "Leaderboard", "emoji": True},
                  "value": "open_leaderboard", "action_id": "btn_leaderboard"},
                 {"type": "button", "text": {"type": "plain_text", "text": "Users", "emoji": True},
                  "value": "open_users", "action_id": "btn_users"},
                 {"type": "button", "text": {"type": "plain_text", "text": "Logout", "emoji": True}, "value": "logout",
                  "action_id": "btn_logout"
                  }
             ]})
    else:
        message.append(
            {
                "type": "input",
                "block_id": "block_id",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "box_login"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Enter your Flavortown API key here!",
                    "emoji": True
                },
                "optional": False
            })
        message.append(
            {"type": "actions",
             "elements": [
                 {"type": "button", "text": {"type": "plain_text", "text": "Login", "emoji": True}, "value": "login",
                  "action_id": "btn_login"}]})
    return message
async def build_explore(userid, search=None):
    if search:
        path = f"projects?query={search}"
    else:
        path = "projects"
    projects = await make_user_request(userid,path)
    message = [
		{
			"type": "header",
			"text": {'type': 'plain_text', 'text': 'Explore'}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "Here are some projects we picked for you, use the menu below to view more details on any project!"
			}
		},
		{
			"type": "divider"
		}
    ]
    options = []
    for project in projects.get("projects",[])[:10]:
        message.append({
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"*{project.get('id',0)}. {project.get('title',"TestTitle")}*\n {project.get('description','TestDesc')}"
			},
			"accessory": {
				"type": "image",
                "image_url": "https://flavortown.hackclub.com" + (
                            project.get('banner_url') or '/assets/default-banner-3d4e1b67.png'),
                "alt_text": "item icon"
			}
		})
        message.append({
			"type": "divider"
		})
        options.append({
						"text": {
							"type": "plain_text",
							"text": f"{project.get('id',0)}. {project.get('title',"TestTitle")}",
							"emoji": True
						},
						"value": str(project.get('id',0)) + " explore"
					})
    if search:
        message.append({
                "dispatch_action": True,
                "type": "input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "search_explore",
                    "initial_value": search

                },
                "label": {
                    "type": "plain_text",
                    "text": "Search",
                    "emoji": True
                },
                'block_id':"search",
                "optional": False
            })
    else:
        message.append({
            "dispatch_action": True,
            "type": "input",
            "element": {
                "type": "plain_text_input",
                "action_id": "search_explore"

            },
            "label": {
                "type": "plain_text",
                "text": "Search",
                "emoji": True
            },
            'block_id': "search",
            "optional": False
        })
    message.append({
			"type": "actions",
            'block_id': "select",
			"elements": [{
				"type": "static_select",
				"placeholder": {
					"type": "plain_text",
					"text": "Select a project",
					"emoji": True
				},
				"options": options,

				"action_id": "project_select"
			},
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Back",
                        "emoji": True
                    },
                    "value": "go_back",
                    "action_id": "home_back"
                }
            ],

		})
    return message
async def build_project(userid,project_id,back_type,target_id=None,page=None):
    project_info = await make_user_request(userid, f"/projects/{project_id}")
    message = [
		{'type': 'header', 'text': {'type': 'plain_text', 'text': f" {project_info.get("id",0)}. {project_info.get('title',"TestTitle")}"
		}},
		{
			"type": "image",
			"image_url": "https://flavortown.hackclub.com" + (
                            project_info.get('banner_url') or '/assets/default-banner-3d4e1b67.png'),
			"alt_text": "item icon"
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": project_info.get("description") if project_info.get("description") != '' else "N/A"
			}
		},
		{
			"type": "divider"
		}]
    if project_info.get('ai_declaration'):
        message.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*AI Declaration:*\n {project_info.get('ai_declaration')}"
            }
        })
        message.append({
            "type": "divider"
        })
    message.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*Devlogs:*"
        }
    })
    options = []
    for devlog in project_info.get('devlog_ids',[])[:5]:
        message.append({
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"Devlog {devlog}"
			}
		})
        options.append({
            "text": {
                "type": "plain_text",
                "text": f"Devlog {devlog}",
                "emoji": True
            },
            "value": str(devlog)+" "+str(project_id)+" "+back_type+ ((" " + str(target_id)+" "+str(page)) if target_id else "")
        })
    message.append({
			"type": "divider"
		})
    message.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"Created at: {slack_timestamp(project_info.get("created_at"))}\nUpdated at: {slack_timestamp(project_info.get("updated_at"))}\nShip status: {project_info.get("ship_status")}"
        }
    })
    message.append({
        "type": "divider"
    })
    back_action_id = ""
    if back_type == "explore":
        back_action_id = "btn_explore"
    elif back_type == "projects":
        back_action_id = "btn_projects"
    elif back_type == "leaderboard"or back_type == "users":
        back_action_id = "btn_user_select"
    elements = [{
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "Back",
						"emoji": True
					},
					"value": target_id+" "+page+" "+back_type if target_id else "go_back",
					"action_id": back_action_id
				}]
    if project_info.get("demo_url"):
        elements.append(
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Demo",
                    "emoji": True
                },
                "value": "demo",
                "url": project_info.get("demo_url"),
                "action_id": "link_btn"
            }
        )
    if project_info.get("repo_url"):
        elements.append(
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Repo",
                    "emoji": True
                },
                "value": "repo",
                "url": project_info.get("repo_url"),
                "action_id": "link1_btn"
            }
        )

    if project_info.get("readme_url"):
        elements.append({
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "Readme",
						"emoji": True
					},
					"value": "readme",
					"url": project_info.get("readme_url"),
					"action_id": "link2_btn"
				})
    if options:
        elements.append({
                        "type": "static_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a devlog",
                            "emoji": True
                        },
                        "options": options,

                        "action_id": "devlog_select-action"
                    })
    message.append({
			"type": "actions",
            "block_id": "devlog_select",
			"elements":elements})
    return message
async def build_devlog(user_id,devlog,project,back_type,target_id=None,page=None):
    devlog_info = await make_user_request(user_id,f"/devlogs/{devlog}")
    image_link = None
    for media in devlog_info.get("media"):
        if media.get("content_type") == "image/png":
            image_link = "https://flavortown.hackclub.com" + media.get("url")
            break
    message = [{
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": f"Devlog. {devlog}"
			}
		}]
    if image_link:
        message.append({
			"type": "image",
			"image_url": image_link,
			"alt_text": "item icon"
		})
    message.append({
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": devlog_info.get("body","TestDesc")
			}
		})
    message.append({
			"type": "divider"
		})
    message.append({
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"Comments: {devlog_info.get("comments_count")}\nLikes:{devlog_info.get("likes_count")}\nTime Spent: {seconds_to_hms(devlog_info.get("duration_seconds"))}\nCreated at: {devlog_info.get(slack_timestamp(devlog_info.get("created_at")))}\nUpdated at: {slack_timestamp(devlog_info.get("updated_at"))}"
			}
		})
    message.append({
        "type": "divider"
    })
    message.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Back",
                        "emoji": True
                    },
                    "value": str(project)+" "+back_type+ ((" " + str(target_id)+" "+str(page)) if target_id else ""),
                    "action_id": "project_back"
                }
            ]
        }
    )

    return message
async def build_projects(user_id,project_ids=None,target_id=None,page=None,back_type="projects"):

    options = []
    user_info = await make_user_request(user_id, f"/users/{target_id or "me"}")
    if not target_id:
        message = [
            {
                "type": "header",
                "text": {'type': 'plain_text', 'text': 'Projects'}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Here are your projects, use the menu below to view more details on any project and click the load button to view the details of your projects(Be mindful of ratelimits)!"
                }
            },
            {
                "type": "divider"
            }
        ]
    else:
        message = [
            {
                "type": "header",
                "text": {'type': 'plain_text', 'text': f'User {user_info["id"]}. {user_info["display_name"]}'}
            },

            {
                "type": "context",
                "elements": [
                    {
                        "type": "image",
                        "image_url": user_info["avatar"],
                        "alt_text": "item icon"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"Here is the user {user_info["display_name"]} and their projects:"
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]


    if project_ids:
        projects = await asyncio.gather(*[
            make_user_request(user_id,f"projects/{project}") for project in project_ids[:10]
        ])
        for project in projects:
            message.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{project.get('id', 0)}. {project.get('title', "TestTitle")}*\n {project.get('description', 'TestDesc')}"
                },
                "accessory": {
                    "type": "image",
                    "image_url": "https://flavortown.hackclub.com" + (
                            project.get('banner_url') or '/assets/default-banner-3d4e1b67.png'),
                    "alt_text": "item icon"
                }
            })
            message.append({
                "type": "divider"
            })

            if not target_id:
                options.append({
                    "text": {
                        "type": "plain_text",
                        "text": f"{project.get('id', 0)}. {project.get('title', "TestTitle")}",
                        "emoji": True
                    },
                    "value": str(project.get('id', 0)) + " " +back_type
                })
            else:
                options.append({
                    "text": {
                        "type": "plain_text",
                        "text": f"{project.get('id', 0)}. {project.get('title', "TestTitle")}",
                        "emoji": True
                    },
                    "value": str(project.get('id', 0)) + " "+ back_type + " "+ str(target_id) + " " +str(page)
                })
    else:
        projects = user_info.get("project_ids")
        for project in projects[:10]:
            message.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Project. {project}"
                }
            })
            message.append({
                "type": "divider"
            })

            if not target_id:
                options.append({
                    "text": {
                        "type": "plain_text",
                        "text": f"Project. {project}",
                        "emoji": True
                    },
                    "value": str(project) + " "+back_type
                })
            else:
                options.append({
                    "text": {
                        "type": "plain_text",
                        "text": f"Project. {project}",
                        "emoji": True
                    },
                    "value": str(project) + " " + back_type + " "+ str(target_id) + " " +str(page)
                })

    message.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"Votes: {user_info.get("vote_count")}\nLikes:{user_info.get("like_count")}\nCoding Time Today: {seconds_to_hms(user_info.get("devlog_seconds_today"))}\nCodding Time Total: {seconds_to_hms(user_info.get("devlog_seconds_total"))}\nCookies: {user_info.get("cookies") if user_info.get("cookies") else 0} :cookie:\nSlack ID: {user_info.get("slack_id")}"
        }
    })
    if options:
        message.append({
            "type": "actions",
            'block_id': "select",
            "elements": [{
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a project",
                    "emoji": True
                },
                "options": options,

                "action_id": "project_select"
            },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Load",
                        "emoji": True
                    },
                    "value": json.dumps([project_ids or projects,[target_id or -1,page or -1,back_type]]),
                    "action_id": "load_projects"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Back",
                        "emoji": True
                    },
                    "value": str(page) or "go_back",
                    "action_id": ("lb_prev"if back_type == "leaderboard" else "users_prev")if target_id else "home_back"
                }
            ],

        })
    else:
        message.append({
            "type": "actions",
            'block_id': "select",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Load",
                        "emoji": True
                    },
                    "value": json.dumps([project_ids or projects, [target_id or -1, page or -1]]),
                    "action_id": "load_projects"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Back",
                        "emoji": True
                    },
                    "value": str(page) or "go_back",
                    "action_id": f"{"lb"}_prev" if target_id else "home_back"
                }
            ],

        })
    return message
async def build_shop(user_id,region="us",page=1,sort_mode="1",reverse=False):
    shop = await make_user_request(user_id,"/store")
    if not shop:
        return None
    message =[
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Shop"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Here is the shop. View our wide range of items and click on any to view more details. Prices default to the US region change using the menu below"
            }
        },
        {
            "type": "divider"
        }
    ]
    if sort_mode == "1":
        items = sorted((x for x in shop if x["enabled"]["enabled_" + region] and x["show_in_carousel"]),
                       key=lambda x: x["ticket_cost"][region], reverse=reverse)
    else:
        items = sorted((x for x in shop if x["enabled"]["enabled_" + region] and x["show_in_carousel"]),
                       key=lambda x: x["name"], reverse=reverse)
    options = []
    for i in range(min(15, len(items)-(page-1)*15)):
        item = items[i + (page-1)*15]
        if item["enabled"]["enabled_"+region]:
            message.append({
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"*{item["name"]}*\n{item["description"]}\nCost: {int(item["ticket_cost"][region])} 🍪"
			},
			"accessory": {
				"type": "image",
				"image_url": item["image_url"],
				"alt_text": "item icon"
			}
		})
            message.append({
			"type": "divider"
		})
            options.append({
                "text": {"type": "plain_text", "text": item["name"], "emoji": True},
                "value": f"{item['id']} {region} {page} {sort_mode} {reverse}"
            })
    message.append({
			"type": "actions",
			"elements": [
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "Back",
						"emoji": True
					},
					"value": "go_back",
					"action_id": "home_back"
				},

                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Prev",
                        "emoji": True
                    },
                    "value": f"{region} {max(page - 1, 1)} {sort_mode} {reverse}",
                    "action_id": "shop_prev"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Next",
                        "emoji": True
                    },
                    "value": f"{region} {min(page+1,5)} {sort_mode} {reverse}",
                    "action_id": "shop_next"
                },

                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Reverse",
                        "emoji": True
                    },
                    "value": f"{region} {page} {sort_mode} {not reverse}",
                    "action_id": "toggle_reverse"
                }
			]
		})
    message.append({"type": "actions", "elements":[{
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select an item to view details",
                        "emoji": True
                    },
                    "options": options,
                    "action_id": "shop_item_select"
                },
				{
					"type": "static_select",
					"placeholder": {
						"type": "plain_text",
						"text": "Select a region",
						"emoji": True
					},

					"options": [
						{
							"text": {
								"type": "plain_text",
								"text": "Australia",
								"emoji": True
							},
							"value": f"au {page} {sort_mode} {reverse}"

						},
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Canada",
                                "emoji": True
                            },
                            "value": f"ca {page} {sort_mode} {reverse}"

                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Europe",
                                "emoji": True
                            },
                            "value": f"eu {page} {sort_mode} {reverse}"

                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "India",
                                "emoji": True
                            },
                            "value": f"in {page} {sort_mode} {reverse}"

                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "United Kingdom",
                                "emoji": True
                            },
                            "value": f"uk {page} {sort_mode} {reverse}"

                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "United States of America",
                                "emoji": True
                            },
                            "value": f"us {page} {sort_mode} {reverse}"

                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Rest of the world",
                                "emoji": True
                            },
                            "value": f"xx {page} {sort_mode} {reverse}"

                        }
					],
					"action_id": "region_select"
				},
                {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a sorting mode",
                        "emoji": True
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Price",
                                "emoji": True
                            },
                            "value": f"{region} {page} 1 {reverse}"

                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Alphabetical",
                                "emoji": True
                            },
                            "value": f"{region} {page} 0 {reverse}"

                        }
                    ],
                    "action_id": "sort_mode_select"
                }]}

                    )
    return message
async def build_item(item,region, page, sort_mode, reverse,user_id):
    item_info = await make_user_request(user_id,"store/"+str(item))
    message = [{
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": item_info["name"]
        }
    }, {
        "type": "image",
        "image_url": item_info["image_url"],
        "alt_text": "item icon"
    }, {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": item_info.get("description", "TestDesc")
        }
    }, {
        "type": "divider"
    } ]
    if item_info["max_qty"]:
        message.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": f"You can only buy {item['max_qty']} at a time"}})
        message.append({
        "type": "divider"
    })
    if item_info["sale_percentage"]:
        message.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": f"This item is {item['sale_percentage']}% off"}})
        message.append({
            "type": "divider"
        })
    if item_info["limited"]:
        message.append({"type": "section", "text": {"type": "mrkdwn", "text": f"Only {item['stock']} left in stock"}})
        message.append({
            "type": "divider"
        })
    if item_info["one_per_person_ever"]:
        message.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "This item can only be bought once per person"}})
        message.append({
            "type": "divider"
        })
    if not item_info["buyable_by_self"]:
        message.append({"type": "section", "text": {"type": "mrkdwn", "text": "This item cannot be bought by itself"}})
        message.append({
            "type": "divider"
        })
    if not item_info["enabled"]["enabled_" + region]:
        message.append({"type": "section",
                        "text": {"type": "mrkdwn", "text": f"This item cannot be bought in this region ({region})"}})
        message.append({
            "type": "divider"
        })
    if item_info["type"] == "ShopItem::HQMailItem":
        message.append({"type": "section", "text": {"type": "mrkdwn",
                                                    "text": "⚠️ This item is shipped from United Kingdom. Customs fees may apply"}})
        message.append({
            "type": "divider"
        })
    message.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Back",
                    "emoji": True
                },
                "value": f"{region} {page} {sort_mode} {reverse}",
                "action_id": "shop_back"
            }
        ]
    })
    return message
async def build_leaderboard(user_id,page=1):
    html = await make_user_request(user_id,f"https://flavortown.hackclub.com/leaderboard?page={page}&limit=25",text=True)
    entries = get_entries(html)
    message = [{
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": "Leaderboard"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "Here is the leaderboard!"
			}
		},
		{
			"type": "divider"
		}]
    options = []
    for i, entry in enumerate(entries):
        message.append({

			"type": "context",
			"elements": [
				{
					"type": "image",
					"image_url": entry["icon"],
					"alt_text": "item icon"
				},
				{
					"type": "mrkdwn",
					"text": f"{(page - 1) * 25 + i + 1}. {entry["name"]} - {entry["cookies"]} 🍪"
				}
			]
		})
        options.append({
            "text": {
                "type": "plain_text",
                "text": f"{(page - 1) * 25 + i + 1}. {entry["name"]}",
                "emoji": True
            },
            "value": str(entry["id"]) + " " + str(page)+" leaderboard"
        })
    message.append({
			"type": "divider"
		})
    message.append({
			"type": "actions",
			"elements": [
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "Back",
						"emoji": True
					},
					"value": "go_back",
					"action_id": "home_back"
				},
				{
					"type": "static_select",
					"placeholder": {
						"type": "plain_text",
						"text": "Select a user",
						"emoji": True
					},
					"options": options,
					"action_id": "user_select"
				},{
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Prev",
                        "emoji": True
                    },
                    "value": f"{max(page-1,1)}",
                    "action_id": "lb_prev"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Next",
                        "emoji": True
                    },
                    "value": f"{page+1}",
                    "action_id": "lb_next"
                }
			]
		})
    return message
async def build_users(user_id,page=1,query=None):
    query_page = (page-1)//5+1
    if query:
        path = f"users?page={query_page}&query={query}"
    else:
        path = f"users?page={query_page}"
    users_info = await make_user_request(user_id,path)

    message = [{
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "Users"
        }
    },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Here are some users we picked for you!"
            }
        },
        {
            "type": "divider"
        }]
    options = []
    for i, entry in enumerate(users_info['users'][(page-1)*20:page*20]):
        message.append({

            "type": "context",
            "elements": [
                {
                    "type": "image",
                    "image_url": entry["avatar"],
                    "alt_text": "item icon"
                },
                {
                    "type": "mrkdwn",
                    "text": f"{entry["id"]}. {entry["display_name"]} - {entry["cookies"] if entry["cookies"] else 0} 🍪"
                }
            ]
        })
        options.append({
            "text": {
                "type": "plain_text",
                "text": f"{entry["id"]}. {entry["display_name"]}",
                "emoji": True
            },
            "value": str(entry["id"]) + " " + str(page) + " users"
        })
    message.append({
        "type": "divider"
    })
    if query:
        message.append({
            "dispatch_action": True,
            "type": "input",
            "element": {
                "type": "plain_text_input",
                "action_id": "search_users",
                "initial_value": query
            },
            "label": {
                "type": "plain_text",
                "text": "Search",
                "emoji": True
            },
            'block_id': "search",
            "optional": False
        })
    else:
        message.append({
            "dispatch_action": True,
            "type": "input",
            "element": {
                "type": "plain_text_input",
                "action_id": "search_users"
            },
            "label": {
                "type": "plain_text",
                "text": "Search",
                "emoji": True
            },
            'block_id': str(page),
            "optional": False
        })
    message.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Back",
                    "emoji": True
                },
                "value": "go_back",
                "action_id": "home_back"
            },
            {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a user",
                    "emoji": True
                },
                "options": options,
                "action_id": "user_select"
            }, {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Prev",
                    "emoji": True
                },
                "value": f"{max(page - 1, 1)}",
                "action_id": "users_prev"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Next",
                    "emoji": True
                },
                "value": f"{min(page + 1,int(users_info["pagination"]["total_pages"]))}",
                "action_id": "users_next"
            }
        ]
    })
    return message