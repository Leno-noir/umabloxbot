import discord
from discord.ext import commands

from core import Colors, timestamp_to_discord
from core.ui import (
    PaginatedLayoutView,
    UmaLayoutView,
    roblox_profile_button,
)
from core.utils import get_user_by_discord_id
from db import bl_list_active
from db.blacklist import bl_global_log
from .utils import (
    blacklist_status_text,
    format_event_log_record,
    format_history_entry,
    get_active_blacklist_entry,
    get_past_blacklist_entries,
)

def build_blacklist_added_embed(
    discord_user_label: str,
    roblox_user: str,
    roblox_id: str,
    reason: str,
    added_by: str,
    timestamp,
    evidence: str | None = None,
) -> UmaLayoutView:
  
  
    lines = [
        ("Discord user", discord_user_label),
        ("Roblox", f"{roblox_user} (`{roblox_id}`)"),
        ("Reason", reason),
    ]
   
    if evidence:
        lines.append(("Evidence", evidence))
   
    lines.extend(
        [
            ("Added by", added_by),
            ("Time added", discord.utils.format_dt(timestamp, style="f")),
        ]
    )
   
    return BlacklistLogView("User added to blacklist", discord.Colour.red(), lines)





def build_blacklist_removed_embed(
    discord_user_label: str,
    reason: str,
    removed_by: str,
) -> UmaLayoutView:
  
    lines = [
        ("Discord user", discord_user_label),
        ("Reason for removal", reason),
        ("Removed by", removed_by),
        ("Time removed", discord.utils.format_dt(discord.utils.utcnow(), style="f")),
    ]
   
    return BlacklistLogView("User removed from blacklist", discord.Colour.green(), lines)




def build_blacklist_join_alert_embed(
    member: discord.Member,
    record: dict,
) -> UmaLayoutView:
    return BlacklistLogView(
        "Blacklisted user joined a server",
        discord.Colour(Colors.YELLOW),
        [
            ("Discord user", f"{member.mention} (`{member.id}`) is on the blacklist."),
            ("Roblox", f"{record.get('roblox_user', '?')} (`{record['roblox_id']}`)"),
            ("Reason", record["current_reason"]),
            ("Server", member.guild.name),
            ("Time", discord.utils.format_dt(discord.utils.utcnow(), style="f")),
        ],
    )





class BlacklistLogView(UmaLayoutView):
    """Standardized blacklist log card using Discord components v2."""

    def __init__(
        self,
        title: str,
        accent_colour: discord.Colour,
        lines: list[tuple[str, str]],
    ):
        super().__init__(timeout=None)
       
       
        components: list[discord.ui.Item] = [self.text(f"## {title}")]

        for index, (label, value) in enumerate(lines):
            components.append(self.text(f"**{label}**"))
            components.append(self.text(value))
            if index < len(lines) - 1:
                components.append(self.separator())

        self.set_container(*components, accent=accent_colour)




















def build_blacklist_info_embed(
    discord_id: str,
    discord_user_label: str,
    doc: dict,
) -> tuple[UmaLayoutView, str | None]:
   
    active = get_active_blacklist_entry(doc)
    view = UmaLayoutView()
    items: list[discord.ui.Item] = [
        view.text(f"## Blacklist info - {discord_user_label}"),
        view.text("CURRENTLY BANNED" if active else "No active ban"),
    ]

    if active:
        added_ts = timestamp_to_discord(active["added_at"])
        items.extend(
            [
                view.separator(),
                view.text("**Discord ID**"),
                view.text(discord_id),
                view.separator(),
                view.text("**Roblox**"),
                view.text(f"{active['roblox_user']} (`{active['roblox_id']}`)"),
                view.separator(),
                view.text("**Reason**"),
                view.text(active["reason"]),
            ]
        )

        if active.get("evidence"):
            items.extend(
                [
                    view.separator(),
                    view.text("**Evidence**"),
                    view.text(active["evidence"]),
                ]
            )

        items.extend(
            [
                view.separator(),
                view.text("**Added by**"),
                view.text(active["added_by"]),
                view.text(f"<t:{added_ts}:F>"),
            ]
        )

   
    past = get_past_blacklist_entries(doc)
    if past:   
        lines = [
            f"- <t:{timestamp_to_discord(record['added_at'])}:d> - {record['reason']} (removed by {record.get('removed_by', '?')})"
            for record in past[:5]
        ]
        items.extend(
            [
                view.separator(),
                view.text(f"**Past entries ({len(past)})**"),
                view.text("\n".join(lines)),
            ]
        )

    roblox_id = active["roblox_id"] if active else doc.get("roblox_id")
    accent = discord.Colour(Colors.RED if active else Colors.GRAY)
    components: list[discord.ui.Item] = [view.container(*items, accent=accent)]
   
    if roblox_id:
        components.append(roblox_profile_button(roblox_id))

    view.set_items(*components)
    return view, roblox_id






def build_blacklist_history_embed(
    discord_id: str,
    discord_user_label: str,
    doc: dict,
) -> UmaLayoutView:
    
    history = doc.get("history", [])
    view = UmaLayoutView()
    items: list[discord.ui.Item] = [
        view.text(f"## Blacklist history - {discord_user_label}"),
        view.text(f"{len(history)} event(s) on record"),
    ]

    for record in history:
        added_ts = timestamp_to_discord(record["added_at"])
       
        lines = [
            f"**Discord ID:** {discord_id}",
            f"**Reason:** {record['reason']}",
            f"**Roblox:** {record.get('roblox_user', '?')} (`{record['roblox_id']}`)",
            f"**Added by:** {record['added_by']}",
        ]
      
        if record.get("evidence"):
            lines.insert(3, f"**Evidence:** {record['evidence']}")

        if record.get("removed_at"):
            removed_ts = timestamp_to_discord(record["removed_at"])
           
            lines += [
                f"**Removed by:** {record.get('removed_by', '?')} on <t:{removed_ts}:d>",
                f"**Removal reason:** {record.get('remove_reason', '?')}",
            ]
            items.append(view.separator())
            items.append(view.text(f"**Unbanned - added <t:{added_ts}:d>**"))
            items.append(view.text("\n".join(lines)))
      
        else:
            items.append(view.separator())
            items.append(view.text(f"**Banned - <t:{added_ts}:d>**"))
            items.append(view.text("\n".join(lines)))

    view.set_container(*items, accent=discord.Colour(Colors.BLUE))
    return view






def build_blacklist_list_embed(
    page: int,
    records: list[dict],
    total: int,
) -> UmaLayoutView:
   
    total_pages = max(1, (total + 9) // 10)
    view = UmaLayoutView()
    items: list[discord.ui.Item] = [
        view.text(f"## Blacklist - Page {page}"),
        view.text(f"**{total}** banned user(s) in total"),
    ]
    
    for record in records:
        added_ts = timestamp_to_discord(record["current_added_at"])
        items.extend(
            [
                view.separator(),
                view.text(f"**{record.get('roblox_user', '?')} | <@{record['discord_id']}>**"),
                view.text(
                    f"Reason: {record['current_reason']}\n"
                    f"Added: <t:{added_ts}:d> by {record['current_added_by']}"
                ),
            ]
        )
   
    items.append(view.text(f"Page {page}/{total_pages}"))
    view.set_container(*items, accent=discord.Colour(Colors.RED))
    return view






def build_blacklist_log_embed(
    page: int,
    records: list[dict],
    total: int,
) -> UmaLayoutView:
    
    total_pages = max(1, (total + 4) // 5)
    view = UmaLayoutView()
    
    items: list[discord.ui.Item] = [
        view.text("## Blacklist Event Log"),
        view.text(f"**{total}** event(s) in total"),
        view.separator(),
    ]

    for record in records:
        items.append(view.text(format_event_log_record(record)))
        items.append(view.separator())

    items.append(view.text(f"Page {page}/{total_pages}"))
   
    view.set_container(*items, accent=discord.Colour.blue())
    
    return view







class ConfirmRemoveView(discord.ui.View):
    """Confirmation buttons shown before removing a user."""

    def __init__(self, user_discord_id: str, user_discord_label: str, bot):
        super().__init__(timeout=30)
        self.user_discord_id = user_discord_id
        self.user_discord_label = user_discord_label
        self.bot = bot
        self.confirmed = False

   
    @discord.ui.button(label="Yes, remove", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
       
        from .modals import BlacklistRemoveModal

        self.confirmed = True
      
        await interaction.response.send_modal(
            BlacklistRemoveModal(
                self.user_discord_id, self.user_discord_label, self.bot
            )
        )
       
        self.stop()

    
    
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
       
        await interaction.delete_original_response()
      
        self.stop()



    async def on_timeout(self):
        for item in self.children:
            item.disabled = True







class BlacklistBanPromptView(discord.ui.View):
    """Button that shows the ban command for a blacklisted user who joined."""

    def __init__(self, discord_id: int, reason: str):
        super().__init__(timeout=600)
        self.discord_id = discord_id
        self.reason = reason

   
    @discord.ui.button(label="Copy Ban Command", style=discord.ButtonStyle.primary)
    async def copy_ban_command(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
       
        command = f"/ban user:{self.discord_id} reason:{self.reason}"
       
        await interaction.response.send_message(
            f"Command copied to clipboard:\n```{command}```",
            ephemeral=True,
        )







class BlacklistPanelView(PaginatedLayoutView):
    """Paginated blacklist panel using Discord components v2."""

    def __init__(self, bot: commands.Bot, page: int = 1):
        super().__init__(page=page, timeout=None)
        self.bot = bot

   
    async def _rebuild_layout(self):
        blacklisted_users, total = await bl_list_active(
            skip=self.page_offset(), limit=self.items_per_page
        )
       
        total_pages = self.clamp_page(total)
       
        blacklisted_users, total = await bl_list_active(
            skip=self.page_offset(), limit=self.items_per_page
        )

        items: list[discord.ui.Item] = [
            self.media("https://i.imgur.com/mmiyHe9.png"),
            self.text(
                f"**{total} banned user(s) in total**"
                if total
                else "The blacklist is currently empty."
            ),
        ]

        if blacklisted_users:
            items.append(self.separator())

        for index, user in enumerate(blacklisted_users):
            added_timestamp = timestamp_to_discord(user["current_added_at"])
           
            discord_user_label = await get_user_by_discord_id(
                self.bot, user["discord_id"]
            )
          
            items.extend(
                [
                    self.text(f"{discord_user_label} | {user.get('roblox_user', '?')}"),
                    self.text(f"Reason: {user['current_reason']}"),
                    self.text(f"Added: <t:{added_timestamp}:d>"),
                ]
            )
          
            if index < len(blacklisted_users) - 1:
                items.append(self.separator())

        items.append(self.text(f"Page {self.page}/{total_pages}"))

        self.set_items(
            self.container(*items, accent=discord.Colour(15158332)),
            self.pagination_row(total_pages, "blacklist_list"),
        )







class BlacklistEventLogView(PaginatedLayoutView):
    """Paginated blacklist event log panel using Discord components v2."""

    def __init__(self, page: int = 1):
        super().__init__(page=page, timeout=None)



    async def _rebuild_layout(self):
        page_events, total = await bl_global_log(
            skip=self.page_offset(),
            limit=self.items_per_page,
        )
       
        total_pages = self.clamp_page(total)

        items: list[discord.ui.Item] = [
            self.text("## Blacklist Event Log"),
            self.text(f"**{total}** event(s) in total"),
            self.separator(),
        ]

        for record in page_events:
            items.append(self.text(format_event_log_record(record)))
            items.append(self.separator())

        items.append(self.text(f"Page {self.page}/{total_pages}"))

        self.set_items(
            self.container(*items, accent=discord.Colour(15158332)),
            self.pagination_row(total_pages, "blacklist_event_log"),
        )






class BlacklistInfoView(UmaLayoutView):
    def __init__(
        self,
        discord_user: str,
        discord_id: int,
        roblox_user: str,
        roblox_id: int,
        doc: dict,
    ):
        super().__init__(timeout=None)

        items: list[discord.ui.Item] = [
            self.text("## **Blacklist Info**"),
            self.text(f"\n{discord_user}"),
            self.text(f"\n{blacklist_status_text(bool(doc.get('active')))}"),
            self.separator(),
            self.text(f"**Discord Info**\nUsername: {discord_user}\nID: {discord_id}"),
            self.separator(),
            self.text(f"\n**Roblox Info**\nUsername: {roblox_user}\nID: {roblox_id}"),
            self.separator(),
        ]

        past_entries = get_past_blacklist_entries(doc)
       
        if past_entries:
            history_lines = "\n".join(
                f"- <t:{timestamp_to_discord(entry['added_at'])}:d> - {entry['reason']}"
                for entry in past_entries
            )
            items.append(self.text(f"**Past Entries ({len(past_entries)})**\n{history_lines}"))

        components: list[discord.ui.Item] = [
            self.container(*items, accent=discord.Colour(15548997))
        ]

        if roblox_id:
            components.append(roblox_profile_button(roblox_id))

        self.set_items(*components)







class BlacklistHistoryView(PaginatedLayoutView):
    """Paginated blacklist history panel for a single user."""

    def __init__(
        self,
        discord_user: str,
        discord_id: int,
        roblox_user: str,
        roblox_id: int,
        doc: dict,
        page: int = 1,
    ):
        super().__init__(page=page, timeout=None)
        self.discord_user = discord_user
        self.discord_id = discord_id
        self.roblox_user = roblox_user
        self.roblox_id = roblox_id
        self.doc = doc

  
  
    async def _rebuild_layout(self):
        history = self.doc.get("history", [])
        total = len(history)
       
        total_pages = self.clamp_page(total)
        page_start = self.page_offset()
        page_entries = self.page_items(history)

        items: list[discord.ui.Item] = [
            self.text(
                f"## **Blacklist History for {self.roblox_user} (`{self.roblox_id}`)**"
            ),
            self.text(f"**{total}** event(s) on record"),
            self.separator(),
            self.text(f"Discord: {self.discord_user}"),
            self.separator(),
        ]

        for index, entry in enumerate(page_entries, start=page_start + 1):
            items.append(self.text(format_history_entry(entry, index)))
            items.append(self.separator())

        items.append(self.text(f"Page {self.page}/{total_pages}"))

        components: list[discord.ui.Item] = [
            self.container(*items, accent=discord.Colour.red())
        ]
      
        if self.roblox_id:
            components.append(roblox_profile_button(self.roblox_id))
       
        components.append(self.pagination_row(total_pages, "blacklist_history"))
        self.set_items(*components)
