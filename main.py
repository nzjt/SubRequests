import json
import pendulum
import discord
from discord import AllowedMentions
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from UsersManager import UsersManager
from RequestsManager import RequestsManager

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

users_manager = UsersManager()
requests_manager = RequestsManager()
geolocator = Nominatim(user_agent="sub-requests-bot", timeout=10)
tf = TimezoneFinder()

requests_group = discord.app_commands.Group(name="requests", description="Sub requests")
tree.add_command(requests_group)
timezone_group = discord.app_commands.Group(name="timezone", description="Timezone")
tree.add_command(timezone_group)
admin_group = discord.app_commands.Group(name="admin", description="Admin")
tree.add_command(admin_group)

@admin_group.command(name="add")
@discord.app_commands.describe(user="user")
async def admin_add(interaction: discord.Interaction, user: discord.User):
    if await users_manager.query_admin(str(interaction.user.id)):
        await users_manager.update_admin(str(user.id), True)
        content = "Added <@{}> as an admin.".format(user.id)
    else:
        content = "You do not have permission to do that."

    await interaction.response.send_message(
        content,
        allowed_mentions=discord.AllowedMentions.none(),
        ephemeral=interaction.guild is not None
    )

@admin_group.command(name="remove")
@discord.app_commands.describe(user="user")
async def admin_remove(interaction: discord.Interaction, user: discord.User):
    if await users_manager.query_admin(str(interaction.user.id)):
        await users_manager.update_admin(str(user.id), False)
        content = "Removed <@{}> as an admin.".format(user.id)
    else:
        content = "You do not have permission to do that."

    await interaction.response.send_message(
        content,
        allowed_mentions=discord.AllowedMentions.none(),
        ephemeral=interaction.guild is not None
    )

@admin_group.command(name="list")
async def admin_list(interaction: discord.Interaction):
    admins = await users_manager.query_all_admins()
    content = []
    for i, row in enumerate(admins):
        content.append("{}. <@{}>".format(
            i + 1,
            row[0]
        ))
    if content:
        content = "\n".join(content)
    else:
        content = "There are no admins."

    await interaction.response.send_message(
        content,
        allowed_mentions=discord.AllowedMentions.none(),
        ephemeral=interaction.guild is not None
    )

@requests_group.command(name="add")
@discord.app_commands.describe(month="Month")
@discord.app_commands.describe(day="Day")
@discord.app_commands.describe(time="24h time (H:MM)")
@discord.app_commands.describe(class_="Class")
async def requests_add(interaction: discord.Interaction, month: int, day: int, time: str, class_: str):
    await requests_add_impl(interaction, str(interaction.user.id), month, day, time, class_)

@requests_group.command(name="addfor")
@discord.app_commands.describe(user="User")
@discord.app_commands.describe(month="Month")
@discord.app_commands.describe(day="Day")
@discord.app_commands.describe(time="24h time (H:MM)")
@discord.app_commands.describe(class_="Class")
async def requests_addfor(interaction: discord.Interaction, user: discord.User, month: int, day: int, time: str, class_: str):
    if await users_manager.query_admin(str(interaction.user.id)):
        await requests_add_impl(interaction, str(user.id), month, day, time, class_)
    else:
        await interaction.response.send_message(
            "You do not have permission to do that.",
            ephemeral=interaction.guild is not None
        )

async def requests_add_impl(interaction: discord.Interaction, user: str, month: int, day: int, time: str, class_: str):
    timezone = await users_manager.query_timezone(str(interaction.user.id))
    use_default = timezone is None
    if use_default:
        timezone = "America/New_York"
    today = pendulum.now(timezone)

    year = today.year
    if month == 2 and day == 29:
        while not pendulum.date(year, 1, 1).is_leap_year():
            year += 1

    try:
        time = pendulum.parse(time)
        target = pendulum.datetime(year, month, day, time.hour, time.minute, tz=timezone)
    except Exception:
        await interaction.response.send_message(
            "Error during parsing. Check your format is correct.",
            ephemeral=interaction.guild is not None
        )
        return

    if target < today:
        year += 1
        if month == 2 and day == 29:
            while not pendulum.date(year, 1, 1).is_leap_year():
                year += 1
        target = target.set(year=year)

    content = "Confirm that you are requesting a sub for **{}** on <t:{}:F>.".format(
        class_,
        target.int_timestamp
    )
    if use_default:
        content = "Warning :warning: You did not set a timezone, so **EST** (UTC-05:00) is assumed.\n" + content

    class YesNoView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)

        @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
        async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.edit_message(
                content="Requested a sub for **{}** on <t:{}:F>.".format(
                    class_,
                    target.int_timestamp
                ),
                view=None
            )

            await requests_manager.add_request(user, class_, target.int_timestamp)

        @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
        async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.edit_message(content="{}\nCancelled.".format(content), view=None)

    await interaction.response.send_message(
        content,
        ephemeral=interaction.guild is not None,
        view=YesNoView()
    )

@requests_group.command(name="view")
async def requests_view(interaction: discord.Interaction):
    user_id: str = str(interaction.user.id)

    content = []
    for request_id, class_, time in await requests_manager.query_by_user(user_id):
        content.append("#{}: **{}** on <t:{}:F>".format(
            request_id,
            class_,
            time
        ))
    if content:
        content = "\n".join(content)
    else:
        content = "You have no sub requests."

    await interaction.response.send_message(
        content,
        ephemeral=interaction.guild is not None
    )

@requests_group.command(name="viewall")
async def requests_viewall(interaction: discord.Interaction):
    content = []
    for request_id, user, class_, time in await requests_manager.query_all():
        content.append("#{}: **{}** on <t:{}:F> (sub for <@{}>)".format(
            request_id,
            class_,
            time,
            user
        ))
    if content:
        content = "\n".join(content)
    else:
        content = "There are no sub requests."

    await interaction.response.send_message(
        content,
        allowed_mentions=AllowedMentions.none(),
        ephemeral=interaction.guild is not None
    )

@requests_group.command(name="remove")
@discord.app_commands.describe(request_id="id")
async def requests_remove(interaction: discord.Interaction, request_id: int):
    user_id: str = str(interaction.user.id)

    request_id = str(request_id)
    request_data = await requests_manager.query_by_id(request_id)
    if request_data:
        my_request = request_data[0] == user_id
        if my_request or await users_manager.query_admin(user_id):
            user_id, class_, time = request_data
            if my_request:
                content = "Are you sure you want to cancel your sub request for **{}** on <t:{}:F>?".format(
                    class_,
                    time
                )
            else:
                content = "Are you sure you want to cancel <@{}>'s sub request for **{}** on <t:{}:F>?".format(
                    user_id,
                    class_,
                    time
                )

            class YesNoView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)

                @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
                async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.edit_message(
                        content="Sub request for **{}** on <t:{}:F> has been cancelled.".format(
                            class_,
                            time
                        ),
                        view=None
                    )

                    await requests_manager.remove(request_id)

                @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
                async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.edit_message(view=None)

            await interaction.response.send_message(
                content,
                view=YesNoView(),
                ephemeral=interaction.guild is not None
            )
        else:
            await interaction.response.send_message(
                "Request #{} is not yours!".format(request_id),
                ephemeral=interaction.guild is not None
            )
    else:
        await interaction.response.send_message(
            "Invalid id.",
            ephemeral=interaction.guild is not None
        )

@timezone_group.command(name="get")
async def timezone_get(interaction: discord.Interaction):
    user_id: str = str(interaction.user.id)

    timezone = await users_manager.query_timezone(user_id)
    if timezone:
        local_time = pendulum.now(timezone)

        await interaction.response.send_message(
            "Your timezone is **{} (UTC{})**.".format(timezone, local_time.format("Z")),
            ephemeral=interaction.guild is not None
        )
    else:
        await interaction.response.send_message(
            "You have not set a timezone yet.",
            ephemeral=interaction.guild is not None
        )

@timezone_group.command(name="set")
@discord.app_commands.describe(city="City")
async def timezone_set(interaction: discord.Interaction, city: str):
    await interaction.response.defer()

    user_id: str = str(interaction.user.id)

    try:
        location = geolocator.geocode(city)

        if location:
            timezone = tf.timezone_at(lng=location.longitude, lat=location.latitude)

            local_time = pendulum.now(timezone)

            class YesNoView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)

                @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
                async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.edit_message(
                        embed=discord.Embed(
                            title="Set timezone to {} (UTC{})!".format(timezone, local_time.format("Z")),
                            colour=discord.Color.green()
                        ),
                        view=None
                    )

                    await users_manager.update_timezone(user_id, timezone)

                @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
                async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.edit_message(
                        embed=discord.Embed(
                            title="Set timezone to {} (UTC{})?".format(timezone, local_time.format("Z")),
                            description="Cancelled.",
                            colour=discord.Color.red()
                        ),
                        view=None
                    )

            await interaction.followup.send(
                embed=discord.Embed(
                    title="Set timezone to {} (UTC{})?".format(timezone, local_time.format("Z")),
                    description="Confirm whether your local time is **{}**.".format(local_time.format("h:mm A")),
                    colour=discord.Color.yellow()
                ),
                view=YesNoView(),
                ephemeral=interaction.guild is not None
            )
        else:
            await interaction.followup.send(
                "Couldn't find **{}**!".format(city),
                ephemeral=interaction.guild is not None
            )
    except Exception as e:
        await interaction.followup.send(
            embed=discord.Embed(
                title="Exception",
                description="```{}```".format(e),
                colour=discord.Color.red()
            ),
            ephemeral=interaction.guild is not None
        )

@tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

@client.event
async def on_ready():
    await users_manager.init("users.db")
    await requests_manager.init("requests.db")
    await tree.sync()


with open("TOKEN.txt", "r") as token:
    client.run(token.read())
