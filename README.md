# AI-ASSISTED PROJECT

During the development of this project, I encountered a number of bugs and technical issues that I was unable to resolve on my own, so I used AI to help with debugging and troubleshooting. AI was also used as a learning aid to help me understand concepts I was not previously familiar with.

AI was used as a tool alongside my own development, testing, and decision-making

## Linux Touhou Launcher

Linux Touhou Launcher is a **work-in-progress** Touhou game launcher for Linux, built using Python, GTK4, and Libadwaita.

The goal of this project is to provide a simple and convenient way to manage and launch Touhou games on Linux

This project is still under active development, so some features may be incomplete or subject to change.

## Note

This project does not distribute any game files, users must provide their own game files to use with the launcher

## To-do list

* Fangames tab
* Printworks tab
* Controller support for navigating the launcher interface
* New Classics Remake
* AppImage release
* Flatpak release

## Installation

### Run From Source

Clone the repository and run the launcher with Python:

```bash
git clone https://github.com/lyrilika/linux-touhou-launcher.git
cd linux-touhou-launcher
chmod +x install_umu.sh
./install_umu.sh
python main.py
```

### Requirements

* Python
* PyGObject
* GTK4
* Libadwaita
* Wine (Optional if you will be using proton-GE)

Additional dependencies may be required depending on your Linux distribution and the games you want to run.

## Support

If you encounter a bug, please report it through [GitHub Issues](../../issues) and include as much relevant information as possible, such as your Linux distribution, hardware, and any error messages.

For questions, suggestions, or general discussion about the project, you can use [GitHub Discussions](../../discussions).

## Influences

This project was inspired by these two amazing projects:
- [A Digital Project - Touhou Launcher](https://a-digital-project.github.io/launcher/)
- [9Launcher](https://github.com/wearrrrr/9Launcher)
