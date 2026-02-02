from nomad.config.models.plugins import AppEntryPoint
from nomad.config.models.ui import App, Column, Columns, FilterMenu, FilterMenus

app_entry_point = AppEntryPoint(
    name="Filter Plugin",
    description="New app entry point configuration.",
    app=App(
        label="Filter Plugin",
        path="app",
        category="simulation",
        columns=Columns(
            selected=["entry_id"],
            options={
                "entry_id": Column(),
            },
        ),
        filter_menus=FilterMenus(
            options={
                "material": FilterMenu(label="Material"),
            }
        ),
    ),
)
