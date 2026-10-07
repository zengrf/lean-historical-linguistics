"""Install the local workbench and build its Lean executables with a recorded toolchain."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.request import urlopen
import venv

ROOT = Path(__file__).resolve().parents[1]
ELAN_RELEASE = "v4.2.4"
# Official GitHub release asset digests, checked 2026-10-07.
ASSETS = {
    ("Darwin", "x86_64"): (
        "x86_64-apple-darwin",
        "8a340b309d8ed2e96f930761fa223b3af57a38f5d253b53ac90293c9516f8cd4",
    ),
    ("Darwin", "arm64"): (
        "aarch64-apple-darwin",
        "7ad829861392c718dfebde3a83b5c8508df47be02af68894b094b0b3952616e5",
    ),
    ("Linux", "x86_64"): (
        "x86_64-unknown-linux-gnu",
        "42b94d4244e8353142c456ec0e4ca6528fd898a6c604d4059f494e706e431f63",
    ),
    ("Linux", "aarch64"): (
        "aarch64-unknown-linux-gnu",
        "05febd124d84ebf994b2e7479922a5650b1e950c17ae3bd1ddd776b65bb72bf9",
    ),
}


def run(command, env=None):
    subprocess.run([str(p) for p in command], cwd=ROOT, env=env, check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--toolchain", default=None)
    p.add_argument("--use-installed-elan", action="store_true")
    p.add_argument(
        "--skip-dependencies",
        action="store_true",
        help="Use the current Python environment (CI or an already installed workspace)",
    )
    p.add_argument("--doctor", action="store_true")
    args = p.parse_args()
    if sys.version_info < (3, 11):
        raise SystemExit(
            "Install Python 3.12 first; this application requires Python 3.11 or later."
        )
    if args.doctor:
        from workspace_engine import readiness

        ready = readiness()
        print(
            json.dumps(
                dict(
                    python=sys.version.split()[0],
                    platform=platform.platform(),
                    engine=ready,
                ),
                indent=2,
            )
        )
        raise SystemExit(0 if ready["ready"] else 1)
    toolchain = args.toolchain or (ROOT / "lean/lean-toolchain").read_text().strip()
    if (
        not args.toolchain
        and sys.platform == "darwin"
        and int(platform.mac_ver()[0].split(".")[0]) < 11
    ):
        toolchain = "leanprover/lean4:v4.19.0"
    if not args.skip_dependencies:
        directory = ROOT / ".venv"
        if not directory.is_dir():
            venv.EnvBuilder(with_pip=True).create(directory)
        python = directory / "bin/python"
        run([python, "-m", "pip", "install", "-r", ROOT / "requirements-workspace.txt"])
    environment = os.environ.copy()
    if args.use_installed_elan:
        lake = shutil.which("lake")
        if not lake:
            raise SystemExit(
                "No lake found on PATH; omit --use-installed-elan to install the pinned manager locally"
            )
    else:
        home = ROOT / ".tools/elan"
        lake = home / "bin/lake"
        environment["ELAN_HOME"] = str(home)
        if not lake.is_file():
            asset = ASSETS.get((platform.system(), platform.machine()))
            if asset is None:
                raise SystemExit(
                    "This release supports macOS and Linux. Use a Linux environment on Windows."
                )
            target, expected = asset
            url = f"https://github.com/leanprover/elan/releases/download/{ELAN_RELEASE}/elan-{target}.tar.gz"
            with tempfile.TemporaryDirectory(
                prefix="comparative-install-"
            ) as temporary:
                archive = Path(temporary) / "elan.tar.gz"
                print("Downloading pinned Lean toolchain manager:", url, flush=True)
                with urlopen(url, timeout=60) as source, archive.open("wb") as output:
                    shutil.copyfileobj(source, output)
                if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
                    raise SystemExit(
                        "Toolchain manager checksum mismatch; installation stopped"
                    )
                with tarfile.open(archive) as bundle:
                    member = next(
                        m
                        for m in bundle.getmembers()
                        if Path(m.name).name == "elan-init" and m.isfile()
                    )
                    installer = Path(temporary) / "elan-init"
                    with bundle.extractfile(member) as source, installer.open(
                        "wb"
                    ) as output:
                        shutil.copyfileobj(source, output)
                    installer.chmod(0o700)
                run(
                    [
                        installer,
                        "-y",
                        "--no-modify-path",
                        "--default-toolchain",
                        "none",
                    ],
                    environment,
                )
    run([lake, "+" + toolchain, "-d", ROOT / "lean", "build"], environment)
    from workspace_engine import record_build

    record_build(toolchain)
    print("Setup complete. Run ./workbench to open the private research workspace.")


if __name__ == "__main__":
    main()
