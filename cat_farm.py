import json
import random
import asyncio
import aiohttp
from discord.ext import commands

BASE_HEAT = 25.0

async def generate_human_name():
    api_url = "https://randomuser.me/api/?inc=name"
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            if response.status == 200:
                data = await response.json()
                first_name = data["results"][0]["name"]["first"]
                last_name = data["results"][0]["name"]["last"]
                cat_name = f"{first_name} {last_name}"
                return cat_name
            else:
                return "idk the internet died"

name_seed = "cat"
async def generate_cat_name():
    global name_seed
    api_url = f"https://api.datamuse.com/words?rel_trg={name_seed}"

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            if response.status == 200:
                words = await response.json()
                words = [word["word"].lower() for word in words]
                name_seed = random.choice(words)

                random_name = ""
                for word in random.sample(words, random.randint(3, 5)):
                    lbound = random.randint(0, len(word)-3)
                    hbound = lbound + random.randint(1, len(word) - lbound)
                    random_name += word[lbound:hbound]

                return random_name
            else:
                return "calico"

class CatFarm:
    save_file: str = ""
    data = {}
    died = []

    def __init__(self, save_file):
        self.save_file = save_file
        with open(save_file, "r") as f:
            self.data = json.load(f)

    def save_data(self):
        with open(self.save_file, "w") as f:
            f.write(json.dumps(self.data, indent=4))
        print("farm: data saved")

    async def _generate_cat(self, user: str):
        new_name = await generate_cat_name()
        self.data.setdefault(user, {})
        self.data[user][new_name] = {
            "props": {
                "color": random.choice([
                    "orange",
                    "white",
                    "black",
                    "pink",
                    "red",
                    "green",
                    "purple",
                ]),
                "short_legs": random.choice([True, False]),
                "fluffy": random.choice([True, False]),
                "thirsty_bearing": random.randint(1, 99),
                "hunger_bearing": random.randint(1, 99),
                "heat_bearing": random.randint(1, 99),
                "speed": random.randint(1, 100),
            },
            "health": {
                "total": 100,
                "hunger": 0,
                "thirsty": 0,
                "hot": 0,
            }
        }
        return {
            "name": new_name,
            "props": self.data[user][new_name],
        }

    async def inform_death(self, ctx: commands.Context, bot: commands.Bot):
        for info in self.died:
            user = await bot.fetch_user(int(info["user_id"]))

            self.data[info["user_id"]].pop(info["name"])
            if user:
                await ctx.send(f"{info["name"]} of {user.name} has died")
            else:
                await ctx.send(f"{info["name"]} has died")
        self.died = []

    async def regenerate_health(self, global_heat: float):
        for user in self.data.keys():
            for name in self.data[user].keys():
                total_health = self.data[user][name]["health"]["total"]
                hunger = self.data[user][name]["health"]["hunger"]
                thirsty = self.data[user][name]["health"]["thirsty"]
                hot = self.data[user][name]["health"]["hot"]

                if hunger > 75:
                    total_health -= 22 * hunger / 100
                if hunger < 25:
                    total_health += 12 * hunger / 100

                if thirsty > 90:
                    total_health -= 35 * thirsty / 100
                if thirsty < 20:
                    total_health += 3 * thirsty / 100

                total_health = max(min(total_health, 100), 0)
                self.data[user][name]["health"]["total"] = total_health

                if total_health == 0:
                    self.died.append({
                        "user_id": user,
                        "name": name,
                    })

    async def update_health(self, global_heat: float):
        for user in self.data.keys():
            for name in self.data[user].keys():
                hunger = self.data[user][name]["health"]["hunger"]
                thirsty = self.data[user][name]["health"]["thirsty"]
                hot = self.data[user][name]["health"]["hot"]

                hunger_bearing = self.data[user][name]["props"]["hunger_bearing"]
                thirsty_bearing = self.data[user][name]["props"]["thirsty_bearing"]
                heat_bearing = self.data[user][name]["props"]["heat_bearing"]

                heat_impact = (global_heat - BASE_HEAT) * (100 - heat_bearing) / 100

                hunger += 17 * (100 - hunger_bearing) / 100 - 27 * heat_impact
                thirsty += 35 * (100 - thirsty_bearing) / 100 + 35 * heat_impact
                hot = heat_impact

                hunger = max(min(hunger, 100), 0)
                thirsty = max(min(thirsty, 100), 0)

                self.data[user][name]["health"]["hunger"] = hunger
                self.data[user][name]["health"]["thirsty"] = thirsty
                self.data[user][name]["health"]["hot"] = hot

    async def lure(self, ctx: commands.Context):
        message = await ctx.send("luring cats ...")
        sec = random.randint(5, 10)
        print("farm: waiting for", sec, "secs")
        await asyncio.sleep(sec)
        cat = await self._generate_cat(str(ctx.author.id))
        await message.edit(content=f"captured a wild {cat["name"]}!")

    async def feed(self, ctx: commands.Context, user: str, name: str = ""):
        if name == "" or name not in self.data[user].keys():
            name = random.choice(list(self.data[user].keys()))

        self.data[user][name]["health"]["hunger"] -= random.randint(25, 75)
        self.data[user][name]["health"]["hunger"] = max(self.data[user][name]["health"]["hunger"], 0)

        self.data[user][name]["health"]["thirsty"] -= random.randint(35, 90)
        self.data[user][name]["health"]["thirsty"] = max(self.data[user][name]["health"]["thirsty"], 0)

        await ctx.send(f"{name} is feeded")

    async def stat(self, ctx: commands.Context, user: str, name: str):
        await ctx.send(f"```# {name}'s stat:\n{json.dumps(self.data[user][name], indent=4)}'```")

    async def check(self, ctx: commands.Context, user: str):
        for name in self.data[user].keys():
            msg = ""
            total_health = self.data[user][name]["health"]["total"]
            hunger = self.data[user][name]["health"]["hunger"]
            thirsty = self.data[user][name]["health"]["thirsty"]
            hot = self.data[user][name]["health"]["hot"]

            if total_health < 25:
                msg += f"{name}'s health is critical\n"
            elif total_health < 50:
                msg += f"{name}'s health is bad\n"

            if hunger > 75:
                msg += f"{name} is starving\n"
            elif hunger > 50:
                msg += f"{name} is hungry\n"

            if thirsty > 75:
                msg += f"{name} is dehydrated\n"
            elif thirsty > 50:
                msg += f"{name} is thirsty\n"

            if hot < -5:
                msg += f"{name} is cold\n"
            elif hot > 5:
                msg += f"{name} is hot\n"

            if msg == "":
                msg = f"{name} is normal"

            await ctx.send(msg)


