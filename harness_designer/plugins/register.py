# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

PLUGIN_TYPE_MISC = 0x00
PLUGIN_TYPE_DATABASE = 0x01
PLUGIN_TYPE_SCRAPER = 0x02
PLUGIN_TYPE_3D = 0x04
PLUGIN_TYPE_SCHEMATIC = 0x08
PLUGIN_TYPE_PEGBOARD = 0x10
PLUGIN_TYPE_AI = 0x20


class RegisterPlugin:

    def __init__(
        self,
        *,
        name: str,
        plugin_type: int,
        short_description: str,
        description: str,
        author: str,
        email: str,
        support_url: str,
        icon: str = None
    ):

        self.name = name
        self.plugin_type = plugin_type
        self.short_description = short_description
        self.description = description
        self.author = author
        self.email = email
        self.support_url = support_url
        self.icon = icon
