import os

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class LauncherApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.lyrilika.touhoulauncher")

    def do_activate(self):
        from page_games import create_games_page

        window = Gtk.ApplicationWindow(application=self)
        window.set_title("Touhou Launcher")
        window.set_default_size(1280, 720)

        stack = Gtk.Stack()
        stack_switcher = Gtk.StackSwitcher(stack=stack)
        page_games = create_games_page()
        page_fangames = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        page_manga = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        stack.add_titled(page_games, "games", "Games")
        stack.add_titled(page_fangames, "fangames", "Fan Games")
        stack.add_titled(page_manga, "manga", "Mangas")
        stack_switcher.set_halign(Gtk.Align.CENTER)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        container.append(stack_switcher)
        container.append(stack)
        window.set_child(container)

        css_path = os.path.join(BASE_DIR, "style.css")
        provider = Gtk.CssProvider()
        provider.load_from_path(css_path)
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        window.present()


app = LauncherApp()
app.run(None)
