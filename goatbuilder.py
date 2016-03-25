#!/usr/bin/env python3
"""
Copyright (c) 2016 Luca Boccassi <luca.boccassi@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import argparse
import itertools
import os
import shutil
import subprocess
import time


def copy_pacs(pbuilder_base, source, dest, distro, arch, version, pkg=""):
    if pkg == "current":
        pkg = ""
    elif pkg != "":
        pkg = "-" + pkg

    dkms_src = pbuilder_base + "/" + source + "-" + distro + "-" + arch + \
               "/result/" + "nvidia" + pkg + "-kernel-dkms_" + version + \
               "_" + arch + ".deb"
    dkms_dst = pbuilder_base + "/" + dest + "-" + distro + "-" + arch + \
               "/result/" + "nvidia" + pkg + "-kernel-dkms_" + version + \
               "_" + arch + ".deb"
    if os.path.isfile(dkms_src) and not os.path.isfile(dkms_dst):
        shutil.copy2(dkms_src, dkms_dst)

    source_src = pbuilder_base + "/" + source + "-" + distro + "-" + arch + \
               "/result/" + "nvidia" + pkg + "-kernel-source_" + version + \
               "_" + arch + ".deb"
    source_dst = pbuilder_base + "/" + dest + "-" + distro + "-" + arch + \
               "/result/" + "nvidia" + pkg + "-kernel-source_" + version + \
               "_" + arch + ".deb"
    if os.path.isfile(source_src) and not os.path.isfile(source_dst):
        shutil.copy2(source_src, source_dst)


def delete_pacs(pbuilder_base, dest, distro, arch, version, pkg=""):
    if pkg == "current":
        pkg = ""
    elif pkg != "":
        pkg = "-" + pkg

    dkms_dst = pbuilder_base + "/" + dest + "-" + distro + "-" + arch + \
               "/result/" + "nvidia" + pkg + "-kernel-dkms_" + version + \
               "_" + arch + ".deb"
    if os.path.isfile(dkms_dst):
        os.remove(dkms_dst)

    source_dst = pbuilder_base + "/" + dest + "-" + distro + "-" + arch + \
               "/result/" + "nvidia" + pkg + "-kernel-source_" + version + \
               "_" + arch + ".deb"
    if os.path.isfile(source_dst):
        os.remove(source_dst)

def update_chroot(base, dist, arch):
    env = os.environ.copy()
    env["OS"] = base
    env["ARCH"] = arch
    env["DIST"] = dist

    p = subprocess.Popen(["cowbuilder", "--update"], env=env)
    p.base = base
    p.arch = arch
    p.dist = dist
    return p


def update_all_chroots(bases, dists, archs):
    processes = []
    for base, dist, arch in itertools.product(bases, dists, archs):
        processes.append(update_chroot(base, dist, arch))
        time.sleep(5)

    for p in processes:
        p.wait()
        if p.returncode != 0:
            print("Error while running:"
                  " {} OS={} DIST={} ARCH={}".format(p.args, p.base, p.dist,
                                                     p.arch))


if __name__ == "__main__":
    with open("/etc/pbuilderrc") as file:
        text = file.read()
    m = re.search(r'PBUILDER_BASE="(.*)"', text)
    if m is not None:
        pbuilderrc = m.group(1)

    parser = argparse.ArgumentParser(description="Automated test for "
                                     "Debian's nvidia-kernel-dkms and "
                                     "nvidia-kernel-source packages via "
                                     "cowbuilder. The tests will be run in "
                                     "parallel per architecture. A valid "
                                     "pbuilderrc is required, and at least a "
                                     "bootstrapped cowbuilder chroot with a"
                                     "name in the format: "
                                     "<TARGET>-<DISTRIBUTION>-<ARCH>")
    parser.add_argument('-u', '--update', action='store_true',
                        help='Update chroots. Defaults to false.')
    parser.add_argument('-c', '--copy', action='store_false',
                        help="Copy packages from source chroot to destination"
                        " chroot (result subdirectory). Defaults to true.")
    parser.add_argument('-p', '--pbuilder-base-path',
                        default=pbuilderrc,
                        help="Path to pbuilder base directory. Defaults to "
                        "value of PBUILDER_BASE in /etc/pbuilderrc.")
    parser.add_argument('-s', '--source', default='base',
                        help="Source chroot name (source of packages). "
                        "Defaults to base (eg: base-sid-amd64).")
    parser.add_argument('-t', '--target', default='dkms',
                        help="Destination chroot name (destination of "
                        "packages and build host). "
                        "Defaults to dkms (eg: dkms-sid-amd64).")
    parser.add_argument('-d', '--distribution', default='sid',
                        help='Chroot distribution. Defaults to sid.')
    parser.add_argument('-a', '--archs', dest='archs', nargs='+',
                        default=["amd64", "i386", "armhf"],
                        help='amd64, i386 or armhf. Defaults to all of them.')
    parser.add_argument('-n', '--nvidia-branch', default='current',
                        help="Branch of nvidia packages (current, "
                        "legacy-340xx, etc). Defaults to current.")
    parser.add_argument('-v', '--version', required=True,
                        help='Package version. Required.')

    args = parser.parse_args()

    for arch in args.archs:
        if args.copy:
            copy_pacs(args.pbuilder_base_path, args.source, args.target,
                      args.distribution, arch, args.version,
                      args.nvidia_branch)
    if args.update:
        update_all_chroots([args.source, args.target], [args.distribution],
                           args.archs)

    if args.copy:
        for arch in args.archs:
            delete_pacs(args.pbuilder_base_path, args.target,
                        args.distribution, arch, args.version,
                        args.nvidia_branch)
