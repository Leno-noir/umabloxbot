from __future__ import annotations
from .sections.blacklist import BlacklistSection
from .sections.promotion import PromotionSection
from .sections.feedback import FeedbackSection
from .sections.networking import NetworkingSection
import discord

from db.guild_configs import guild_get_settings

#register all sections here — order controls display order in the settings panel
SECTIONS = [BlacklistSection, PromotionSection, FeedbackSection, NetworkingSection]


class SettingsView(discord.ui.View):
    """Builds the settings panel dynamically from registered sections.
    
    Adding a new module = add its Section class to SECTIONS above.
    This design allows easy extension without modifying the view logic.
    """

    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self._message: discord.Message | None = None

    def _add_section_buttons(self, settings: dict):
        """Attach buttons from every section to this view.
        
        Clears existing buttons and adds new ones from each section.
        This is called whenever settings are updated to refresh the UI.
        """
        #remove all existing buttons
        self.clear_items()
        
        #loop through each section and add its buttons
        for section in SECTIONS:
            for btn in section.get_buttons(self.guild_id, self):
                self.add_item(btn)

    @staticmethod
    async def build_embed(guild: discord.Guild) -> discord.Embed:
        """Build the settings embed showing all current configuration values.
        
        Fetches settings from database and displays them organized by section.
        Each section contributes its own fields to the embed.
        """
        #fetch current settings from database
        settings = await guild_get_settings(guild.id) or {}

        #create the main settings embed
        embed = discord.Embed(
            title       = f"⚙️ Settings — {guild.name}",
            description = "Configure the bot for this server. Changes apply immediately.",
            color       = 0x5865F2,
        )

        #loop through each section and add its configuration fields
        for section in SECTIONS:
            #get all fields (label: value pairs) from this section
            fields = await section.get_fields(settings)
            
            #build section value: "Label: value\nLabel: value" format
            lines = "\n".join(f"**{label}:** {value}" for label, value in fields)
            
            #add this section to the embed
            embed.add_field(
                name   = f"{section.emoji} {section.label}",
                value  = lines or "No settings configured.",
                inline = False,
            )

        #add footer explaining who can change settings
        embed.set_footer(text="Only administrators can change these settings.")
        return embed

    async def send(self, interaction: discord.Interaction):
        """Send the initial settings panel to the user.
        
        Creates embed, attaches buttons, and sends as ephemeral message.
        Stores message reference for later updates.
        """
        #fetch current settings for this guild
        settings = await guild_get_settings(interaction.guild_id) or {}
        
        #attach buttons from all sections to the view
        self._add_section_buttons(settings)
        
        #build the settings embed
        embed = await self.build_embed(interaction.guild)
        
        #send the panel as an ephemeral (private) message
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
        
        #store the message object for later updates
        self._message = await interaction.original_response()

    async def refresh(self, interaction: discord.Interaction | None = None):
        """Rebuild the settings embed after a value changes.
        
        Called whenever a setting is modified to update the panel.
        Re-fetches database, rebuilds buttons, and edits the message.
        """
        #if no message stored, nothing to refresh
        if self._message is None:
            return

        try:
            #get guild from interaction or stored message
            guild = interaction.guild if interaction is not None else self._message.guild
            if guild is None:
                return

            #fetch updated settings from database
            settings = await guild_get_settings(guild.id) or {}
            
            #rebuild buttons with updated settings
            self._add_section_buttons(settings)
            
            #build the updated embed
            embed = await self.build_embed(guild)
            
            #edit the stored message with new embed and buttons
            await self._message.edit(embed=embed, view=self)
        except Exception:
            #silently fail if message was deleted or other issues
            pass
