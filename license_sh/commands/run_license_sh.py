import questionary

from . import config_cmd
from ..config import get_config, get_raw_config, whitelist_licenses
from ..helpers import get_dependency_tree_with_licenses
from ..project_identifier import ProjectType, get_project_types
from ..reporters.ConsoleReporter import ConsoleReporter
from ..reporters.JSONConsoleReporter import JSONConsoleReporter
from ..runners.maven import MavenRunner
from ..runners.npm import NpmRunner
from ..runners.python import PythonRunner
from ..runners.yarn import YarnRunner


def run_license_sh(arguments):

    config_mode = arguments["config"]
    path = arguments["<path>"] or "."
    configPath = arguments["--config"]
    output = arguments["--output"]
    tree = arguments["--tree"]
    debug = arguments["--debug"]

    path_to_config = configPath if configPath else path

    if config_mode:
        config_cmd(path, get_raw_config(path_to_config))
        exit(0)

    silent = output == "json" or debug
    whitelist, ignored_packages_map = get_config(path_to_config)

    # docopt guarantees that output variable contains either console or json
    Reporter = {"console": ConsoleReporter, "json": JSONConsoleReporter}[output]

    project_types = get_project_types(path)
    ignored_packages = []

    dep_tree = None

    if ProjectType.PYTHON_PIPENV in project_types:
        runner = PythonRunner(path, silent, debug)
        dep_tree, license_map = runner.check()
        ignored_packages = ignored_packages_map[ProjectType.PYTHON_PIPENV.value]

    if ProjectType.NPM in project_types:
        runner = NpmRunner(path, silent, debug)
        dep_tree, license_map = runner.check()
        ignored_packages = ignored_packages_map[ProjectType.NPM.value]

    if ProjectType.MAVEN in project_types:
        runner = MavenRunner(path, silent, debug)
        dep_tree, license_map = runner.check()
        ignored_packages = ignored_packages_map[ProjectType.MAVEN.value]

    if ProjectType.YARN in project_types:
        runner = YarnRunner(path, silent, debug)
        dep_tree, license_map = runner.check()
        ignored_packages = ignored_packages_map[ProjectType.YARN.value]

    (
        filtered_dep_tree,
        licenses_not_found,
        has_issues,
    ) = get_dependency_tree_with_licenses(
        dep_tree, whitelist, ignored_packages=ignored_packages, get_full_tree=tree
    )

    Reporter.output(filtered_dep_tree)

    if licenses_not_found and output != "json":
        manual_add: bool = questionary.confirm(
            "Do you want to add some of the licenses to your whitelist?"
        ).ask()

        if manual_add:
            license_whitelist = questionary.checkbox(
                "📋 Which licenses do you want to whitelist?",
                choices=[{"name": license} for license in licenses_not_found],
            ).ask()
            if license_whitelist:
                whitelist_licenses(path_to_config, license_whitelist)

                whitelist, ignored_packages = get_config(path_to_config)
                (
                    filtered_dep_tree,
                    licenses_not_found,
                    has_issues,
                ) = get_dependency_tree_with_licenses(
                    dep_tree,
                    whitelist,
                    ignored_packages=ignored_packages,
                    get_full_tree=tree,
                )
                Reporter.output(filtered_dep_tree)

    exit(1 if has_issues else 0)
