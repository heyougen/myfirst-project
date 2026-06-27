from copy import deepcopy


PROJECT_TEMPLATES = {
    "STM32 Keil": {
        "include_source_dirs": ["Core", "Drivers", "Inc", "Src", "User", "UserAPP", "MDK-ARM"],
        "exclude_dirs": [".git", ".stm32_git_tool", "Debug", "Objects", "Listings", "build", "__pycache__"],
        "exclude_patterns": [
            "*.map",
            "*.axf",
            "*.o",
            "*.d",
            "*.lst",
            "*.dep",
            "*.lnp",
            "*.uvguix.*",
            "*.uvgui.*",
            "*.build_log.htm",
            "*.htm",
        ],
        "firmware_patterns": ["*.bin", "*.hex"],
    },
    "Generic C/C++": {
        "include_source_dirs": ["src", "include", "lib", "test", "tests"],
        "exclude_dirs": [".git", ".stm32_git_tool", "build", "dist", "out", "bin", "obj"],
        "exclude_patterns": ["*.o", "*.obj", "*.exe", "*.dll", "*.so", "*.a", "*.lib", "*.map"],
        "firmware_patterns": ["*.bin", "*.elf", "*.hex"],
    },
    "Python": {
        "include_source_dirs": ["src", "tests", "scripts"],
        "exclude_dirs": [".git", ".stm32_git_tool", "__pycache__", ".venv", "venv", "build", "dist"],
        "exclude_patterns": ["*.pyc", "*.pyo", "*.log"],
        "firmware_patterns": ["*.whl", "*.tar.gz"],
    },
    "Custom": {
        "include_source_dirs": [],
        "exclude_dirs": [".git", ".stm32_git_tool", "build", "dist"],
        "exclude_patterns": [],
        "firmware_patterns": [],
    },
}


def template_names():
    return list(PROJECT_TEMPLATES.keys())


def get_template(name):
    return deepcopy(PROJECT_TEMPLATES.get(name, PROJECT_TEMPLATES["STM32 Keil"]))
