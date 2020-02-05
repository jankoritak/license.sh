import json
from os import path
from typing import List
from .project_identifier import ProjectType

DEFAULT_CONFIG_NAME = ".license-sh.json"
IGNORED_PACKAGES = "ignored_packages"
WHITELIST = "whitelist"

try:
    from license_sh_private.licenses import COMMERCIAL_LICENSES as WHITELIST
except ImportError:
    PRIVATE_LICENCES_WHITELIST = []


def get_ignored_packages(ignored_packages: dict):
    ignored_packages_map = {e.value: [] for e in ProjectType}
    if not ignored_packages:
        return ignored_packages_map
    project_list = [e.value for e in ProjectType]
    for project_type, ignored_packages in ignored_packages.items():
        if not project_type in project_list:
            print(
                f"Ignored packages for project '{project_type}' is not supported. Ignoring..."
            )
            continue
        if not isinstance(ignored_packages, list):
            print(
                f"Ignored packages for project '{project_type}' are incorrect. Ignoring..."
            )
            ignored_packages_map[project_type] = []
            continue

        for ignored_package in ignored_packages:
            if not isinstance(ignored_package, str):
                print(
                    f"Ignored package for project {project_type}, '{ignored_package}' is incorrect. Ignoring..."
                )
            else:
                ignored_packages_map[project_type].append(ignored_package)
    return ignored_packages_map


def get_licenses_whitelist(whitelist: list):
    licenses_whitelist = PRIVATE_LICENCES_WHITELIST
    if not whitelist:
        return licenses_whitelist
    for whitelisted_license in whitelist:
        if not isinstance(whitelisted_license, str):
            print(
                f"Whitelisted license '{whitelisted_license}' is incorrect. Ignoring..."
            )
        else:
            licenses_whitelist.append(whitelisted_license)
    return licenses_whitelist


def get_config_path(path_to_config: str):
    return (
        path_to_config
        if path.isfile(path_to_config)
        else path.join(path_to_config, DEFAULT_CONFIG_NAME)
    )


def get_raw_config(path_to_config: str):
    config_path = get_config_path(path_to_config)
    try:
        with open(config_path) as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Config file '{config_path}' not found...")
        return dict()


def get_config(path_to_config: str):
    raw_config = get_raw_config(path_to_config)

    return (
        get_licenses_whitelist(raw_config.get(WHITELIST, [])),
        get_ignored_packages(raw_config.get(IGNORED_PACKAGES, {})),
    )


def write_config(path_to_config: str, config):
    config_path = get_config_path(path_to_config)
    try:
        with open(config_path, "w+") as outfile:
            json.dump(config, outfile, indent=2, sort_keys=True)
            return True
    except FileNotFoundError:
        return False


def whitelist_licenses(path_to_config: str, licenses: List[str]):
    config = get_raw_config(path_to_config)
    current_whitelist = get_licenses_whitelist(config.get(WHITELIST, []))
    config[WHITELIST] = list(set(current_whitelist + licenses))
    write_config(path_to_config, config)
