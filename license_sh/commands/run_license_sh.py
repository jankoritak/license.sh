import questionary
import sys
from . import config_cmd
from license_sh.analyze import run_analyze
from ..config import get_config, get_raw_config, whitelist_licenses, ignore_packages
from ..helpers import get_dependency_tree_with_licenses, label_dep_tree, flatten_dependency_tree, \
    get_problematic_packages_from_analyzed_tree
from ..project_identifier import ProjectType, get_project_types
from ..reporters.ConsoleReporter import ConsoleReporter
from ..reporters.JSONConsoleReporter import JSONConsoleReporter
from ..runners import run_check


def run_license_sh(arguments):
    config_mode = arguments["config"]
    path = arguments["<path>"] or "."
    configPath = arguments["--config"]
    output = arguments["--output"]
    tree = arguments["--tree"]
    analyze = arguments["--dependencies"]
    project_type = arguments["--project"]
    debug = arguments["--debug"]
    interactive = arguments["--interactive"]

    path_to_config = configPath if configPath else path

    if interactive and output == "json":
        print("You can't run in interactive mode while specifying json as an output")
        exit(1)

    if config_mode:
        config_cmd(path, get_raw_config(path_to_config))
        exit(0)

    silent = output == "json" or debug
    whitelist, ignored_packages_map = get_config(path_to_config)

    # docopt guarantees that output variable contains either console or json
    Reporter = {"console": ConsoleReporter, "json": JSONConsoleReporter}[output]

    ignored_packages = []
    supported_projects = [e.value for e in ProjectType]
    project_list = [e.value for e in get_project_types(path)]

    if len(project_list) == 0:
        print(
            f"None of currently supported projects found. Supported {supported_projects}",
            file=sys.stderr,
        )
        exit(2)

    project_to_check: ProjectType = project_type if project_type else project_list[0]

    if project_type:
        if not project_type in supported_projects:
            print(
                f"Specified project '{project_type}' is not supported. Supported {supported_projects}",
                file=sys.stderr,
            )
            exit(2)

        if not project_type in project_list:
            print(
                f"Specified project '{project_type}' not found in '{path}'. Found {project_list}",
                file=sys.stderr,
            )
            exit(2)

    if not project_type and len(project_list) > 1:
        print(
            f"Curretly there is no support for multi project/language repositories. Found {project_list}. Only '{project_list[0]}' will be checked.",
            file=sys.stderr,
        )

    dep_tree = run_check(project_to_check, path, silent, debug)
    label_dep_tree(dep_tree, project_to_check)
    ignored_packages = ignored_packages_map.get(project_to_check, [])

    if analyze:
        analyzed_tree = run_analyze(project_to_check, path, dep_tree)
        if not analyzed_tree:
            print(
                f"Analyze not suported for '{project_to_check}' project",
                file=sys.stderr,
            )

    if not dep_tree:
        print(f"Unexpected issue, couldn't create dependency tree", file=sys.stderr)
        exit(3)

    (
        filtered_dep_tree,
        licenses_not_found,
        has_issues,
    ) = get_dependency_tree_with_licenses(
        dep_tree,
        whitelist,
        ignored_packages=ignored_packages,
        get_full_tree=tree,
        analyze=analyze,
    )

    Reporter.output(filtered_dep_tree)

    if licenses_not_found and interactive and questionary.confirm(
            "Do you want to add some of the licenses to your whitelist?"
    ).ask():
        license_whitelist = questionary.checkbox(
            "📋 Which licenses do you want to whitelist?",
            choices=[{"name": license} for license in licenses_not_found],
        ).ask()

        if license_whitelist:
            whitelist_licenses(path_to_config, license_whitelist)

    if has_issues and interactive and questionary.confirm(
            "Do you want to ignore some of the packages?"
    ).ask():
        bad_packages = get_problematic_packages_from_analyzed_tree(filtered_dep_tree)
        new_ignored_packages = questionary.checkbox(
            "📋 Which packages do you want to ignore?",
            choices=[{"name": package} for package, version in bad_packages]
        ).ask()
        ignore_packages(path_to_config, project_to_check, new_ignored_packages)

    if not has_issues:
        print("✅ Your project passed the compliance check 🎉🎉🎉")
    exit(1 if has_issues else 0)
