"""Retired ec18 launcher: refuse before changing any historical resource.

Current launch requires a new private path and generation-bound bundle.
Use live_stack.py with exact images and a new own evidence folder.
"""


def main():
    raise SystemExit('legacy_current_launcher_retired: use tooling/foundation/live_stack.py '
        '--service-image sha256:<exact> --learner-image sha256:<exact> '
        '--port <unused-port> --evidence <new-own-folder>; old stacks are preserved')


if __name__=='__main__':main()
