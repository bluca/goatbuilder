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
import pexpect
import re
import shutil
import subprocess
import threading
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


def start_chr(pbuilder_base, base, dist, arch, prompt="root@.*:/.*#"):
    env = os.environ.copy()
    env["OS"] = base
    env["ARCH"] = arch
    env["DIST"] = dist

    chr = pexpect.spawn("cowbuilder --login "
                        "--bindmounts {}/{}-{}-{}".format(pbuilder_base, base,
                                                          dist, arch),
                        env=env, timeout=600)
    chr.expect(prompt)

    return chr


def stop_chr(chroot_handle):
    chroot_handle.sendline("exit")
    chroot_handle.expect([pexpect.EOF])


def test_dkms(chr, pbuilder_base, base, dist, arch, version, pkg="current",
              prompt="root@.*:/.*#"):
    if pkg != "":
        pkg = "-" + pkg
    if pkg == "-current":
        deb = ""
    else:
        deb = pkg

    chr.sendline("dpkg -i {0}/{1}-{2}-{3}/result/"
                 "nvidia{5}-kernel-dkms"
                 "_{4}_{3}.deb".format(pbuilder_base, base, dist, arch,
                                       version, deb))
    index = chr.expect(["Setting up nvidia{}-kernel-dkms".format(deb),
               "Errors were encountered while processing"])
    if index != 0:
        raise Exception("Failed to dpkg -i {0}-{1}-{2}/result/"
                 "nvidia{4}-kernel-dkms_{3}_{2}.deb".format(base, dist, arch,
                                                         version, deb))
    chr.expect(prompt)

    dkms_arch = {"amd64": "x86_64", "i386": "i386", "armhf": "armv7l"}
    header_arch = {"amd64": "amd64", "i386": "[4|5|6]86", "armhf": "armmp"}
    chr.sendline("ls /usr/src |"
                 " grep -e 'linux-headers.*{}'".format(header_arch[arch]))
    chr.expect(prompt)
    up_m = re.search("(.*)-\d+", version)
    up_ver = up_m.group(1)
    kernels = [m.group(1) for m in re.finditer("linux-headers-(.*)",
                                    chr.before.decode("utf-8"))]
    for k in kernels:
        print("dkms install for kernel: {}".format(k))
        chr.sendline("dkms install nvidia"
                     "{}/{} -k {}/{}".format(pkg, up_ver, k, dkms_arch[arch]))
        index = chr.expect(["DKMS: install completed", "Error"])
        chr.expect(prompt)
        if index != 0:
            print("Failed to dkms install nvidia"
                  "{}/{} -k {}/{}".format(pkg, up_ver, k, dkms_arch[arch]))
            print(chr.before)
            print(chr.after)


def test_source(chr, pbuilder_base, base, dist, arch, version, pkg="current",
              prompt="root@.*:/.*#"):
    if pkg != "":
        pkg = "-" + pkg
    if pkg == "-current":
        deb = ""
    else:
        deb = pkg

    chr.sendline("dpkg -i {0}/{1}-{2}-{3}/result/"
                 "nvidia{5}-kernel-source"
                 "_{4}_{3}.deb".format(pbuilder_base, base, dist, arch,
                                       version, deb))
    index = chr.expect(["Setting up nvidia{}-kernel-source".format(deb),
               "Errors were encountered while processing"])
    if index != 0:
        raise Exception("Failed to dpkg -i {0}-{1}-{2}/result/"
                 "nvidia{4}-kernel-source_{3}_{2}.deb".format(base, dist, arch,
                                                         version, deb))
    chr.expect(prompt)

    chr.sendline("rm -rf /tmp/modules")
    chr.expect(prompt)

    chr.sendline("ls /usr/src | grep -e 'nvidia-kernel\.tar'")
    chr.expect(prompt)

    compression = re.search("nvidia-kernel\.tar\.(bz2|xz|gz)",
                            chr.before.decode("utf-8"))

    if compression.group(1) == "bz2":
        chr.sendline("tar xjvf /usr/src/nvidia-kernel.tar.bz2 -C /tmp")
    elif compression.group(1) == "xz":
        chr.sendline("tar xJvf /usr/src/nvidia-kernel.tar.xz -C /tmp")
    elif compression.group(1) == "gz":
        chr.sendline("tar xzvf /usr/src/nvidia-kernel.tar.gz -C /tmp")
    else:
        raise Exception("Could not find nvidia-kernel tarball in /usr/src")
    chr.expect(prompt)

    chr.sendline("cd /tmp/modules/nvidia-kernel")
    chr.expect(prompt)

    kernel_arch = {"amd64": "amd64", "i386": "[4|5|6]86", "armhf": "armmp"}
    chr.sendline("ls /usr/src |"
                 " grep -e 'linux-headers.*{}'".format(kernel_arch[arch]))
    chr.expect(prompt)

    kernels = [m.group(1) for m in re.finditer("linux-headers-(.*)",
                                    chr.before.decode("utf-8"))]
    for k in kernels:
        print("source build for kernel: {}".format(k))
        chr.sendline("unset ARCH")
        chr.expect(prompt)
        chr.sendline("export KSRC=/usr/src/linux-headers-{}".format(k))
        chr.expect(prompt)
        chr.sendline("debian/rules clean")
        chr.expect(prompt)
        chr.sendline("debian/rules binary_modules")
        index = chr.expect(["dpkg-deb: building package",
                            "recipe for target 'modules' failed",
                            pexpect.TIMEOUT])
        chr.expect(prompt)
        if index != 0:
            print("Failed source build on kernel {}".format(k))
            print(chr.before)
            print(chr.after)
        chr.sendline("debian/rules clean")
        chr.expect(prompt)

    chr.sendline("rm -rf /tmp/modules")
    chr.expect(prompt)


def worker(pbuilder_base, base, dist, arch, version, pkg="current",
              prompt="root@.*:/.*#", dkms=True, source=True):
    chr = start_chr(pbuilder_base, base, dist, arch)
    try:
        if dkms:
            test_dkms(chr, pbuilder_base, base, dist, arch, version, pkg,
                        prompt)
        if source:
            test_source(chr, pbuilder_base, base, dist, arch, version, pkg,
                        prompt)
    except Exception as e:
        print(chr.before)
        print(chr.after)
        stop_chr(chr)
        raise e
    finally:
        stop_chr(chr)


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
    parser.add_argument('-b', '--build', action='store_false',
                        help='Test dkms and source builds. Defaults to true.')
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
    parser.add_argument('-r', '--prompt-regex', default='root@.*:/.*#',
                        help="Regex that matches the chroot prompt, required "
                        "for pexpect. Defaults to root@.*:/.*#")
    parser.add_argument('-n', '--nvidia-branch', default='current',
                        help="Branch of nvidia packages (current, "
                        "legacy-340xx, etc). Defaults to current.")
    parser.add_argument('-v', '--version', required=True,
                        help='Package version. Required.')
    parser.add_argument('-l', '--ludicrous-speed', action='store_false',
                        help="Test source and dkms builds in parallel, in"
                        "separate chroots")

    args = parser.parse_args()

    if args.update:
        update_all_chroots([args.source, args.target], [args.distribution],
                           args.archs)

    if args.build:
        threads = []
        for arch in args.archs:
            if args.copy:
                copy_pacs(args.pbuilder_base_path, args.source, args.target,
                          args.distribution, arch, args.version,
                          args.nvidia_branch)
            if not args.ludicrous_speed:
                t = threading.Thread(target=worker, args=(args.pbuilder_base_path,
                                                          args.target,
                                                          args.distribution,
                                                          arch,
                                                          args.version,
                                                          args.nvidia_branch,
                                                          args.prompt_regex))
                t.start()
                threads.append(t)
                time.sleep(5)
            else:
                t = threading.Thread(target=worker, args=(args.pbuilder_base_path,
                                                          args.target,
                                                          args.distribution,
                                                          arch,
                                                          args.version,
                                                          args.nvidia_branch,
                                                          args.prompt_regex,
                                                          True, False))
                t.start()
                threads.append(t)
                time.sleep(5)

                t = threading.Thread(target=worker, args=(args.pbuilder_base_path,
                                                          args.target,
                                                          args.distribution,
                                                          arch,
                                                          args.version,
                                                          args.nvidia_branch,
                                                          args.prompt_regex,
                                                          False, True))
                t.start()
                threads.append(t)
                time.sleep(5)


        for t in threads:
            t.join()


        if args.copy:
            for arch in args.archs:
                delete_pacs(args.pbuilder_base_path, args.target,
                            args.distribution, arch, args.version,
                            args.nvidia_branch)
