import json
import os
import hashlib
import shlex
import shutil
import urllib.request
import tarfile
import zipfile
import tempfile
import subprocess
import tarfile
import tempfile
import threading
import urllib.request
import re
from pathlib import Path

from gi.repository import Gtk, GLib, Pango

OPEN_SETTINGS_POPOVERS = []
SETTINGS_REFRESHERS = {}
ACTIVE_GAME = None
ACTIVE_GAME_TITLE = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "touhou-launcher",
    "games_config.json",
)
PREFIX_ROOT = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "touhou-launcher",
    "prefixes",
)
UMU_DATA_ROOT = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "umu",
)
UMU_RUNTIME_NAME = "steamrt4"
DOSBOX_ROOT = os.path.join(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")), "touhou-launcher", "dosbox-x")
DOSBOX_BINARY = os.path.join(DOSBOX_ROOT, "dosbox-x")
CARD_WIDTH = 180
CARD_SPACING = 15


def get_umu_path():
    bundled = os.path.join(BASE_DIR, "resources", "umu-run")
    if os.path.isfile(bundled) and os.access(bundled, os.X_OK):
        return bundled
    return "umu-run"


def get_config_dir():
    path = os.path.dirname(CONFIG_FILE)
    os.makedirs(path, exist_ok=True)
    return path


def load_config():
    get_config_dir()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            raw = json.loads(content) if content else {}
    else:
        raw = {}

    config = {}
    for game_key, value in raw.items():
        if isinstance(value, str):
            config[game_key] = {
                "exe": value,
                "launch_options": "",
                "runner": "wine",
            }
        else:
            runner = value.get("runner", "wine")
            if runner not in ("wine", "ge-proton", "dosbox-x"):
                runner = "wine"
            config[game_key] = {
                "exe": value.get("exe"),
                "launch_options": value.get("launch_options", ""),
                "runner": runner,
            }
    return config


def save_config(config):
    get_config_dir()
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    os.replace(tmp, CONFIG_FILE)


class GameFlowBox(Gtk.FlowBox):
    def do_measure(self, orientation, for_size):
        min_size, nat_size, min_baseline, nat_baseline = Gtk.FlowBox.do_measure(
            self, orientation, for_size
        )
        if orientation == Gtk.Orientation.HORIZONTAL:
            min_size = CARD_WIDTH + self.get_margin_start() + self.get_margin_end()
        return (min_size, nat_size, min_baseline, nat_baseline)

    def do_size_allocate(self, width, height, baseline):
        content_width = width - self.get_margin_start() - self.get_margin_end()
        columns = max(1, (content_width + CARD_SPACING) // (CARD_WIDTH + CARD_SPACING))
        if self.get_max_children_per_line() != columns:
            self.set_max_children_per_line(columns)
            self.set_min_children_per_line(columns)
        Gtk.FlowBox.do_size_allocate(self, width, height, baseline)


def create_games_page():
    outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    outer_box.set_margin_start(30)
    outer_box.set_margin_end(30)
    outer_box.set_margin_top(30)
    outer_box.set_margin_bottom(30)

    header = Gtk.Label(label="Game Library")
    header.add_css_class("title")
    outer_box.append(header)

    scroll = Gtk.ScrolledWindow()
    scroll.set_vexpand(True)
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    flow_box = GameFlowBox()
    flow_box.set_hexpand(True)
    flow_box.set_row_spacing(CARD_SPACING)
    flow_box.set_column_spacing(CARD_SPACING)
    flow_box.set_margin_start(10)
    flow_box.set_margin_end(10)
    flow_box.set_margin_top(15)
    flow_box.set_margin_bottom(15)
    flow_box.set_valign(Gtk.Align.START)
    flow_box.set_homogeneous(True)
    flow_box.set_selection_mode(Gtk.SelectionMode.NONE)

    config = load_config()
    games = [
        ("Touhou 1: The Highly Responsive to Prayers", "th1", "th1.jpg"),
        ("Touhou 2: Story of Eastern Wonderland", "th2", "th2.jpg"),
        ("Touhou 3: Phantasmagoria of Dim.Dream", "th3", "th3.jpg"),
        ("Touhou 4: Lotus Land Story", "th4", "th4.jpg"),
        ("Touhou 5: Mystic Square", "th5", "th5.jpg"),
        ("Touhou 6: The Embodiment of Scarlet Devil", "th6", "th6.jpg"),
        ("Touhou 7: Perfect Cherry Blossom", "th7", "th7.jpg"),
        ("Touhou 7.5: Immaterial and Missing Power", "th7.5", "th75.jpg"),
        ("Touhou 8: Imperishable Night", "th8", "th8.jpg"),
        ("Touhou 9: Phantasmagoria of Flower View", "th9", "th9.jpg"),
        ("Touhou 9.5: Shoot the Bullet", "th9.5", "th95.jpg"),
        ("Touhou 10: Mountain of Faith", "th10", "th10.jpg"),
        ("Touhou 10.5: Scarlet Weather Rhapsody", "th10.5", "th105.jpg"),
        ("Touhou 11: Subterranean Animism", "th11", "th11.jpg"),
        ("Touhou 12: Undefined Fantastic Object", "th12", "th12.jpg"),
        ("Touhou 12.3: Hisoutensoku", "th12.3", "th123.jpg"),
        ("Touhou 12.5: Double Spoiler", "th12.5", "th125.jpg"),
        ("Touhou 12.8: Great Fairy Wars", "th12.8", "th128.jpg"),
        ("Touhou 13: Ten Desires", "th13", "th13.jpg"),
        ("Touhou 13.5: Hopeless Masquerade", "th13.5", "th135.jpg"),
        ("Touhou 14: Double Dealing Character", "th14", "th14.jpg"),
        ("Touhou 14.3: Impossible Spell Card", "th14.3", "th143.jpg"),
        ("Touhou 14.5: Urban Legend in Limbo", "th14.5", "th145.jpg"),
        ("Touhou 15: Legacy of Lunatic Kingdom", "th15", "th15.jpg"),
        ("Touhou 15.5: Antinomy of Common Flowers", "th15.5", "th155.jpg"),
        ("Touhou 16: Hidden Star in Four Seasons", "th16", "th16.jpg"),
        ("Touhou 16.5: Violet Detector", "th16.5", "th165.jpg"),
        ("Touhou 17: Wily Beast and Weakest Creature", "th17", "th17.jpg"),
        ("Touhou 17.5: Sunken Fossil World", "th17.5", "th175.jpg"),
        ("Touhou 18: Unconnected Marketeers", "th18", "th18.jpg"),
        ("Touhou 18.5: 100th Black Market", "th18.5", "th185.jpg"),
        ("Touhou 19: Unfinished Dream of All Living Ghost", "th19", "th19.jpg"),
        ("Touhou 20: Fossilized Wonders", "th20", "th20.jpg"),
    ]

    running_bar = create_running_bar()
    running_bar.set_visible(False)

    for game_title, game_key, image_file in games:
        card = create_game_card(game_title, game_key, image_file, config, running_bar)
        flow_box.append(card)

    scroll.set_child(flow_box)
    library_overlay = Gtk.Overlay()
    library_overlay.set_child(scroll)
    library_overlay.set_measure_overlay(running_bar, False)
    library_overlay.add_overlay(running_bar)
    running_bar.set_halign(Gtk.Align.FILL)
    running_bar.set_valign(Gtk.Align.END)
    outer_box.append(library_overlay)

    outside_click = Gtk.GestureClick()
    outside_click.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
    def on_outside_click(_gesture, _n_press, x, y):
        target = outer_box.pick(x, y, Gtk.PickFlags.DEFAULT)
        for button, _popover in OPEN_SETTINGS_POPOVERS:
            if target is not None and _is_descendant(target, button):
                return
        dismiss_settings_popovers()
    outside_click.connect("pressed", on_outside_click)
    outer_box.add_controller(outside_click)
    return outer_box

def ge_proton_directory():
    data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return os.path.join(data_home, "Steam", "compatibilitytools.d")


def ge_proton_installed():
    directory = ge_proton_directory()
    if not os.path.isdir(directory):
        return False
    return any(
        name.startswith("GE-Proton") and os.path.isdir(os.path.join(directory, name))
        for name in os.listdir(directory)
    )


def latest_ge_proton_info():
    api_url = "https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest"
    request = urllib.request.Request(
        api_url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Touhou-Launcher"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        release = json.load(response)

    if os.uname().machine in ("x86_64", "amd64"):
        suffix = "-x86_64.tar.gz"
    elif os.uname().machine in ("aarch64", "arm64"):
        suffix = "-aarch64.tar.gz"
    else:
        raise RuntimeError(f"Unsupported architecture: {os.uname().machine}")

    tarball_url = None
    checksum_url = None
    tarball_name = None

    for asset in release.get("assets", []):
        name = asset.get("name", "")
        url = asset.get("browser_download_url")
        if name.endswith(suffix):
            tarball_name = name
            tarball_url = url

    if not tarball_url or not tarball_name:
        raise RuntimeError("Could not find the latest GE-Proton release for this architecture")

    expected_checksum_name = f"{tarball_name[:-len('.tar.gz')]}.sha512sum"
    for asset in release.get("assets", []):
        if asset.get("name") == expected_checksum_name:
            checksum_url = asset.get("browser_download_url")
            break

    release_name = tarball_name[:-len(".tar.gz")]
    return release_name, tarball_url, checksum_url


def _download_file_with_progress(url, destination, progress_callback):
    request = urllib.request.Request(url, headers={"User-Agent": "Touhou-Launcher"})
    with urllib.request.urlopen(request, timeout=30) as response, open(destination, "wb") as output:
        total = response.headers.get("Content-Length")
        total = int(total) if total else 0
        downloaded = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            downloaded += len(chunk)
            if total:
                progress_callback(min(100, int(downloaded * 100 / total)))
            else:
                progress_callback(None)


def _read_sha512sum_file(path, tarball_name):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].lstrip("*") == tarball_name:
            return parts[0]
    for line in text.splitlines():
        value = line.strip().split()[0] if line.strip() else ""
        if len(value) == 128 and all(c in "0123456789abcdefABCDEF" for c in value):
            return value
    return None


def _install_latest_ge_proton(progress_callback):
    release_name, tarball_url, checksum_url = latest_ge_proton_info()
    install_dir = ge_proton_directory()
    target_dir = os.path.join(install_dir, release_name)

    if os.path.isdir(target_dir):
        progress_callback(100)
        return True

    os.makedirs(install_dir, exist_ok=True)
    tarball_name = os.path.basename(tarball_url)

    with tempfile.TemporaryDirectory(prefix="touhou-ge-proton-") as temp_dir:
        tarball_path = os.path.join(temp_dir, tarball_name)
        checksum_path = os.path.join(temp_dir, f"{tarball_name}.sha512sum")

        progress_callback(0)
        _download_file_with_progress(tarball_url, tarball_path, progress_callback)

        if checksum_url:
            _download_file_with_progress(checksum_url, checksum_path, lambda _percent: None)
            expected = _read_sha512sum_file(checksum_path, tarball_name)
            if expected:
                digest = hashlib.sha512()
                with open(tarball_path, "rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                if digest.hexdigest().lower() != expected.lower():
                    raise RuntimeError("GE-Proton checksum verification failed")

        staging_dir = tempfile.mkdtemp(prefix="ge-proton-install-", dir=install_dir)
        try:
            with tarfile.open(tarball_path, "r:gz") as archive:
                root = os.path.realpath(staging_dir)
                for member in archive.getmembers():
                    destination = os.path.realpath(os.path.join(staging_dir, member.name))
                    if not destination.startswith(root + os.sep):
                        raise RuntimeError("Unsafe path found in GE-Proton archive")
                if hasattr(tarfile, 'data_filter'):
                    archive.extractall(staging_dir, filter='data')
                else:
                    archive.extractall(staging_dir)

            extracted = os.path.join(staging_dir, release_name)
            if not os.path.isdir(extracted):
                raise RuntimeError("GE-Proton archive did not contain the expected directory")
            os.replace(extracted, target_dir)
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

    progress_callback(100)
    return True


def update_runner_status(label):
    if ge_proton_installed():
        label.set_text("GE-Proton: installed")
        label.remove_css_class("runner-missing")
        label.add_css_class("runner-installed")
    else:
        label.set_text("GE-Proton: not downloaded")
        label.remove_css_class("runner-installed")
        label.add_css_class("runner-missing")


def on_download_ge_clicked(button, status_label, download_button, progress_bar=None):
    download_button.set_sensitive(False)
    status_label.set_text("GE-Proton: checking for latest release…")
    status_label.remove_css_class("runner-missing")
    status_label.remove_css_class("runner-installed")
    status_label.add_css_class("runner-downloading")
    if progress_bar is not None:
        progress_bar.set_fraction(0)
        progress_bar.set_text("0%")
        progress_bar.set_visible(True)

    def update_progress(percent):
        def update():
            if percent is None:
                status_label.set_text("GE-Proton: downloading…")
                if progress_bar is not None:
                    progress_bar.set_text("Downloading…")
            else:
                status_label.set_text(f"GE-Proton: downloading… {percent}%")
                if progress_bar is not None:
                    progress_bar.set_fraction(percent / 100.0)
                    progress_bar.set_text(f"{percent}%")
            return False
        GLib.idle_add(update)

    def worker():
        try:
            ok = _install_latest_ge_proton(update_progress)
        except Exception as error:
            ok = False
            error_text = str(error)
        else:
            error_text = ""

        def finish():
            download_button.set_sensitive(True)
            status_label.remove_css_class("runner-downloading")
            if progress_bar is not None:
                progress_bar.set_fraction(1.0 if ok else progress_bar.get_fraction())
                progress_bar.set_text("100%" if ok else "Failed")
            update_runner_status(status_label)
            if not ok:
                status_label.set_text(f"GE-Proton: download failed — {error_text}")
                status_label.add_css_class("runner-missing")
            return False

        GLib.idle_add(finish)

    threading.Thread(target=worker, daemon=True).start()


def dismiss_settings_popovers(except_popover=None):
    for _button, popover in OPEN_SETTINGS_POPOVERS:
        if popover is not except_popover and popover.is_visible():
            popover.popdown()

def create_game_card(title, game_key, image_file, config, running_bar):
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    card.set_size_request(CARD_WIDTH, 240)
    card.set_halign(Gtk.Align.CENTER)
    card.add_css_class("card-border")

    entry = config.get(game_key, {})
    exe_path = entry.get("exe")
    runner = entry.get("runner", "wine")
    if runner not in ("wine", "ge-proton", "dosbox-x"):
        runner = "wine"

    if exe_path and os.path.exists(exe_path):
        card.add_css_class("enabled-card")
        card.remove_css_class("disabled-card")
    else:
        card.add_css_class("disabled-card")
        card.remove_css_class("enabled-card")

    thumb = Gtk.Picture()
    thumb.set_filename(os.path.join(BASE_DIR, "Covers", image_file))
    thumb.set_size_request(170, 170)
    thumb.set_hexpand(False)
    thumb.set_vexpand(False)
    thumb.set_halign(Gtk.Align.CENTER)
    thumb.set_valign(Gtk.Align.CENTER)
    thumb.set_content_fit(Gtk.ContentFit.COVER)
    thumb.add_css_class("thumbnail")

    overlay = Gtk.Overlay()
    overlay.set_child(thumb)

    title_label = Gtk.Label()
    update_title_label(title_label, title, exe_path, runner)
    title_label.set_halign(Gtk.Align.CENTER)
    title_label.set_wrap(True)
    title_label.set_max_width_chars(16)

    settings_icon = Gtk.Image.new_from_icon_name("preferences-system-symbolic")
    settings_icon.set_pixel_size(15)
    settings_button = Gtk.Button()
    settings_button.set_child(settings_icon)
    settings_button.add_css_class("settings-button")
    settings_button.add_css_class("circular")
    settings_button.add_css_class("flat")
    settings_button.set_halign(Gtk.Align.END)
    settings_button.set_valign(Gtk.Align.START)
    overlay.add_overlay(settings_button)
    settings_popover = create_settings_popover(
        settings_button, title, game_key, config, title_label, card
    )
    def toggle_settings(_button):
        if settings_popover.is_visible():
            settings_popover.popdown()
        else:
            dismiss_settings_popovers(settings_popover)
            settings_popover.popup()
    settings_button.connect("clicked", toggle_settings)
    OPEN_SETTINGS_POPOVERS.append((settings_button, settings_popover))

    card.append(overlay)
    card.append(title_label)

    click_controller = Gtk.GestureClick.new()
    click_controller.connect(
        "pressed", on_card_clicked, title, game_key, config, title_label, card, settings_button, running_bar
    )
    card.add_controller(click_controller)
    return card



def update_title_label(label, title, exe_path, runner):
    if exe_path:
        label.set_text(title)
        label.remove_css_class("heading-disabled")
        label.add_css_class("heading-enabled")
    else:
        label.set_text(f"{title}\n[NOT SET]")
        label.add_css_class("heading-disabled")
        label.remove_css_class("heading-enabled")


def _is_descendant(widget, ancestor):
    while widget is not None:
        if widget == ancestor:
            return True
        widget = widget.get_parent()
    return False


def on_card_clicked(controller, n_press, x, y, title, game_key, config, label, card, settings_button, running_bar):
    target = card.pick(x, y, Gtk.PickFlags.DEFAULT)
    if target is not None and _is_descendant(target, settings_button):
        return

    entry = config.get(game_key, {})
    exe_path = entry.get("exe")
    if exe_path and os.path.exists(exe_path):
        launch_game(
            exe_path,
            entry.get("launch_options", ""),
            entry.get("runner", "wine"),
            game_key,
            card,
            title,
            running_bar,
        )
    else:
        prompt_for_exe(title, game_key, config, label, card)


def get_dosbox_path():
    candidates = (
        DOSBOX_BINARY,
        os.path.join(DOSBOX_ROOT, "dosbox-x.AppImage"),
        os.path.join(DOSBOX_ROOT, "dosbox-x"),
    )
    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    system = shutil.which("dosbox-x")
    if system:
        return system

    return None


def dosbox_installed():
    return get_dosbox_path() is not None

def install_dosbox(button, status):
    global DOSBOX_BINARY

    def update_status(text):
        GLib.idle_add(status.set_text, text)

    def worker():
        try:
            update_status("Downloading DOSBox-X...")

            os.makedirs(DOSBOX_ROOT, exist_ok=True)

            api = "https://api.github.com/repos/pkgforge-dev/DOSBox-X-AppImage/releases/latest"
            req = urllib.request.Request(api, headers={"User-Agent": "Lyrilika"})
            with urllib.request.urlopen(req, timeout=15) as response:
                release = json.loads(response.read().decode("utf-8"))

            asset_url = None
            for asset in release.get("assets", []):
                name = asset.get("name", "").lower()
                if "appimage" in name and ("x86_64" in name or "amd64" in name):
                    asset_url = asset.get("browser_download_url")
                    break

            if not asset_url:
                raise RuntimeError("No compatible DOSBox-X build found")

            out = os.path.join(DOSBOX_ROOT, "dosbox-x.AppImage")

            with urllib.request.urlopen(asset_url) as response, open(out, "wb") as f:
                total = response.headers.get("Content-Length")
                total = int(total) if total else 0
                done = 0

                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        percent = int(done * 100 / total)
                        update_status(f"Downloading DOSBox-X... {percent}%")

            os.chmod(out, 0o755)

            try:
                if os.path.exists(DOSBOX_BINARY):
                    os.remove(DOSBOX_BINARY)
                os.symlink(out, DOSBOX_BINARY)
            except Exception:
                pass

            update_status("Installed")

        except Exception as e:
            update_status("Install failed: " + str(e))

    threading.Thread(target=worker, daemon=True).start()


def dosbox_config_for_touhou(rom):
    rom = os.path.abspath(rom)
    return [
        "-set", "machine=pc98",
        "-c", f'IMGMOUNT C "{rom}"',
        "-c", "C:",
        "-c", "GAME"
    ]

def show_dosbox_missing(parent=None):
    window = None
    if parent is not None:
        try:
            root = parent.get_root()
            if isinstance(root, Gtk.Window):
                window = root
        except Exception:
            pass

    dialog = Gtk.MessageDialog(
        transient_for=window,
        modal=True,
        buttons=Gtk.ButtonsType.OK,
        message_type=Gtk.MessageType.ERROR,
        text="DOSBox-X is not installed\n\nUse the Download DOSBox-X button in the settings, or manually install DOSBox-X and restart the app.",
    )
    dialog.connect("response", lambda d, r: d.destroy())
    dialog.show()

def build_launch_command(exe_path, launch_options, runner, game_key):
    if runner == "dosbox-x":
        db = get_dosbox_path()
        if not db:
            raise FileNotFoundError("DOSBox-X is not installed")
        return [db] + dosbox_config_for_touhou(exe_path), os.environ.copy()
    options = (launch_options or "").strip()
    option_parts = shlex.split(options) if options else []
    game_dir = os.path.dirname(os.path.abspath(exe_path))

    if runner == "ge-proton":
        prefix = os.path.join(PREFIX_ROOT, game_key)
        os.makedirs(prefix, exist_ok=True)
        env = os.environ.copy()
        env["WINEPREFIX"] = prefix
        env["GAMEID"] = "0"
        env["PROTONPATH"] = "GE-Proton"
        env["STEAM_COMPAT_INSTALL_PATH"] = game_dir
        env["STEAM_COMPAT_LIBRARY_PATHS"] = game_dir
        umu = get_umu_path()
        base_command = [umu, exe_path]
        if "%command%" in options:
            before, after = options.split("%command%", 1)
            before_args = shlex.split(before) if before.strip() else []
            after_args = shlex.split(after) if after.strip() else []
            command = before_args + base_command + after_args
        else:
            command = base_command + option_parts
        return command, env

    env = os.environ.copy()
    base_command = ["wine", exe_path]
    if "%command%" in options:
        before, after = options.split("%command%", 1)
        before_args = shlex.split(before) if before.strip() else []
        after_args = shlex.split(after) if after.strip() else []
        command = before_args + base_command + after_args
    else:
        command = base_command + option_parts
    return command, env


def show_runner_error(card, title):
    root = card.get_root()
    parent = root if isinstance(root, Gtk.Window) else None
    dialog = Gtk.AlertDialog()
    dialog.set_message("GE-Proton is not installed")
    dialog.set_detail(f"Download GE-Proton from the settings for {title} before launching this game with GE-Proton.")
    dialog.show(parent)


def show_running_error(card, title, launch_callback):
    root = card.get_root()
    parent = root if isinstance(root, Gtk.Window) else None
    dialog = Gtk.AlertDialog()
    same_game = ACTIVE_GAME_TITLE == title
    if same_game:
        dialog.set_message("This game is already running")
        dialog.set_detail(f"{title} is already running.")
        dialog.set_buttons(["Close & Relaunch", "Cancel"])
    else:
        current_title = ACTIVE_GAME_TITLE or "the current game"
        dialog.set_message("A game is already running")
        dialog.set_detail(f"Close {current_title} first and then launch {title}?")
        dialog.set_buttons(["Close Current Game", "Cancel"])
    dialog.set_default_button(0)
    dialog.set_cancel_button(1)

    def response(_dialog, result, _user_data):
        try:
            selected = dialog.choose_finish(result)
        except GLib.Error:
            return
        if selected == 0:
            stop_current_game_and_then(launch_callback)

    dialog.choose(parent, None, response, None)


def umu_runtime_installed():
    runtime_dir = os.path.join(UMU_DATA_ROOT, UMU_RUNTIME_NAME)
    if not os.path.isdir(runtime_dir):
        return False
    try:
        with os.scandir(runtime_dir) as entries:
            return next(entries, None) is not None
    except OSError:
        return False


def create_umu_setup_window(card):
    root = card.get_root()
    parent = root if isinstance(root, Gtk.Window) else None

    window = Gtk.Window()
    window.set_title("UMU Setup")
    window.set_modal(True)
    window.set_deletable(False)
    window.set_resizable(False)
    if parent is not None:
        window.set_transient_for(parent)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.set_margin_start(24)
    box.set_margin_end(24)
    box.set_margin_top(20)
    box.set_margin_bottom(20)

    title = Gtk.Label(label="UMU is setting up")
    title.add_css_class("popover-heading")
    title.set_halign(Gtk.Align.START)
    box.append(title)

    runtime = Gtk.Label(label=f"Installing runtime: {UMU_RUNTIME_NAME}")
    runtime.set_halign(Gtk.Align.START)
    box.append(runtime)

    progress = Gtk.ProgressBar()
    progress.set_show_text(True)
    progress.set_fraction(0)
    progress.set_text("0%")
    box.append(progress)

    status = Gtk.Label(label="Preparing…")
    status.set_halign(Gtk.Align.START)
    status.add_css_class("running-status")
    box.append(status)

    window.set_child(box)
    window.present()
    return window, runtime, progress, status


def monitor_umu_setup(process, window, runtime_label, progress_bar, status_label):
    def worker():
        finished = False
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                runtime_match = re.search(r"runtime ['\"]([^'\"]+)['\"]", line)
                percent_matches = re.findall(r"(?<!\d)(\d{1,3})%", line)
                percent = int(percent_matches[-1]) if percent_matches else None
                runtime_name = runtime_match.group(1) if runtime_match else None
                if "Running '" in line and "using runtime" in line:
                    finished = True

                def update(runtime_name=runtime_name, percent=percent, finished=finished):
                    if runtime_name:
                        runtime_label.set_text(f"Installing runtime: {runtime_name}")
                    if percent is not None:
                        value = min(100, percent)
                        progress_bar.set_fraction(value / 100.0)
                        progress_bar.set_text(f"{value}%")
                    if finished:
                        progress_bar.set_fraction(1.0)
                        progress_bar.set_text("100%")
                        status_label.set_text("Setup complete")
                        window.close()
                    elif percent is not None:
                        status_label.set_text("Downloading…")
                    return False

                GLib.idle_add(update)
                if finished:
                    break
        finally:
            def close_if_needed():
                if window.get_visible() and process.poll() is not None:
                    if process.returncode == 0:
                        progress_bar.set_fraction(1.0)
                        progress_bar.set_text("100%")
                        status_label.set_text("Setup complete")
                    else:
                        status_label.set_text("Setup finished with an error")
                    window.close()
                return False
            GLib.idle_add(close_if_needed)

    threading.Thread(target=worker, daemon=True).start()


def prompt_for_exe(title, game_key, config, label, card):
    root = card.get_root()
    parent = root if isinstance(root, Gtk.Window) else None
    pc98 = game_key in ("th1", "th2", "th3", "th4", "th5")
    dialog = Gtk.FileChooserNative.new(
        title=(f"Select ROM for {title}" if pc98 else f"Select EXE for {title}"),
        parent=parent,
        action=Gtk.FileChooserAction.OPEN,
        accept_label="Select",
        cancel_label="Cancel",
    )
    filter_exe = Gtk.FileFilter()
    if pc98:
        filter_exe.set_name("PC-98 ROM images")
        for ext in ("*.hdi", "*.nhd", "*.fdi", "*.img", "*.d88"):
            filter_exe.add_pattern(ext)
    else:
        filter_exe.set_name("Executable files")
        filter_exe.add_pattern("*.exe")
    dialog.add_filter(filter_exe)
    dialog.connect("response", on_dialog_response, title, game_key, config, label, card)
    dialog.show()


def on_dialog_response(dialog, response, title, game_key, config, label, card):
    if response == Gtk.ResponseType.ACCEPT:
        file = dialog.get_file()
        path = file.get_path()
        entry = config.setdefault(
            game_key, {"exe": None, "launch_options": "", "runner": "wine"}
        )
        entry["exe"] = path
        if game_key in ("th1", "th2", "th3", "th4", "th5"):
            entry["runner"] = "dosbox-x"
        else:
            entry.setdefault("runner", "wine")
        save_config(config)
        update_title_label(label, title, path, entry["runner"])
        if game_key in SETTINGS_REFRESHERS:
            SETTINGS_REFRESHERS[game_key]()
        card.remove_css_class("disabled-card")
        card.add_css_class("enabled-card")
    dialog.destroy()


def proc_exists(pid):
    status_path = f"/proc/{pid}/stat"
    try:
        data = Path(status_path).read_text(encoding="utf-8", errors="replace")
    except (FileNotFoundError, PermissionError, OSError):
        return False
    closing = data.rfind(")")
    if closing == -1:
        return True
    fields = data[closing + 2:].split()
    return not fields or fields[0] != "Z"


def proc_children(pid):
    path = f"/proc/{pid}/task/{pid}/children"
    try:
        data = Path(path).read_text(encoding="ascii").strip()
    except (FileNotFoundError, PermissionError, OSError):
        return []
    return [int(value) for value in data.split() if value.isdigit()]


def process_tree_snapshot(root_pid, known=None):
    pids = set(known or ())
    if proc_exists(root_pid):
        pids.add(root_pid)
        pending = [root_pid]
        seen = set()
        while pending:
            pid = pending.pop()
            if pid in seen or not proc_exists(pid):
                continue
            seen.add(pid)
            children = proc_children(pid)
            for child in children:
                if child not in pids:
                    pids.add(child)
                if child not in seen:
                    pending.append(child)
    return pids


def process_group_has_live_member(pgid):
    try:
        entries = os.listdir("/proc")
    except OSError:
        return False
    prefix = "/proc/"
    for name in entries:
        if not name.isdigit():
            continue
        path = f"{prefix}{name}/stat"
        try:
            data = Path(path).read_text(encoding="ascii")
        except (FileNotFoundError, PermissionError, OSError):
            continue
        closing = data.rfind(")")
        if closing == -1:
            continue
        fields = data[closing + 2:].split()
        if len(fields) >= 3 and fields[0] != "Z":
            try:
                if int(fields[2]) == pgid:
                    return True
            except ValueError:
                continue
    return False


SESSION_ENV_VAR = "TOUHOU_LAUNCHER_SESSION"

WINE_SYSTEM_EXES = {
    "services.exe", "winedevice.exe", "plugplay.exe", "svchost.exe", "explorer.exe",
    "rpcss.exe", "conhost.exe", "start.exe", "winemenubuilder.exe", "wineboot.exe",
    "rundll32.exe", "mscorsvw.exe", "tabtip.exe", "steam.exe", "iexplore.exe",
    "winedbg.exe", "cmd.exe",
}


def _session_marker(token):
    return f"{SESSION_ENV_VAR}={token}".encode()


def session_pids(token):
    """All live (non-zombie) processes carrying our per-launch environment marker.

    Wine starts child Windows processes with a double fork + setsid(), so they leave
    both our process tree and our process group, but they still inherit the
    environment. This is the only reliable way to find e.g. the real game started by
    a TH6 patcher/loader exe that exits right away.
    """
    if not token:
        return []
    marker = _session_marker(token)
    own_pid = os.getpid()
    found = []
    try:
        entries = os.listdir("/proc")
    except OSError:
        return found
    for name in entries:
        if not name.isdigit() or int(name) == own_pid:
            continue
        try:
            with open(f"/proc/{name}/environ", "rb") as f:
                environ = f.read()
        except OSError:
            continue
        if marker in environ.split(b"\0") and proc_exists(int(name)):
            found.append(int(name))
    return found


def _windows_exe_name(pid):
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            argv = f.read().split(b"\0")
    except OSError:
        return None
    for arg in argv[:2]:
        text = arg.decode("utf-8", "replace").strip()
        base = re.split(r"[\\/]", text)[-1].lower()
        if base.endswith(".exe"):
            return base
    return None


def session_game_alive(token):
    for pid in session_pids(token):
        exe = _windows_exe_name(pid)
        if exe and exe not in WINE_SYSTEM_EXES:
            return True
    return False


def process_tree_exists(process):
    if process is None:
        return False
    process.poll()
    if process.returncode is None:
        return True
    if process_group_has_live_member(process.pid):
        return True
    state = getattr(process, "_touhou_tree_pids", set())
    state = {pid for pid in state if proc_exists(pid)}
    state.update(process_tree_snapshot(process.pid, state))
    process._touhou_tree_pids = state
    state.discard(process.pid)
    if any(proc_exists(pid) for pid in state):
        return True
    return session_game_alive(getattr(process, "_touhou_session", None))


def send_process_group_signal(process, signal):
    try:
        os.killpg(process.pid, signal)
    except ProcessLookupError:
        pass
    except PermissionError:
        try:
            process.send_signal(signal)
        except ProcessLookupError:
            pass
    for pid in session_pids(getattr(process, "_touhou_session", None)):
        try:
            os.kill(pid, signal)
        except (ProcessLookupError, PermissionError):
            pass


def stop_current_game_and_then(callback):
    global ACTIVE_GAME
    process = ACTIVE_GAME
    if process is None:
        callback()
        return
    send_process_group_signal(process, 15)
    elapsed = 0

    def finish_stop():
        nonlocal elapsed
        global ACTIVE_GAME
        if not process_tree_exists(process):
            ACTIVE_GAME = None
            callback()
            return False
        elapsed += 100
        if elapsed >= 1500:
            send_process_group_signal(process, 9)
            ACTIVE_GAME = None
            callback()
            return False
        return True

    GLib.timeout_add(100, finish_stop)


def launch_game(exe_path, launch_options, runner, game_key, card, title, running_bar):
    if game_key and any(k in str(game_key).lower() for k in ("th01", "th02", "th03", "th04", "th05")):
        runner = "dosbox-x"

    if ACTIVE_GAME is not None and process_tree_exists(ACTIVE_GAME):
        show_running_error(
            card,
            title,
            lambda: launch_game(exe_path, launch_options, runner, game_key, card, title, running_bar),
        )
        return
    if runner == "ge-proton" and not ge_proton_installed():
        show_runner_error(card, title)
        return
    game_dir = os.path.dirname(exe_path)
    if runner == "dosbox-x":
        dosbox_path = get_dosbox_path()
        if not dosbox_path:
            show_dosbox_missing(card)
            return

    try:
        command, env = build_launch_command(exe_path, launch_options, runner, game_key)
    except FileNotFoundError:
        if runner == "dosbox-x":
            show_dosbox_missing(card)
            return
        raise
    session_token = os.urandom(8).hex()
    env[SESSION_ENV_VAR] = session_token
    setup_window = None
    setup_widgets = None
    if runner == "ge-proton" and not umu_runtime_installed():
        setup_window, runtime_label, progress_bar, status_label = create_umu_setup_window(card)
        setup_widgets = (setup_window, runtime_label, progress_bar, status_label)
    process = subprocess.Popen(
        command,
        cwd=game_dir,
        env=env,
        start_new_session=True,
        stdout=subprocess.PIPE if setup_window else None,
        stderr=subprocess.STDOUT if setup_window else None,
        text=True if setup_window else False,
        bufsize=1 if setup_window else -1,
    )
    process._touhou_tree_pids = {process.pid}
    process._touhou_session = session_token
    if setup_widgets:
        monitor_umu_setup(process, *setup_widgets)
    show_running_game(running_bar, process, title)


def hide_running_game(running_bar):
    global ACTIVE_GAME, ACTIVE_GAME_TITLE
    ACTIVE_GAME = None
    ACTIVE_GAME_TITLE = None
    running_bar.set_visible(False)


def show_running_game(running_bar, process, title):
    global ACTIVE_GAME, ACTIVE_GAME_TITLE
    ACTIVE_GAME = process
    ACTIVE_GAME_TITLE = title
    process._touhou_tree_pids = {process.pid}
    running_bar.name_label.set_text(title)
    running_bar.set_visible(True)

    def poll():
        if ACTIVE_GAME is not process:
            return False
        if process_tree_exists(process):
            return True
        hide_running_game(running_bar)
        return False

    GLib.timeout_add(250, poll)


def kill_running_game(running_bar):
    global ACTIVE_GAME
    process = ACTIVE_GAME
    if process is None:
        return

    process._touhou_tree_pids = process_tree_snapshot(
        process.pid, getattr(process, "_touhou_tree_pids", set())
    )

    send_process_group_signal(process, 15)
    elapsed = 0

    def wait_then_force_kill():
        nonlocal elapsed
        if ACTIVE_GAME is not process:
            return False

        if not process_tree_exists(process):
            hide_running_game(running_bar)
            return False

        elapsed += 100
        if elapsed >= 1000:
            send_process_group_signal(process, 9)

            for pid in list(getattr(process, "_touhou_tree_pids", set())):
                try:
                    os.kill(pid, 9)
                except (ProcessLookupError, PermissionError):
                    pass

            hide_running_game(running_bar)
            return False

        return True

    GLib.timeout_add(100, wait_then_force_kill)


def create_running_bar():
    bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    bar.set_margin_start(10)
    bar.set_margin_end(10)
    bar.set_margin_top(4)
    bar.set_margin_bottom(4)
    bar.set_size_request(-1, 26)
    bar.set_vexpand(False)
    bar.set_hexpand(True)
    bar.add_css_class("running-bar")

    name = Gtk.Label()
    name.set_halign(Gtk.Align.START)
    name.set_valign(Gtk.Align.CENTER)
    name.set_hexpand(True)
    name.set_ellipsize(Pango.EllipsizeMode.END)
    name.add_css_class("running-name")
    bar.append(name)
    bar.name_label = name

    status = Gtk.Label(label="Running")
    status.set_valign(Gtk.Align.CENTER)
    status.add_css_class("running-status")
    bar.append(status)

    kill_button = Gtk.Button(label="Stop")
    kill_button.add_css_class("destructive-action")
    kill_button.set_valign(Gtk.Align.CENTER)
    kill_button.connect("clicked", lambda _button: kill_running_game(bar))
    bar.append(kill_button)
    return bar


def create_settings_popover(button, title, game_key, config, label, card):
    entry = config.get(game_key, {})
    exe_path = entry.get("exe")
    launch_options = entry.get("launch_options", "")
    runner = entry.get("runner", "wine")

    popover = Gtk.Popover()
    popover.set_parent(button)
    popover.set_position(Gtk.PositionType.BOTTOM)
    popover.set_autohide(False)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.set_size_request(250, -1)
    box.set_margin_start(12)
    box.set_margin_end(12)
    box.set_margin_top(12)
    box.set_margin_bottom(12)

    heading = Gtk.Label(label=title)
    heading.add_css_class("popover-heading")
    heading.set_wrap(True)
    heading.set_halign(Gtk.Align.START)
    box.append(heading)

    if entry.get("runner") == "dosbox-x" or game_key in ("th1","th2","th3","th4","th5"):
        status = Gtk.Label(label="")
        status.set_halign(Gtk.Align.START)
        status.set_text("DOSBox-X installed on system" if dosbox_installed() else "DOSBox-X not installed")
        box.append(status)
        install = Gtk.Button(label="Download DOSBox-X")
        box.append(install)
        change = Gtk.Button(label="Change ROM (.hdi/.nhd/.fdi/.img/.d88)…")
        box.append(change)

        remove_button = Gtk.Button(label="Remove ROM")
        remove_button.add_css_class("destructive-action")
        remove_button.set_visible(bool(exe_path and Path(exe_path).exists()))
        box.append(remove_button)

        popover.set_child(box)

        def choose(_):
            prompt_for_exe(title, game_key, config, label, card)
            config.setdefault(game_key,{})["runner"]="dosbox-x"
            save_config(config)

        def remove_rom(_):
            current = config.setdefault(game_key, {})
            current["exe"] = None
            save_config(config)
            update_title_label(label, title, None, "dosbox")
            if game_key in SETTINGS_REFRESHERS:
                SETTINGS_REFRESHERS[game_key]()
            card.remove_css_class("enabled-card")
            card.add_css_class("disabled-card")
            popover.popdown()

        change.connect("clicked", choose)
        remove_button.connect("clicked", remove_rom)
        def refresh_rom_button():
            remove_button.set_visible(bool(config.get(game_key, {}).get("exe") and Path(config.get(game_key, {}).get("exe")).exists()))
        SETTINGS_REFRESHERS[game_key] = refresh_rom_button
        install.connect("clicked", lambda *_: install_dosbox(install,status))
        return popover

    runner_label_text = Gtk.Label(label="Runner:")
    runner_label_text.set_halign(Gtk.Align.START)
    runner_label_text.add_css_class("settings-label")
    box.append(runner_label_text)

    runner_dropdown = Gtk.DropDown.new_from_strings(["Wine", "GE-Proton"])
    runner_dropdown.set_selected(1 if runner == "ge-proton" else 0)
    box.append(runner_dropdown)

    ge_status = Gtk.Label()
    ge_status.set_halign(Gtk.Align.START)
    ge_status.add_css_class("runner-status-small")
    update_runner_status(ge_status)
    box.append(ge_status)

    download_button = Gtk.Button(label="Download / update GE-Proton")
    box.append(download_button)

    download_progress = Gtk.ProgressBar()
    download_progress.add_css_class("download-progress")
    download_progress.set_show_text(True)
    download_progress.set_visible(False)
    box.append(download_progress)

    change_button = Gtk.Button(label="Change .exe…" if exe_path else "Set .exe…")
    box.append(change_button)

    remove_button = Gtk.Button(label="Remove .exe")
    remove_button.add_css_class("destructive-action")
    remove_button.set_visible(bool(exe_path and Path(exe_path).exists()))
    box.append(remove_button)

    options_label = Gtk.Label(label="Launch options:")
    options_label.set_halign(Gtk.Align.START)
    options_label.add_css_class("settings-label")
    box.append(options_label)

    options_entry = Gtk.Entry()
    options_entry.set_text(launch_options)
    options_entry.set_placeholder_text("e.g. mangohud %command%")
    box.append(options_entry)

    popover.set_child(box)

    def persist():
        current = config.setdefault(
            game_key, {"exe": exe_path, "launch_options": "", "runner": "wine"}
        )
        current["launch_options"] = options_entry.get_text()
        current["runner"] = "ge-proton" if runner_dropdown.get_selected() == 1 else "wine"
        save_config(config)
        update_title_label(label, title, current.get("exe"), current["runner"])

    def on_runner_changed(_dropdown, _param):
        persist()
        if runner_dropdown.get_selected() == 1 and not ge_proton_installed():
            ge_status.set_text("GE-Proton is not installed yet.")

    def on_change_clicked(_button):
        popover.popdown()
        prompt_for_exe(title, game_key, config, label, card)

    def on_remove_clicked(_button):
        current = config.setdefault(game_key, {})
        current["exe"] = None
        save_config(config)
        update_title_label(label, title, None, current.get("runner", "wine"))
        if game_key in SETTINGS_REFRESHERS:
            SETTINGS_REFRESHERS[game_key]()
        card.remove_css_class("enabled-card")
        card.add_css_class("disabled-card")
        popover.popdown()

    def on_closed(_popover):
        persist()

    runner_dropdown.connect("notify::selected", on_runner_changed)
    options_entry.connect("activate", lambda _entry: persist())
    change_button.connect("clicked", on_change_clicked)
    remove_button.connect("clicked", on_remove_clicked)
    def refresh_exe_button():
        remove_button.set_visible(bool(config.get(game_key, {}).get("exe") and Path(config.get(game_key, {}).get("exe")).exists()))
    SETTINGS_REFRESHERS[game_key] = refresh_exe_button
    download_button.connect(
        "clicked",
        lambda _button: on_download_ge_clicked(
            download_button, ge_status, download_button, download_progress
        ),
    )
    popover.connect("closed", on_closed)
    return popover
